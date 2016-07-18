import binascii
import ctypes
import datetime
import json
import logging
import os
import struct
import time

from satnogsclient import settings
from satnogsclient.observer.commsocket import Commsocket
from satnogsclient.observer.udpsocket import Udpsocket
from satnogsclient.upsat import hldlc
from satnogsclient.upsat import packet_settings


logger = logging.getLogger('satnogsclient')
log_path = ""


def folder_init():
    global log_path
    log_path = settings.OUTPUT_PATH + "/files/"
    logger.info("Dir %s", log_path)
    if not os.path.exists(log_path):
        logger.info("Made dir %s", log_path)
        os.mkdir(log_path)
    for sid in range(8, 11):
        sid_dir = os.path.join(log_path, packet_settings.upsat_store_ids[str(sid)])
        logger.info("Check dir %s", sid_dir)
        if not os.path.exists(sid_dir):
            logger.info("Made dir %s", sid_dir)
            os.mkdir(sid_dir)


def ecss_encoder(port):
    logger.info('Started ecss encoder')
    sock = Commsocket('127.0.0.1', port)
    sock.bind()
    sock.listen()
    while 1:
        conn = sock.accept()
        if conn:
            data = conn.recv(sock.tasks_buffer_size)
            ecss_packetizer(data)


def ecss_depacketizer(buf, dict_out):
    size = len(buf)
    print binascii.hexlify(buf)
    assert((buf != 0) == True)
    assert((size > packet_settings.MIN_PKT_SIZE and size < packet_settings.MAX_PKT_SIZE) == True)
    tmp_crc1 = buf[size - 1]
    tmp_crc2 = 0
    for i in range(0, size - 2):
        tmp_crc2 = tmp_crc2 ^ buf[i]

    ver = buf[0] >> 5

    pkt_type = (buf[0] >> 4) & 0x01
    dfield_hdr = (buf[0] >> 3) & 0x01

    pkt_app_id = buf[1]

    pkt_seq_flags = buf[2] >> 6
    t = bytearray(2)
    t[0] = buf[2]
    t[1] = buf[3]
    t.reverse()

    pkt_len = (buf[4] << 8) | buf[5]
    ccsds_sec_hdr = buf[6] >> 7
    tc_pus = buf[6] >> 4
    pkt_ack = 0x07 & buf[6]
    pkt_ser_type = buf[7]
    pkt_ser_subtype = buf[8]
    pkt_dest_id = buf[9]

    if not ((pkt_app_id < packet_settings.LAST_APP_ID) == True):
        return (dict_out, packet_settings.SATR_PKT_ILLEGAL_APPID)

    if not ((pkt_len == size - packet_settings.ECSS_HEADER_SIZE - 1) == True):
        print "INV LEN", pkt_len, " ", size - packet_settings.ECSS_HEADER_SIZE - 1, " ", size
        return (dict_out, packet_settings.SATR_PKT_INV_LEN)

    pkt_len = pkt_len - packet_settings.ECSS_DATA_HEADER_SIZE - packet_settings.ECSS_CRC_SIZE + 1

    if not (tmp_crc1 == tmp_crc2):
        print "INV CRC calc ", tmp_crc2, " pkt", tmp_crc1
        return (dict_out, packet_settings.SATR_PKT_INC_CRC)

    if not ((ver == packet_settings.ECSS_VER_NUMBER) == True):
        return (dict_out, packet_settings.SATR_ERROR)

    if not ((tc_pus == packet_settings.ECSS_PUS_VER) == True):
        return (dict_out, packet_settings.SATR_ERROR)

    if not ((ccsds_sec_hdr == packet_settings.ECSS_SEC_HDR_FIELD_FLG) == True):
        print "INV HDR FIELD", ccsds_sec_hdr
        return (dict_out, packet_settings.SATR_ERROR)

    if not ((pkt_type == packet_settings.TC or pkt_type == packet_settings.TM) == True):
        print "INV TYPE", pkt_type
        return (dict_out, packet_settings.SATR_ERROR)

    if not ((dfield_hdr == packet_settings.ECSS_DATA_FIELD_HDR_FLG) == True):
        return (dict_out, packet_settings.SATR_ERROR)

    if not ((pkt_ack == packet_settings.TC_ACK_NO or pkt_ack == packet_settings.TC_ACK_ACC) == True):
        return (dict_out, packet_settings.SATR_ERROR)

    if not ((pkt_seq_flags == packet_settings.TC_TM_SEQ_SPACKET) == True):
        return (dict_out, packet_settings.SATR_ERROR)
    pkt_data = bytes(pkt_len)

    pkt_data = buf[packet_settings.ECSS_DATA_OFFSET: size - 2]
    dict_out = {'type': pkt_type,
             'app_id': pkt_app_id,
             'size': pkt_len,
             'ack': pkt_ack,
             'ser_type': pkt_ser_type,
             'ser_subtype': pkt_ser_subtype,
             'dest_id': pkt_dest_id,
             'data': pkt_data
             }
    logger.debug('Got packet: %s', dict_out)
    return (dict_out, packet_settings.SATR_OK)


def ecss_decoder(port):
    logger.info('Started ecss decoder')
    sock = Commsocket('127.0.0.1', port)
    sock.bind()
    sock.listen()
    while 1:
        conn = sock.accept()
        if conn:
            data = conn.recv(sock.tasks_buffer_size)
            ecss_depacketizer(data)


def ecss_packetizer(ecss, buf):
    Commsocket(packet_settings.FRAME_RECEIVER_IP, packet_settings.FRAME_RECEIVER_PORT)
    assert(((ecss['type'] == 0) or (ecss['type'] == 1)) == True)
    assert((ecss['app_id'] < packet_settings.LAST_APP_ID) == True)
    data_size = ecss['size']
    app_id = ecss['app_id']
    app_id_ms = app_id & 0xFF00
    app_id_ls = app_id & 0x00FF
    app_id_ms = app_id_ms >> 8
    buf[0] = (packet_settings.ECSS_VER_NUMBER << 5 | ecss['type']
               << 4 | packet_settings.ECSS_DATA_FIELD_HDR_FLG << 3 | app_id_ms)
    buf[1] = app_id_ls
    seq_flags = packet_settings.TC_TM_SEQ_SPACKET
    seq_count = ecss['seq_count']
    seq_count_ms = (seq_count >> 8) & 0x00FF
    seq_count_ls = seq_count & 0x00FF
    buf[2] = (seq_flags << 6 | seq_count_ms)
    buf[3] = seq_count_ls
    if ecss['type'] == 0:
        buf[6] = packet_settings.ECSS_PUS_VER << 4
    elif ecss['type'] == 1:
        buf[6] = (packet_settings.ECSS_SEC_HDR_FIELD_FLG << 7 | packet_settings.ECSS_PUS_VER << 4 | ecss['ack'])
    buf[7] = ecss['ser_type']
    buf[8] = ecss['ser_subtype']
    buf[9] = ecss['dest_id']
    buf_pointer = packet_settings.ECSS_DATA_OFFSET
    for i in range(0, data_size):
        buf[buf_pointer + i] = ecss['data'][i]
    data_w_headers = data_size + packet_settings.ECSS_DATA_HEADER_SIZE + packet_settings.ECSS_CRC_SIZE - 1
    packet_size_ms = (data_w_headers >> 8) & 0x00FF
    packet_size_ls = data_w_headers & 0x00FF
    buf[4] = packet_size_ms >> 8
    buf[5] = packet_size_ls
    buf_pointer = buf_pointer + data_size
    for i in range(0, buf_pointer):
        buf[buf_pointer + 1] = buf[buf_pointer + 1] ^ buf[i]

    size = buf_pointer + 2
    assert((size > packet_settings.MIN_PKT_SIZE and size < packet_settings.MAX_PKT_SIZE) == True)
    logger.debug('Packet in hex: %s', ''.join(' {:02x} '.format(x) for x in buf))
    return packet_settings.SATR_OK


def comms_off():
    sock = Udpsocket([])
    data = ctypes.create_string_buffer(25)
    data[0:9] = 'RF SW CMD'
    struct.pack_into("<I", data, 9, settings.RF_SW_CMD_OFF_1)
    struct.pack_into("<I", data, 13, settings.RF_SW_CMD_OFF_2)
    struct.pack_into("<I", data, 17, settings.RF_SW_CMD_OFF_3)
    struct.pack_into("<I", data, 21, settings.RF_SW_CMD_OFF_4)
    d = bytearray(data)
    sock.sendto(d, (packet_settings.FRAME_RECEIVER_IP, packet_settings.FRAME_RECEIVER_PORT))


def comms_on():
    sock = Udpsocket([])
    data = ctypes.create_string_buffer(25)
    data[0:9] = 'RF SW CMD'
    struct.pack_into("<I", data, 9, settings.RF_SW_CMD_ON_1)
    struct.pack_into("<I", data, 13, settings.RF_SW_CMD_ON_2)
    struct.pack_into("<I", data, 17, settings.RF_SW_CMD_ON_3)
    struct.pack_into("<I", data, 21, settings.RF_SW_CMD_ON_4)
    print data.raw
    d = bytearray(data)
    sock.sendto(d, (packet_settings.FRAME_RECEIVER_IP, packet_settings.FRAME_RECEIVER_PORT))


def custom_cmd_to_backend(data):
    sock = Udpsocket([])
    packet = json.dumps(data)
    sock.sendto(packet, ('127.0.0.1', settings.STATUS_LISTENER_PORT))


def construct_packet(ecss_dict, backend):
    logger.info('ECSS to be sent: %s', ecss_dict)
    if backend == "serial":
        out_buf = bytearray(0)
        packet_size = len(ecss_dict['data']) + packet_settings.ECSS_DATA_HEADER_SIZE + packet_settings.ECSS_CRC_SIZE + packet_settings.ECSS_HEADER_SIZE
        ecssbuf = bytearray(packet_size)
        ecss_packetizer(ecss_dict, ecssbuf)
        hldlc.HLDLC_frame(ecssbuf, out_buf)
    elif backend == "gnuradio":
        packet_size = len(ecss_dict['data']) + packet_settings.ECSS_DATA_HEADER_SIZE + packet_settings.ECSS_CRC_SIZE + packet_settings.ECSS_HEADER_SIZE
        out_buf = bytearray(packet_size)
        ecss_packetizer(ecss_dict, out_buf)
    return out_buf


def deconstruct_packet(buf_in, ecss_dict, backend):
    if backend == 'serial':
        hldlc_buf = bytearray(0)
        hldlc.HLDLC_deframe(buf_in, hldlc_buf)
        print "HLDLC ", ''.join('{:02x}'.format(x) for x in buf_in), " ", ''.join('{:02x}'.format(x) for x in hldlc_buf)
        res = ecss_depacketizer(hldlc_buf, ecss_dict)
        logger.debug('The HDLC result is %s', res)
    elif backend == 'gnuradio':
        res = ecss_depacketizer(buf_in, ecss_dict)
    return res


def ecss_logic(ecss_dict):

    global log_path

    id = 0
    text = "Nothing found"

    if ecss_dict['ser_type'] == packet_settings.TC_VERIFICATION_SERVICE:

        # We should have a list of packets with ack in order to return it
        report = "Wrong sub type"
        if ecss_dict['ser_subtype'] == packet_settings.TM_VR_ACCEPTANCE_SUCCESS:
            report = "OK"
        elif ecss_dict['ser_subtype'] == packet_settings.TM_VR_ACCEPTANCE_FAILURE:
            report = "Error " + packet_settings.SAT_RETURN_STATES[ecss_dict['data'][4]]

        text = "ACK {0}, FROM: {1}".format(report, packet_settings.upsat_app_ids[str(ecss_dict['app_id'])])

    elif ecss_dict['ser_type'] == packet_settings.TC_HOUSEKEEPING_SERVICE and ecss_dict['ser_subtype'] == packet_settings.TM_HK_PARAMETERS_REPORT:

        struct_id = ecss_dict['data'][0]

        if ecss_dict['app_id'] == packet_settings.EPS_APP_ID and struct_id == packet_settings.HEALTH_REP:

            report = "data "

        elif ecss_dict['app_id'] == packet_settings.EPS_APP_ID and struct_id == packet_settings.EX_HEALTH_REP:

            pointer = 1
            report = "EX_HEALTH_REP "

            time_obc = cnv8_32(ecss_dict['data'][pointer:]) * 0.001
            pointer += 4
            report += "time " + str(time_obc) + " "

        elif ecss_dict['app_id'] == packet_settings.COMMS_APP_ID and struct_id == packet_settings.HEALTH_REP:

            report = "data "

        elif ecss_dict['app_id'] == packet_settings.COMMS_APP_ID and struct_id == packet_settings.EX_HEALTH_REP:

            pointer = 1
            report = "EX_HEALTH_REP "

            time_obc = cnv8_32(ecss_dict['data'][pointer:]) * 0.001
            pointer += 4
            report += "time " + str(time_obc) + " "

        elif ecss_dict['app_id'] == packet_settings.ADCS_APP_ID and struct_id == packet_settings.EX_HEALTH_REP:

            pointer = 1
            report = "EX_HEALTH_REP "

            time_obc = cnv8_32(ecss_dict['data'][pointer:]) * 0.001
            pointer += 4
            report += "time " + str(time_obc) + " "

        elif ecss_dict['app_id'] == packet_settings.ADCS_APP_ID and struct_id == packet_settings.SU_SCI_HDR_REP:

            pointer = 1
            report = "SU_SCI_HDR_REP "

            roll = cnv_signed_8_16(ecss_dict['data'][pointer:]) * 0.01
            pointer += 2
            report += "roll " + str(roll) + " "

            pitch = cnv_signed_8_16(ecss_dict['data'][pointer:]) * 0.01
            pointer += 2
            report += "pitch " + str(pitch) + " "

            yaw = cnv_signed_8_16(ecss_dict['data'][pointer:]) * 0.01
            pointer += 2
            report += "yaw " + str(yaw) + " "

            roll_dot = cnv_signed_8_16(ecss_dict['data'][pointer:]) * 0.001
            pointer += 2
            report += "roll_dot " + str(roll_dot) + " "

            pitch_dot = cnv_signed_8_16(ecss_dict['data'][pointer:]) * 0.001
            pointer += 2
            report += "pitch_dot " + str(pitch_dot) + " "

            yaw_dot = cnv_signed_8_16(ecss_dict['data'][pointer:]) * 0.001
            pointer += 2
            report += "yaw_dot " + str(yaw_dot) + " "

            x = cnv_signed_8_16(ecss_dict['data'][pointer:]) * 0.5
            pointer += 2
            report += "x " + str(x) + " "

            y = cnv_signed_8_16(ecss_dict['data'][pointer:]) * 0.5
            pointer += 2
            report += "y " + str(y) + " "

            z = cnv_signed_8_16(ecss_dict['data'][pointer:]) * 0.5
            pointer += 2
            report += "z " + str(z) + " "

        elif ecss_dict['app_id'] == packet_settings.OBC_APP_ID and struct_id == packet_settings.EX_HEALTH_REP:

            pointer = 1
            report = "EX_HEALTH_REP "

            time_obc = cnv8_32(ecss_dict['data'][pointer:]) * 0.001
            pointer += 4
            report += "time " + str(time_obc)

        elif struct_id == packet_settings.EXT_WOD_REP:
            pointer = 1
            report = "EXT WOD"

            qb50 = cnv8_32(ecss_dict['data'][pointer:])
            utc = qb50_to_utc(qb50)
            pointer += 4

            obc = cnv8_32(ecss_dict['data'][pointer:]) * 0.001
            pointer += 4
            comms = cnv8_32(ecss_dict['data'][pointer:]) * 0.001
            pointer += 4
            eps = cnv8_32(ecss_dict['data'][pointer:]) * 0.001
            pointer += 4
            adcs = cnv8_32(ecss_dict['data'][pointer:]) * 0.001
            pointer += 4

            task_uart = cnv8_32(ecss_dict['data'][pointer:]) * 0.001
            pointer += 4

            task_idle = cnv8_32(ecss_dict['data'][pointer:]) * 0.001
            pointer += 4

            task_hk = cnv8_32(ecss_dict['data'][pointer:]) * 0.001
            pointer += 4

            task_su = cnv8_32(ecss_dict['data'][pointer:]) * 0.001
            pointer += 4

            task_sch = cnv8_32(ecss_dict['data'][pointer:]) * 0.001
            pointer += 4

            vbat = cnv8_16(ecss_dict['data'][pointer:])
            pointer += 2

            # uart_state = ecss_dict['data'][pointer]
            # pointer += 1

            report += " time " + str(qb50) + "\n" + \
                      " UTC " + str(utc) + "\n" + \
                      " obc " + str(obc) + "\n" + \
                      " comms " + str(comms) + "\n" + \
                      " eps " + str(eps) + "\n" + \
                      " adcs " + str(adcs) + "\n" + \
                      " task_uart " + str(task_uart) + "\n" + \
                      " task_idle " + str(task_idle) + "\n" + \
                      " task_hk " + str(task_hk) + "\n" + \
                      " task_su " + str(task_su) + "\n" + \
                      " task_sch " + str(task_sch) + "\n" + \
                      " vbat " + str(vbat) + "\n"

            # if uart_state == 0x00:
            #     report += " Uart state reset"
            # elif uart_state == 0x20:
            #     report += " Uart state ready"
            # elif uart_state == 0x24:
            #     report += " Uart state busy"
            # elif uart_state == 0x21:
            #     report += " Uart state busy tx"
            # elif uart_state == 0x22:
            #     report += " Uart state busy rx"
            # elif uart_state == 0x23:
            #     report += " Uart state busy tx rx"
            # elif uart_state == 0xA0:
            #     report += " Uart state timeout"
            # elif uart_state == 0xE0:
            #     report += " Uart state error"
            # else:
            #     report += " Uart state unkown: " + str(uart_state)

        text = "HK {0}, FROM: {1}".format(report, packet_settings.upsat_app_ids[str(ecss_dict['app_id'])])

    elif ecss_dict['ser_type'] == packet_settings.TC_EVENT_SERVICE and ecss_dict['ser_subtype'] == packet_settings.TM_EV_NORMAL_REPORT:

        report = ""
        event_id = ecss_dict['data'][0]
        if event_id == packet_settings.EV_sys_boot:
            report = "booted"

        text += "EVENT {0}, FROM: {1}".format(report, packet_settings.upsat_app_ids[str(ecss_dict['app_id'])])

    elif ecss_dict['ser_type'] == packet_settings.TC_FUNCTION_MANAGEMENT_SERVICE:
        # Nothing to do here
        text += "FM {0}, FROM: {1}".format(packet_settings.upsat_app_ids[str(ecss_dict['app_id'])])

    elif ecss_dict['ser_type'] == packet_settings.TC_TIME_MANAGEMENT_SERVICE:

        # Check https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior
        if ecss_dict['ser_subtype'] == packet_settings.TM_TIME_REPORT_IN_UTC:

            wkd = ecss_dict['data'][0]
            day = ecss_dict['data'][1]
            mon = ecss_dict['data'][2]
            year = ecss_dict['data'][3]
            hour = ecss_dict['data'][4]
            mins = ecss_dict['data'][5]
            sec = ecss_dict['data'][6]

            report = str(year) + "-" + str(mon) + "-" + str(day) + " " + str(hour) + ":" + str(mins) + ":" + str(sec) + " wkd:" + str(wkd)

        elif ecss_dict['ser_subtype'] == packet_settings.TM_TIME_REPORT_IN_QB50:

            qb50 = cnv8_32(ecss_dict['data'][0:])
            utc = qb50_to_utc(qb50)
            report = "QB50 " + str(qb50) + " UTC: " + str(utc)

        text = "TIME: {0}, FROM: {1}".format(report, packet_settings.upsat_app_ids[str(ecss_dict['app_id'])])

    elif ecss_dict['ser_type'] == packet_settings.TC_SCHEDULING_SERVICE:
        text = "APO, DO LET US KNOW WHAT TO DO HERE"
    elif ecss_dict['ser_type'] == packet_settings.TC_LARGE_DATA_SERVICE:
        text = "FM {0}, FROM: {1}".format(ecss_dict['app_id'])
    elif ecss_dict['ser_type'] == packet_settings.TC_MASS_STORAGE_SERVICE:

        report = ""
        if ecss_dict['ser_subtype'] == packet_settings.TM_MS_CATALOGUE_REPORT:

            for i in range(0, 7):

                offset = (i * packet_settings.SCRIPT_REPORT_SU_OFFSET)
                valid = ecss_dict['data'][(offset)]
                size = cnv8_32(ecss_dict['data'][(1 + offset):])
                fatfs = cnv8_32(ecss_dict['data'][(5 + offset):])
                time_modfied = fatfs_to_utc(fatfs)

                print "offset: " + str(offset) + " script " + packet_settings.upsat_store_ids[str(i + 1)] + " valid: " + str(valid) + " size: " + str(size) + \
                    " time_modified: " + str(time_modfied)
                print "raw ", ' '.join('{:02x}'.format(x) for x in ecss_dict['data'][(offset):(offset + packet_settings.SCRIPT_REPORT_SU_OFFSET)])

                report += "script " + packet_settings.upsat_store_ids[str(i + 1)] + "\n" + \
                          "valid: " + str(valid) + "\n" + \
                          "size: " + str(size) + "\n" + \
                          "time_modified: " + str(time_modfied) + "\n"

            for i in range(0, 4):

                offset = (7 * packet_settings.SCRIPT_REPORT_SU_OFFSET) + (i * packet_settings.SCRIPT_REPORT_LOGS_OFFSET)

                fnum = cnv8_16(ecss_dict['data'][(offset):])

                fname_tail = cnv8_16(ecss_dict['data'][(2 + offset):])
                tail_size = cnv8_32(ecss_dict['data'][(4 + offset):])
                fatfs_tail = cnv8_32(ecss_dict['data'][(8 + offset):])
                time_modfied_tail = fatfs_to_utc(fatfs_tail)

                fname_head = cnv8_16(ecss_dict['data'][(12 + offset):])
                head_size = cnv8_32(ecss_dict['data'][(14 + offset):])
                fatfs_head = cnv8_32(ecss_dict['data'][(18 + offset):])
                time_modfied_head = fatfs_to_utc(fatfs_head)

                print "offset: " + str(offset) + " script " + packet_settings.upsat_store_ids[str(i + 8)] + " number of files: " + str(fnum) + " tail size: " + str(tail_size) + \
                    " tail time_modfied: " + str(time_modfied_tail) + " head size: " + str(head_size) + " head time_modfied: " + str(time_modfied_head)
                print "raw ", ' '.join('{:02x}'.format(x) for x in ecss_dict['data'][(offset):(offset + packet_settings.SCRIPT_REPORT_LOGS_OFFSET)])

                report += "script " + packet_settings.upsat_store_ids[str(i + 8)] + "\n" + \
                          "number of files: " + str(fnum) + "\n" + \
                          "tail name: " + str(fname_tail) + "\n" + \
                          "tail size: " + str(tail_size) + "\n" + \
                          "tail time_modfied: " + str(time_modfied_tail) + "\n" + \
                          "head name: " + str(fname_head) + "\n" + \
                          "head size: " + str(head_size) + "\n" + \
                          "head time_modfied: " + str(time_modfied_head) + "\n"

        elif ecss_dict['ser_subtype'] == packet_settings.TM_MS_CATALOGUE_LIST:

            sid = ecss_dict['data'][0]
            f_iter = cnv8_16(ecss_dict['data'][1:])

            if sid == packet_settings.SU_LOG or \
               sid == packet_settings.WOD_LOG or \
               sid == packet_settings.EXT_WOD_LOG or \
               sid == packet_settings.EVENT_LOG or \
               sid == packet_settings.FOTOS:

                files = (ecss_dict['size'] - 3) / packet_settings.LOGS_LIST_SIZE

                print "data size is: ", ecss_dict['size'], " ", (ecss_dict['size'] - 3) / packet_settings.LOGS_LIST_SIZE, " ", files
                # If su_logs > MAX_DOWNLINK_SU_LOGS:
                # Error

                ecss_dict['files'] = [0] * files
                ecss_dict['files_sid'] = sid

                report = "received file list, for store " + str(sid) + " with " + str(files) + " files, next file iteration is: " + str(f_iter) + "\n"
                for i in range(0, files):
                    filename = cnv8_16(ecss_dict['data'][(3 + (i * packet_settings.LOGS_LIST_SIZE)):])
                    size = cnv8_32(ecss_dict['data'][(5 + (i * packet_settings.LOGS_LIST_SIZE)):])
                    fatfs = cnv8_32(ecss_dict['data'][(9 + (i * packet_settings.LOGS_LIST_SIZE)):])
                    time_modfied = fatfs_to_utc(fatfs)

                    # Ecss_dict['files'][i]['filename'] = filename
                    # Ecss_dict['files'][i]['time_modfied'] = time_modfied
                    # Ecss_dict['files'][i]['size'] = size

                    report += "file " + str(i) + "\n" + \
                              "filename " + str(filename) + "\n" + \
                              "size " + str(size) + "\n" + \
                              "modified " + str(time_modfied) + "\n"
                print report

            elif sid <= packet_settings.SU_SCRIPT_7:
                report = "received file list, for store " + str(sid) + " you should do a report"

        elif ecss_dict['ser_subtype'] == packet_settings.TM_MS_CONTENT:

            sid = ecss_dict['data'][0]
            fname = cnv8_16(ecss_dict['data'][1:])

            report = "From store: " + packet_settings.upsat_store_ids[str(sid)] + " file " + str(fname)  # + " content " + ecss_dict['data'] + \
            # " " + ' '.join('{:02x}'.format(x) for x in ecss_dict['data']) + "\n"

            if sid == packet_settings.SU_LOG:

                su_logs = 1  # (ecss_dict['size'] - 3) / packet_settings.SU_LOG_SIZE

                # If su_logs > MAX_DOWNLINK_SU_LOGS:
                # Error

                report += " received " + str(su_logs) + " su logs "
                for i in range(0, su_logs):
                    qb50 = cnv8_32(ecss_dict['data'][(3 + (i * packet_settings.SU_LOG_SIZE)):])
                    utc = qb50_to_utc(qb50)
                    report += "SU LOG, with QB50 " + str(qb50) + " UTC: " + str(utc)

            elif sid == packet_settings.WOD_LOG:

                wod_logs = 1  # (ecss_dict['size'] - 3) / packet_settings.SU_LOG_SIZE

                # If su_logs > MAX_DOWNLINK_SU_LOGS:
                # Error

                report += " received " + str(wod_logs) + " wod logs "
                for i in range(0, wod_logs):
                    qb50 = cnv8_32(ecss_dict['data'][(3 + (i * packet_settings.WOD_LOG_SIZE)):])
                    utc = qb50_to_utc(qb50)
                    report += "WOD LOG, with QB50 " + str(qb50) + " UTC: " + str(utc)

            elif sid <= packet_settings.SU_SCRIPT_7:

                sum1 = 0
                sum2 = 0
                size = (ecss_dict['size'] - 3)
                for i in range(3, size):
                    sum1 = (sum1 + ecss_dict['data'][i]) % 255
                    sum2 = (sum2 + sum1) % 255
                if ((sum2 << 8) | sum1) == 0:
                    report += " Checksum ok"
                else:
                    report += " Checksum error"

            timestr = time.strftime("%Y%m%d-%H%M%S")

            fwname = log_path + packet_settings.upsat_store_ids[str(sid)] + "/" + str(fname) + "_" + timestr + ".bin"
            myfile = open(fwname, 'w')
            myfile.write(ecss_dict['data'][3:])
            myfile.close()

        text = "MS {0}, FROM: {1}".format(report, packet_settings.upsat_app_ids[str(ecss_dict['app_id'])])

    elif ecss_dict['ser_type'] == packet_settings.TC_TEST_SERVICE:
        text = "TEST Service from {0}".format(packet_settings.upsat_app_ids[str(ecss_dict['app_id'])])
    elif ecss_dict['ser_type'] == packet_settings.TC_SU_MNLP_SERVICE:
        text = "APO, DO LET US KNOW WHAT TO DO HERE"

    res_dict = {}
    res_dict['id'] = id
    res_dict['log_message'] = text
    res_dict['files'] = []
    return res_dict


def fatfs_to_utc(fatfs):
    return fatfs


def qb50_to_utc(qb50):
    utc = datetime.datetime.fromtimestamp(qb50 + 946684800).strftime("%A, %d. %B %Y %H:%M:%S")
    return utc


def cnv32_8(inc):

    ret = [0] * 4

    ret[0] = inc & 0x000000FF
    ret[1] = (inc >> 8) & 0x000000FF
    ret[2] = (inc >> 16) & 0x000000FF
    ret[3] = (inc >> 24) & 0x000000FF
    return ret


def cnv16_8(inc):

    ret = [0] * 2

    ret[0] = inc & 0x00FF
    ret[1] = (inc >> 8) & 0x00FF
    return ret


def cnv8_32(inc):
    return ((inc[3] << 24) | (inc[2] << 16) | (inc[1] << 8) | (inc[0]))


def cnv8_16(inc):
    return ((inc[1] << 8) | (inc[0]))


def cnv_signed_8_32(inc):
    res = ((inc[3] << 24) | (inc[2] << 16) | (inc[1] << 8) | (inc[0]))
    if (res >> 31) == 1:
        res = (0xFFFFFFFF - res) * -1
    return res


def cnv_signed_8_16(inc):
    res = ((inc[1] << 8) | (inc[0]))
    if (res >> 15) == 1:
        res = (0xFFFF - res) * -1
    return res
