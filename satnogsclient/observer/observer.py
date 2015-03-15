# -*- coding: utf-8 -*-
from satnogsclient import settings
from satnogsclient.observer.worker import WorkerFreq, WorkerTrack
from satnogsclient.receiver import SignalReceiver

from time import sleep


class Observer:

    _observation_id = None
    _tle = None
    _observation_end = None
    _frequency = None

    _location = None

    _rot_ip = settings.ROT_IP
    _rot_port = settings.ROT_PORT

    _rig_ip = settings.RIG_IP
    _rig_port = settings.RIG_PORT

    ## Variables from settings
    ## Mainly present so we can support multiple ground stations from the client

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, location):
        self._location = location

    @property
    def rot_ip(self):
        return self._rot_ip

    @rot_ip.setter
    def rot_ip(self, ip):
        self._rot_ip = ip

    @property
    def rot_port(self):
        return self._rot_port

    @rot_port.setter
    def rot_port(self, port):
        self._rot_port = port

    @property
    def rig_ip(self):
        return self._rig_ip

    @rig_ip.setter
    def rig_ip(self, ip):
        self._rig_ip = ip

    @property
    def rig_port(self):
        return self._rig_port

    @rig_port.setter
    def rig_port(self, port):
        self._rig_port = port

    ## Passed variables

    @property
    def observation_id(self):
        return self._observation_id

    @observation_id.setter
    def observation_id(self, observation_id):
        self._observation_id = observation_id

    @property
    def tle(self):
        return self._tle

    @tle.setter
    def tle(self, tle):
        self._tle = tle

    @property
    def observation_end(self):
        return self._observation_end

    @observation_end.setter
    def observation_end(self, timestamp):
        self._observation_end = timestamp

    @property
    def frequency(self):
        return self._frequency

    @frequency.setter
    def frequency(self, frequency):
        self._frequency = frequency

    def setup(self, observation_id, tle, observation_end, frequency, obj):
        """
        Sets up required internal variables.
        returns True if setup is ok
        returns False if setup had problems
        """

        # Set attributes
        self.observation_id = observation_id
        self.tle = tle
        self.observation_end = observation_end
        self.frequency = frequency

        self._extract_receiver_variables(obj)

        return all([self.observation_id, self.tle, self.observation_end, self.frequency])

    def _extract_receiver_variables(self, obj):
        self._decoding = obj.get('decoding', None)
        self._ppm_error = obj.get('ppm_error', None)
        self._pcm_demodulator = obj.get('demodulator', None)
        self._modulation = obj.get('modulation', None)
        self._sample_rate = obj.get('sample_rate', None)
        self._aprs = obj.get('aprs', None)

    def observe(self):
        """Starts threads for rotcrl and rigctl."""

        # Instantiate receiver
        self.run_receiver()

        # start thread for rotctl
        self.run_rot()

        # start thread for rigctl
        self.run_rig()

    def run_receiver(self):
        decoding = self._decoding if self._decoding else None

        kwargs = {}
        if self._ppm_error:
            kwargs['ppm_error'] = self._ppm_error
        if self._pcm_demodulator:
            kwargs['pcm_demodulator'] = self._pcm_demodulator
        if self._modulation:
            kwargs['modulation'] = self._modulation
        if self._sample_rate:
            kwargs['sample_rate'] = self._sample_rate
        if self._aprs:
            kwargs['aprs'] = self._aprs

        rec = SignalReceiver(self.observation_id, self.frequency, decoding, kwargs)
        rec.run()

        sleep(2)  # sleep for 2 seconds, in order for the external modules to properly initialise
        return True

    def run_tracker(self):
        self.tracker = Worker(
            rotip=self.rot_ip,
            rotport=self.rot_port,
            rigip=self.rig_ip,
            rigport=self.rig_port,
            frequency=self.frequency,
            time_to_stop=self.observation_end)

        self.tracker.trackobject(self.location, self.tle)
        self.tracker.trackstart()
