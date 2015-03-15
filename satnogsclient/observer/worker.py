# -*- coding: utf-8 -*-
import threading
import time

from datetime import datetime

import pytz

from satnogsclient import settings
from satnogsclient.observer.commsocket import Commsocket
from satnogsclient.observer.orbital import pinpoint


class Worker:
    """Class to facilitate as a worker for rotctl/rigctl."""

    # sockets to connect to
    _ROT_IP = None
    _ROT_PORT = None

    _RIG_IP = None
    _RIG_PORT = None

    # sleep time of loop
    SLEEP_TIME = 0.1  # in seconds

    # refresh tracking info every n loops
    REFRESH_TRACKING_INTERVAL = 10

    # loop flag
    _stay_alive = False

    # debug flag
    _debugmode = False

    # end when this timestamp is reached
    _observation_end = None

    # frequency of original signal
    _frequency = None

    observer_dict = {}
    satellite_dict = {}

    def __init__(self, rotip=None, rotport=None, rigip=None, rigport=None, frequency=None, time_to_stop=None):
        if rotip:
            self._ROT_IP = rotip
        if rotport:
            self._ROT_PORT = rotport
        if rigip:
            self._RIG_IP = rigip
        if rigport:
            self._RIG_PORT = rigport
        if frequency:
            self._frequency = frequency
        if time_to_stop:
            self._observation_end = time_to_stop

    def isalive(self):
        """Returns if tracking loop is alive or not."""
        return self._stay_alive

    def trackobject(self, observer_dict, satellite_dict):
        """
        Sets tracking object.
        Can also be called while tracking, to manipulate observation.
        """
        self.observer_dict = observer_dict
        self.satellite_dict = satellite_dict

    def trackstart(self):
        """
        Starts the thread that communicates info to remote sockets.
        Stops by calling trackstop()
        """
        self._stay_alive = True

        if not all([self.observer_dict, self.satellite_dict]):
            raise ValueError('Satellite or observer dictionary not defined.')

        t = threading.Thread(target=self._communicate_tracking_info)
        t.daemon = True
        t.start()

        return True

    def _communicate_tracking_info(self):
        """
        Runs as a daemon thread, communicating tracking info to remote socket.
        Uses observer and satellite objects set by trackobject().
        Will exit when observation_end timestamp is reached.
        """
        if self._debugmode:
            print(('alive:', self._stay_alive))
        else:
            sock = Commsocket()
            sock.connect(self._IP, self._PORT)  # change to correct address

        loop_count = 0

        # track satellite
        while self._stay_alive:

            # check if we need to exit
            self.check_observation_end_reached()

            if self._debugmode:
                print(('Tracking', self.satellite_dict['tle0']))
                print('from', self.observer_dict['elev'])
            else:
                p = pinpoint(self.observer_dict, self.satellite_dict)
                if p['ok']:
                    self.send_to_socket_rig(p, sock)
                    loop_count += 1
                    if loop_count >= self.REFRESH_TRACKING_INTERVAL:
                        self.send_to_socket_rot(p, sock)
                        loop_count = 0
                    time.sleep(self.SLEEP_TIME)

        if self._debugmode:
            print('Worker thread exited.')
        else:
            sock.disconnect()

    def trackstop(self):
        """ Sets object flag to false and stops the tracking thread.
        """
        self._stay_alive = False
        ## Need to stop receiver instance from here.
        ## Suggestion: pass receiver object to init and keep it as a reference
        ## so we can call receiver.stop() directly

    def check_observation_end_reached(self):
        if datetime.now(pytz.utc) > self._observation_end:
            self.trackstop()

    def send_to_socket_rot(self, p, sock):
        az = p['az'].conjugate()
        alt = p['alt'].conjugate()
        msg = 'P {0} {1}\n'.format(az, alt)
        sock.send(msg)

    def send_to_socket_rig(self, p, sock):
        msg = 'F{0}\n'.format(self._frequency)
        sock.send(msg)
