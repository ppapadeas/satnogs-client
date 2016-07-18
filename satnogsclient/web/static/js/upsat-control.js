$(document).ready(function() {
    init();

    $("[name='backend-switch']").on('switchChange.bootstrapSwitch', function(event, state) {
        if (state) {
          mode = 'gnuradio';
        }
        else {
          mode = 'serial';
        }
        Cookies.set('backend', mode);
        request = encode_backend_mode(mode);
        query_control_backend(request, 'POST', '/command', "application/json; charset=utf-8", "json", true);
    });

    $('#service-select li').on('click', function() {
        // Handle change on service parameter dropdowns
        selected_service_id = $(this).prop('id');
        $(this).addClass('active');
        display_service(selected_service_id);
    });

    $('#service-param-sch-service-type').on('change', function() {
        // Handle change on service parameter dropdowns
        var subservice = $(this).find("option:selected").text();
        var select = $('#service-param-sch-service-subtype');
        update_subservice(subservice, select);
    });

    $('#service-param-service_type').on('change', function() {
        // Handle change on service parameter dropdowns
        var subservice = $(this).find("option:selected").text();
        var select = $('#service-param-service_subtype');
        update_subservice(subservice, select);
    });

    $('#service-param-time-report').on('change', function() {
        if ($('#service-param-time-report').find("option:selected").val() == "manual") {
            $('#datetimepicker-time-row').show();
        } else {
            $('#datetimepicker-time-row').hide();
        }
    });

    $('#service-param-ms-function').on('change', function() {
        if ($('#service-param-ms-function').find("option:selected").val() == "File_system") {
            $('#file-action-row').show();
        } else {
            $('#file-action-row').hide();
            $('#file-upload-row').hide();
            $('#file-select-row').hide();
            $('#folder-select-row').hide();
        }
    });

    $('#service-param-ms-action').on('change', function() {
        if ($('#service-param-ms-action').find("option:selected").val() == "Uplink") {
            $('#file-upload-row').show();
            $('#file-select-row').hide();
            $('#folder-select-row').show();
        } else if ($('#service-param-ms-action').find("option:selected").val() == "Delete" ||
                   $('#service-param-ms-action').find("option:selected").val() == "List" ||
                   $('#service-param-ms-action').find("option:selected").val() == "Downlink") {
             $('#file-upload-row').hide();
             $('#file-select-row').show();
             $('#folder-select-row').show();
        } else if ($('#service-param-ms-action').find("option:selected").val() == "All" ||
                   $('#service-param-ms-action').find("option:selected").val() == "Hard") {
             $('#file-upload-row').hide();
             $('#file-select-row').hide();
             $('#folder-select-row').show();
        } else {
            $('#file-upload-row').hide();
            $('#file-select-row').hide();
            $('#folder-select-row').hide();
        }
    });

    $('#service-param-panel :button').on('click', function() {

        var list = $('this').parent().siblings().find('select');
        var selected_value = $('#service-select li.active').attr("data-value");
        data = [];
        //TODO: Check whether all required fields are selected
        var missing = [];
        for (i = 0; i < list.length; i++) {
            if (isNaN(list[i].value)) {
                missing.push(list[i].value);
                flag = false;
            }
        }

        var app_id = 0;
        var type = 0;
        var ack = 0;
        var service_type = 0;
        var service_subtype = 0;
        var dest_id = 0;
        var data = 0;

        if (selected_value == "custom") {
            app_id = $('#service-param-app_id').val();
            type = $('#service-param-type').val();
            ack = $('#service-param-ack').val();
            service_type = $('#service-param-service_type').val();
            service_subtype = $('#service-param-service_subtype').val();
            dest_id = $('#service-param-dest_id').val();
            data = $('#service-param-service-data').val().split(",");
            seq_count = 0;

            request = encode_service(type, app_id, service_type, service_subtype, dest_id, ack, data);
            query_control_backend(request, 'POST', '/command', "application/json; charset=utf-8", "json", true);

        } else if (selected_value == "house") {
            app_id = $('#service-param-hk-app_id').val();
            type = 1;
            ack = 0;
            service_type = 3;
            service_subtype = 21;
            dest_id = $('#service-param-hk-dest-id').val();

            data = $('#service-param-hk-sid').val();
            request = encode_service(type, app_id, service_type, service_subtype, dest_id, ack, data);
            query_control_backend(request, 'POST', '/command', "application/json; charset=utf-8", "json", true);


        } else if (selected_value == "mass") {

            app_id = 1;
            type = 1;
            ack = $('#service-param-ms-ack').val();
            dest_id = $('#service-param-ms-dest-id').val();
            service_type = 15;
            data = [];

            var store_id = $('#service-param-ms-sid').val();

            var fun = $('#service-param-ms-function').val();

            if(fun == "Format") {
                if (confirm('Are you sure you want to format the sd?')) {
                    service_subtype = 15;
                } else {
                    return 0;
                }
            } else if(fun == "File_system") {

                var action = $('#service-param-ms-action').val();

                if(action == "Report") {

                    service_subtype = 12;

                } else if(action == "List") {

                    var fn_list = $('#service-param-service-ms-num').val();
                    service_subtype = 16;

                    data.splice(0, 0, store_id);
                    data.splice(1, 0, ((fn_list >> 8) & 0x00FF)); // next file
                    data.splice(2, 0, ((fn_list >> 0) & 0x00FF));

                } else if(action == "Downlink") {

                    var fn_down = $('#service-param-service-ms-num').val();
                    service_subtype = 9;

                    data.splice(0, 0, store_id);
                    data.splice(1, 0, ((fn_down >> 8) & 0x00FF)); // file from
                    data.splice(2, 0, ((fn_down >> 0) & 0x00FF));
                    data.splice(3, 0, 1); // num of files

                } else if(action == "Uplink") {

                       var file = $('#service-param-service-ms-num').val();
                       service_subtype = 14;

                       file_encode_and_query_backend(type, app_id, service_type, service_subtype, dest_id, ack, store_id, file);
                       return 0;

                } else if(action == "Delete") {

                    var fn_del = $('#service-param-service-ms-num').val();
                    service_subtype = 11;
                    data.splice(0, 0, store_id);
                    data.splice(1, 0, 0); //mode != 6
                    data.splice(2, 0, ((fn_del >> 8) & 0x00FF)); // num of files
                    data.splice(3, 0, ((fn_del >> 0) & 0x00FF));

                } else if(action == "Hard") {

                    service_subtype = 11;
                    data.splice(0, 0, store_id);
                    data.splice(1, 0, 6);  // 6 is hard delete mode

                } else if(action == "Reset") {

                    service_subtype = 11;
                    data.splice(0, 0, store_id);
                    data.splice(1, 0, 8);  // 8 is the reset fat fs mode

                } else if(action == "All") {

                    service_subtype = 11;
                    data.splice(0, 0, store_id);
                    data.splice(1, 0, 7);  // 7 is delete all mode
                    data.splice(2, 0, 0); // pads for keeping same format as delete
                    data.splice(3, 0, 0);
                }
             }
        //      else if(fun == "Enable") {
        //       continue;
        //     }

            request = encode_service(type, app_id, service_type, service_subtype, dest_id, ack, data);
            query_control_backend(request, 'POST', '/command', "application/json; charset=utf-8", "json", true);

        } else if (selected_value == "power") {

            dev_id = $('#service-param-dev-id').val();
            type = 1;
            ack = $('#service-param-power-ack').val();

            service_type = 8;
            service_subtype = 1;
            dest_id = $('#service-param-power-dest_id').val();

            if (dev_id == 1) {
                app_id = 2;
            } else if (dev_id == 2) {
                app_id = 2;
            } else if (dev_id == 3) {
                app_id = 2;
            } else if (dev_id == 4) {
                app_id = 2;
            } else if (dev_id == 5) {
                app_id = 1;
            } else if (dev_id == 6) {
                app_id = 2;
            } else if (dev_id == 7) {
                app_id = 3;
            } else if (dev_id == 8) {
                app_id = 1;
            } else if (dev_id == 9) {
                app_id = 3;
            } else if (dev_id == 10) {
                app_id = 3;
            } else if (dev_id == 11) {
                app_id = 3;
            } else if (dev_id == 12) {
                app_id = 3;
            } else if (dev_id == 13) {
                app_id = 3;
            } else if (dev_id == 14) {
                app_id = 3;
            } else if (dev_id == 15) {
                app_id = 3;
            }

            var fun_id = $('#service-param-function').val();
            data = [fun_id, dev_id];

            request = encode_service(type, app_id, service_type, service_subtype, dest_id, ack, data);
            query_control_backend(request, 'POST', '/command', "application/json; charset=utf-8", "json", true);

        } else if (selected_value == "test") {
            app_id = $('#service-param-test-app_id').val();
            type = 1;
            ack = 0;

            service_type = 17;
            service_subtype = 1;
            dest_id = $('#service-param-test-dest_id').val();
            data = [];

            request = encode_service(type, app_id, service_type, service_subtype, dest_id, ack, data);
            query_control_backend(request, 'POST', '/command', "application/json; charset=utf-8", "json", true);

          } else if (selected_value == "time") {
              app_id = $('#service-param-time-app_id').val();
              type = 1;
              ack = 0;
              data = [];
              service_type = 9;
              dest_id = $('#service-param-time-dest_id').val();

              selected_action = $('#service-param-time-report').find("option:selected").val();

              var weekday;

              if (selected_action == 'manual') {
                  service_subtype = 1;

                  var datetime = datepicker_time.data("DateTimePicker").date();
                  dateutc = datetime;

                  if (dateutc.day() === 0) {
                    weekday = 7;
                  } else {
                    weekday = dateutc.day();
                  }

                  data.splice(0, 0, weekday);
                  data.splice(1, 0, dateutc.date());
                  data.splice(2, 0, dateutc.month() + 1);  // 7 is delete all mode
                  data.splice(3, 0, dateutc.year() - 2000); // pads for keeping same format as delete
                  data.splice(4, 0, dateutc.hour());
                  data.splice(5, 0, dateutc.minute());
                  data.splice(6, 0, dateutc.seconds());
              } else if (selected_action == 'auto') {

                  service_subtype = 1;
                  dateutc = moment();

                  if (dateutc.day() === 0) {
                    weekday = 7;
                  } else {
                    weekday = dateutc.day();
                  }

                  data.splice(0, 0, weekday);
                  data.splice(1, 0, dateutc.date());
                  data.splice(2, 0, dateutc.month() + 1);  // 7 is delete all mode
                  data.splice(3, 0, dateutc.year() - 2000); // pads for keeping same format as delete
                  data.splice(4, 0, dateutc.hour());
                  data.splice(5, 0, dateutc.minute());
                  data.splice(6, 0, dateutc.seconds());
              } else if (selected_action == 'utc') {
                  service_subtype = 3;
              } else if (selected_action == 'qb50') {
                  service_subtype = 4;
              } else {
                  return 0;
              }

              request = encode_service(type, app_id, service_type, service_subtype, dest_id, ack, data);
              query_control_backend(request, 'POST', '/command', "application/json; charset=utf-8", "json", true);

          } else if (selected_value == "adcs") {
            // TODO: Is app_id needed in time service?
            //app_id = $('#service-param-time-app_id').val();
            app_id = 7;
            type = 0;
            ack = 0;

            service_type = 3;
            service_subtype = 23;
            dest_id = 3;

            data = [];
            ascii_to_dec($('#service-param-service-tle').val().split(''), data);
            data.unshift(6);
            //number of TLE chanacters
            if (data.length != 137) {
                alert("TLE shouldnt be: " + data.length);
                return 0;
            }

            request = encode_service(type, app_id, service_type, service_subtype, dest_id, ack, data);
            query_control_backend(request, 'POST', '/command', "application/json; charset=utf-8", "json", true);

        } else if (selected_value == "comms") {
            if ($(this).attr("id") == "comms-tx-on") {
                request = encode_comms_tx_rf(1);
                query_control_backend(request, 'POST', '/command', "application/json; charset=utf-8", "json", true);
            } else if ($(this).attr("id") == "comms-tx-off") {
                request = encode_comms_tx_rf(0);
                query_control_backend(request, 'POST', '/command', "application/json; charset=utf-8", "json", true);
            }
        }
    });

    $("#time-radio").change(function() {
        // If checkbox not checked already
        if ($('input[name=power-radio]').prop('checked') === true) {
            var elem = document.getElementById('subservice-params-time');
            var elem2 = document.getElementById('subservice-params-power');
            elem.style.display = "block";
            elem2.style.display = "none";
            $('input[name=power-radio]').prop('checked', false);
            // TODO: Uncheck every other radio
        }
    });

    $('#filter-section input').on('change', function() {
        var itemsToFilter = $('#response-panel-body ul li');
        for (var i = 0; i < itemsToFilter.length; i++) {
            var currentItem = itemsToFilter[i];
            if (currentItem.getAttribute("data-type") == $(this).val()) {
                if ($(this).is(':checked')) {
                    currentItem.classList.remove('hide-log');
                    currentItem.classList.add('show-log');
                } else {
                    currentItem.classList.remove('show-log');
                    currentItem.classList.add('hide-log');
                }
            }
        }
    });

    $('#clear-log').on('click', function() {
      var itemsToFilter = $('#response-panel-body ul li');
      for (var i = 0; i < itemsToFilter.length; i++) {
        var currentItem = itemsToFilter[i];
        currentItem.remove();
      }
    });

    $("#mode-switch li").click(function() {
        var current_mode = $(this).attr("data-value");
        var current_backend = Cookies.get('backend');
        if (current_backend === null || typeof current_backend == 'undefined') {
          current_backend = 'gnuradio';
          Cookies.set('backend', current_backend);
          request = encode_backend_mode(current_backend);
          query_control_backend(request, 'POST', '/command', "application/json; charset=utf-8", "json", true);
        }
        //request = encode_mode_switch(current_mode);
        //query_control_backend(request, 'POST', '/command', "application/json; charset=utf-8", "json", true);
        display_control_view(current_mode,current_backend);
    });

});

function display_service(selection) {
    var services = {
        'custom-select': 'service-param-custom',
        'power-select': 'service-param-power',
        'test-select': 'service-param-test',
        'time-select': 'service-param-time',
        'tle-select': 'service-param-tle',
        'ms-select': 'service-param-mass-storage',
        'comms-select': 'service-param-comms',
        'hk-select': 'service-param-housekeeping',
        'sch-select': 'service-param-schedule'
    };
    var keys = [];
    for (var key in services) {
        var elem = document.getElementById(services[key]);
        var service_param_panel = document.getElementById('service-param-panel');
        var service_select = document.getElementById(key);
        if (key == selection) {
            elem.style.display = "block";
            service_param_panel.style.backgroundColor = '#f8f8f8';
        } else {
            elem.style.display = "none";
            service_select.classList.remove('active');
        }
    }
}

function ascii_to_dec(inc, out) {
    for (var i = 0; i < inc.length; i++) {
        out[i] = inc[i].charCodeAt(0);
    }
}

function update_subservice(subservice, select) {

        var VR_SERVICE = {
            TM_VR_ACCEPTANCE_SUCCESS: 1,
            TM_VR_ACCEPTANCE_FAILURE: 2
        };

        var HK_SERVICE = {
            TC_HK_REPORT_PARAMETERS: 21,
            TM_HK_PARAMETERS_REPORT: 23
        };

        var EV_SERVICE = {
            TM_EV_NORMAL_REPORT: 1,
            TM_EV_ERROR_REPORT: 4
        };

        var FM_SERVICE = {
            TC_FM_PERFORM_FUNCTION: 1
        };

        var SC_SERVICE = {
            TC_SC_ENABLE_RELEASE: 1,
            TC_SC_DISABLE_RELEASE: 2,
            TC_SC_RESET_SCHEDULE: 3,
            TC_SC_INSERT_TC: 4,
            TC_SC_DELETE_TC: 5,
            TC_SC_TIME_SHIFT_SPECIFIC: 7,
            TC_SC_TIME_SHIFT_SELECTED_OTP: 8,
            TC_SC_TIME_SHIFT_ALL: 15
        };

        var LD_SERVICE = {
            TM_LD_FIRST_DOWNLINK: 1,
            TC_LD_FIRST_UPLINK: 9,
            TM_LD_INT_DOWNLINK: 2,
            TC_LD_INT_UPLINK: 10,
            TM_LD_LAST_DOWNLINK: 3,
            TC_LD_LAST_UPLINK: 11,
            TC_LD_ACK_DOWNLINK: 5,
            TM_LD_ACK_UPLINK: 14,
            TC_LD_REPEAT_DOWNLINK: 6,
            TM_LD_REPEAT_UPLINK: 15,
            TM_LD_REPEATED_DOWNLINK: 7,
            TC_LD_REPEATED_UPLINK: 12,
            TM_LD_ABORT_SE_DOWNLINK: 4,
            TC_LD_ABORT_SE_UPLINK: 13,
            TC_LD_ABORT_RE_DOWNLINK: 8,
            TM_LD_ABORT_RE_UPLINK: 16
        };

        var MS_SERVICE = {
            TC_MS_ENABLE: 1,
            TC_MS_DISABLE: 2,
            TC_MS_CONTENT: 8,
            TC_MS_DOWNLINK: 9,
            TC_MS_DELETE: 11,
            TC_MS_REPORT: 12,
            TM_MS_CATALOGUE_REPORT: 13,
            TC_MS_UPLINK: 14,
            TC_MS_FORMAT: 15
        };

        var CT_SERVICE = {
            TC_CT_PERFORM_TEST: 1,
            TM_CT_REPORT_TEST: 2
        };

        select.find('option').remove();
        select.append('<option selected="true" style="display:none;">Service sub Type</option>');

        var key;
        if (subservice == "TC_VERIFICATION_SERVICE") {
            for (key in VR_SERVICE) {
                select.append('<option value=' + VR_SERVICE[key] + '>' + key + '</option>');
            }
        } else if (subservice == "TC_HOUSEKEEPING_SERVICE") {
            for (key in HK_SERVICE) {
                select.append('<option value=' + HK_SERVICE[key] + '>' + key + '</option>');
            }
        } else if (subservice == "TC_EVENT_SERVICE") {
            for (key in EV_SERVICE) {
                select.append('<option value=' + EV_SERVICE[key] + '>' + key + '</option>');
            }
        } else if (subservice == "TC_FUNCTION_MANAGEMENT_SERVICE") {
            for (key in FM_SERVICE) {
                select.append('<option value=' + FM_SERVICE[key] + '>' + key + '</option>');
            }
        } else if (subservice == "TC_TIME_MANAGEMENT_SERVICE") {
            for (key in VR_SERVICE) {
                select.append('<option value=' + VR_SERVICE[key] + '>' + key + '</option>');
            }
        } else if (subservice == "TC_SCHEDULING_SERVICE") {
            for (key in SC_SERVICE) {
                select.append('<option value=' + SC_SERVICE[key] + '>' + key + '</option>');
            }
        } else if (subservice == "TC_LARGE_DATA_SERVICE") {
            for (key in LD_SERVICE) {
                select.append('<option value=' + LD_SERVICE[key] + '>' + key + '</option>');
            }
        } else if (subservice == "TC_MASS_STORAGE_SERVICE") {
            for (key in MS_SERVICE) {
                select.append('<option value=' + MS_SERVICE[key] + '>' + key + '</option>');
            }
        } else if (subservice == "TC_TEST_SERVICE") {
            for (key in CT_SERVICE) {
                select.append('<option value=' + CT_SERVICE[key] + '>' + key + '</option>');
            }
        } else if (subservice == "TC_SU_MNLP_SERVICE") {
            for (key in VR_SERVICE) {
                select.append('<option value=' + VR_SERVICE[key] + '>' + key + '</option>');
            }
        }
}

function encode_service(type, app_id, service_type, service_subtype, dest_id, ack, data, seq_count) {
    var DataFieldHeader = {};
    DataFieldHeader.CCSDSSecondaryHeaderFlag = '0';
    DataFieldHeader.TCPacketPUSVersionNumber = '1';
    DataFieldHeader.Ack = ack;
    DataFieldHeader.ServiceType = service_type;
    DataFieldHeader.ServiceSubType = service_subtype;
    DataFieldHeader.SourceID = dest_id;
    DataFieldHeader.Spare = '0';

    var PacketID = {};
    PacketID.VersionNumber = '0';
    PacketID.Type = type;
    PacketID.DataFieldHeaderFlag = '1';
    PacketID.ApplicationProcessID = app_id;

    var PacketSequenceControl = {};
    PacketSequenceControl.SequenceFlags = '3';


    if (typeof seq_count != "undefined") {
        PacketSequenceControl.SequenceCount = seq_count;
    }

    var PacketDataField = {};
    PacketDataField.DataFieldHeader = DataFieldHeader;
    if (data) {
        PacketDataField.ApplicationData = data;
    } else {
        PacketDataField.ApplicationData = '';
    }
    PacketDataField.Spare = '0';
    PacketDataField.PacketErrorControl = '5';

    var PacketHeader = {};
    PacketHeader.PacketID = PacketID;
    PacketHeader.PacketSequenceControl = PacketSequenceControl;
    PacketHeader.PacketLength = '66';

    var TestServicePacket = {};
    TestServicePacket.PacketHeader = PacketHeader;
    TestServicePacket.PacketDataField = PacketDataField;

    var ecss_cmd = {};
    ecss_cmd.ecss_cmd = TestServicePacket;

    console.log(JSON.stringify(ecss_cmd));
    var json_packet = JSON.stringify(ecss_cmd);
    return json_packet;
}

function encode_comms_tx_rf(status) {
    var response = {};
    var custom_cmd = {};
    var comms_tx_rf = {};
    if (status) {
        custom_cmd.comms_tx_rf = 'comms_on';
    } else {
        custom_cmd.comms_tx_rf = 'comms_off';
    }
    response.custom_cmd = custom_cmd;
    console.log(JSON.stringify(response));
    var json_packet = JSON.stringify(response);
    return json_packet;
}

function encode_backend_mode(mode) {
    var response = {};
    var custom_cmd = {};
    var backend = {};
    if (mode == "gnuradio") {
        custom_cmd.backend = 'gnuradio';
    } else if (mode == "serial") {
        custom_cmd.backend = 'serial';
    }
    response.custom_cmd = custom_cmd;
    console.log(JSON.stringify(response));
    var json_packet = JSON.stringify(response);
    return json_packet;
}

function print_command_response(data) {
    var response_panel = $('#response-panel-body ul');
    var data_type;
    console.log(JSON.stringify(data));

    for(var key in data) {
        var resp = data[key];

        var log_data = "";

        if (resp.id == 1) {
            data_type = 'cmd';
            log_data = resp.log_message;
        } else if (resp.id == 2) {
            data_type = 'ecss';
            log_data = resp.log_message;
        } else {
            data_type = 'other';
            log_data = resp.log_message;
            current_mode = Cookies.get('mode');
            if (current_mode !== null && typeof current_mode != 'undefined') {
              request = encode_mode_switch(current_mode);
              query_control_backend(request, 'POST', '/command', "application/json; charset=utf-8", "json", true);
            }
            log_data = log_data.split("\n").join("<br>");
        }

        //Check if log is just hearbeat
        if (resp.log_message == 'backend_online') {
            console.log('backend reported online');
            $('#backend_online').html('backend reported <span data-livestamp="'+moment().toString()+'"></span>');
        } else {
            response_panel.append('<li class="' + apply_log_filter(data_type) + '"' + ' data-type="' + data_type + '">' +
            '<span class="label label-default" title="' + moment().format('YYYY/MM/DD').toString() + '">' + moment().format('HH:mm:ss').toString() + '</span> ' + log_data + '</li>');
     	}
    }
    $('#response-panel-body').scrollTop(response_panel.height());
}

//A function that returns the appropriate class based on the applied filters
function apply_log_filter(log_data_type) {
    var status = $('#filter-section :input[value=' + log_data_type + ']').is(':checked');
    if (status) {
        return 'show-log';
    } else {
        return 'hide-log';
    }
}

function query_control_backend(data, post_mode, url, content_type, data_type, process_data) {
    $.ajax({
        type: post_mode,
        url: url,
        contentType: content_type,
        dataType: data_type,
        data: data,
        processData: process_data,
        success: function(data) {
            print_command_response(data);
        },
        error: function(data) {}
    });
}

function display_control_view(mode, backend) {
    if (mode == 'Network') {
        // Disable Upsat Command and Control
        $('#cnc_mode').css('display', 'none');
        $('#backend-switch').css('display', 'none');
        $('#network_mode').css('display', 'block');
    } else if (mode == 'Stand-Alone') {
        // Enable Upsat Command and Control
        $('#cnc_mode').css('display', 'block');
        $('#backend-switch').css('display', 'block');
        $('#network_mode').css('display', 'none');
    }
    if (backend == 'gnuradio') {
        // Enable GNURadio on Upsat Command and Control
        $("[name='backend-switch']").bootstrapSwitch('state',true);
    } else if (backend == 'serial') {
        // Enable Serial on Upsat Command and Control
        $("[name='backend-switch']").bootstrapSwitch('state',false);
    }
}

//Retrieve file encode command and post the request
function file_encode_and_query_backend(type, app_id, service_type, service_subtype, dest_id, ack, store_id, file) {
  input = document.getElementById('file-upload');
  file = input.files[0];
  reader = new FileReader();
  reader.readAsBinaryString(file.slice());
  reader.onloadend = function(evt) {
    if (evt.target.readyState == FileReader.DONE) {
      data = [];
      result = evt.target.result;
      ascii_to_dec(result,data);

      data.unshift((file >> 0) & 0x00FF); // file to uplink, applicable only to sch sid.
      data.unshift((file >> 8) & 0x00FF); //unshifts inserts to first of the array so the order is reversed
                                          //first the file and then the sid so the array is [sid][file (2 bytes)][data (x bytes)]
      data.unshift(store_id);
      console.log(data);
      request = encode_service(type, app_id, service_type, service_subtype, dest_id, ack, data);
      query_control_backend(request, 'POST', '/command', "application/json; charset=utf-8", "json", true);
    }
  };
}

function init() {

    // Various variable definition
    var app_id, type, ack, service_type, service_subtype, dest_id, data, seq_count;

    // Initialize bootstrap-switch
    backend_switch = $("[name='backend-switch']");
    backend_switch.bootstrapSwitch.defaults.size = 'normal';
    backend_switch.bootstrapSwitch.defaults.onColor = 'success';
    backend_switch.bootstrapSwitch.defaults.offColor = 'danger';
    backend_switch.bootstrapSwitch.defaults.onText = 'GNURadio';
    backend_switch.bootstrapSwitch.defaults.offText = 'Serial';
    backend_switch.bootstrapSwitch.defaults.labelWidth = 1;
    backend_switch.bootstrapSwitch();

    // Set initial back-end mode
    current_backend = Cookies.get('backend');
    if (current_backend === null || typeof current_backend == 'undefined') {
      current_backend = 'gnuradio';
      Cookies.set('backend', current_backend);
    }

    current_mode = Cookies.get('mode');
    if (current_mode === null || typeof current_mode == 'undefined') {
      current_mode = "Network";
      Cookies.set('mode', current_mode);
    }

    display_control_view(current_mode, current_backend);

    // Send a request to backend in order to configure mode.
    request = encode_backend_mode(current_backend);
    query_control_backend(request, 'POST', '/command', "application/json; charset=utf-8", "json", true);

    // Send a request to backend in order to configure mode.
    request = encode_mode_switch(current_mode);
    query_control_backend(request, 'POST', '/command', "application/json; charset=utf-8", "json", true);

    // Setup the periodic packet polling
    setInterval(function() {
        query_control_backend({}, 'POST', '/control_rx', "application/json; charset=utf-8", "json", true);
    }, 10000);

    // Setup the datetimepicker
    datepicker_time = $('#datetimepicker-time').datetimepicker({
        format: 'DD-MM-YYYY HH:mm:ss',
    });

        // Setup the datetimepicker
    datepicker_sch = $('#datetimepicker-sch').datetimepicker({
        format: 'DD-MM-YYYY HH:mm:ss',
    });

    $('#datetimepicker-time-row').hide();
    $('#file-upload-row').hide();
    $('#file-select-row').hide();
    $('#file-action-row').hide();
    $('#folder-select-row').hide();
}

function encode_mode_switch(mode) {
  var response = {};
  var custom_cmd = {};
  var comms_tx_rf = {};
  if (mode == "Stand-Alone") {
      custom_cmd.mode = 'cmd_ctrl';
  }
  else if (mode == "Network") {
      custom_cmd.mode = 'network';
  }
  response.custom_cmd = custom_cmd;
  console.log(JSON.stringify(response));
  var json_packet = JSON.stringify(response);
  return json_packet;
}
