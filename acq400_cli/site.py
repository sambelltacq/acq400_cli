
""" 
Needed sites

Make site more generic 

then have a

 DIO site?
 ACQ site
 AO site
 BOLO SITE
 COMMANS site 
 MGT site?


"""
import logging
import re
import threading
import socket
import atexit
import logging

from acq400_cli.constants import PORTS
from acq400_cli.exception import KnobNotFoundError
from acq400_cli.utils import cached_property


class CommandSocket:
    """handles knob commands to a socket"""
    def __init__(self, addr, port):
        self.addr = addr
        self.port = port
        self.buffer = ''
        self.sock = None
        self.lock = threading.Lock()
        self.termex = re.compile(r"\n(acq400.[0-9]+ ([0-9]+) >)")
        self.connect()
        self.send_message("prompt on")
        atexit.register(self.close)

    def connect(self):
        """Connect socket to port"""
        self.close()
        try:
            #logging.debug(f"{self.addr}:{self.port} Initing Socket")
            self.sock = socket.socket()
            self.sock.connect((self.addr, self.port))
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except ConnectionRefusedError:
            self.close()
            raise

    def send_message(self, knob, value=None, maxlen=4096):
        """Send a message and receive a reply"""
        with self.lock:
            message = f"{knob}={value}" if value is not None else knob
            logging.trace(f"{self.addr}:{self.port} < {message}")
            self.sock.send(f"{message}\n".encode())
            while True:
                self.buffer += self.sock.recv(maxlen).decode("latin-1")
                match = self.termex.search(self.buffer)
                if match: break
            rc = self.buffer[:match.start(1)].rstrip()
            self.buffer = self.buffer[match.end(1):]
            if rc.startswith(f"ERROR:{knob}"):
                logging.trace(f"{self.addr}:{self.port} > Error: '{knob}' not found")
                raise KnobNotFoundError(f"{self.addr}:{self.port} '{knob}' not found")
            rc = rc.removeprefix(knob).lstrip()
            logging.trace(f"{self.addr}:{self.port} > {repr(rc[:100])}")
            return rc

    def get(self, knob): 
        """Get a knob"""
        return self.send_message(knob)

    def set(self, knob, value): 
        """Set a knob"""
        return self.send_message(knob, value)

    def close(self):
        """Close socket"""
        if self.sock:
            #logging.debug(f"{self.addr}:{self.port} Closing Socket")
            self.sock.close()

class Site:
    """A class representing a single site"""

    # Magic methods
    def __init__(self, addr, site):
        self._disable_socket()
        self.site = site
        self.addr = addr
        self.port = site + PORTS.SITE0
        self.carrier = None
        self.socket = CommandSocket(self.addr, self.port)
        logging.debug(f"Initing Site {self.site} ({self.addr}:{self.port})")
        self.model = self.get_model()
        load_overlay(self, self.model)
        self._enable_socket()

    def __setattr__(self, key, value):
        """Send set to socket"""
        if self.socket_disabled or key in self.__dict__: 
            return object.__setattr__(self, key, value)
        return self.set(key, value)

    def __getattr__(self, key):
        """Send unknown gets to socket"""
        return self.get(key)

    def __str__(self):
        return f"< {self.model} Site: {self.site} Port: {self.port} Role: {self.role} >"

    # Internal methods
    def _disable_socket(self):
        """Enable sending to remote socket"""
        object.__setattr__(self, 'socket_disabled', True)
    
    def _enable_socket(self):
        """Enable sending to remote socket"""
        object.__setattr__(self, 'socket_disabled', False)

    # Normal methods
    def knob_exists(self, knob):
        """Check knob existence return bool"""
        return self.escape_knob(knob) in self.knobs

    def get(self, knob, default=False):
        """Get knob value with optional default"""
        try:
            return self.socket.get(self.escape_knob(knob))
        except:
            if default is False: raise
            return default

    def set(self, knob, value):
        """Set knob value"""
        return self.socket.set(self.escape_knob(knob), value)

    def escape_knob(self, knob):
        """Replace '__' with ':'"""
        return knob.replace('__', ':')

    def get_model(self):
        """return site model"""
        return self.get('MODEL', self.get('module_name', 'UNKNOWN')).upper().split(' ')[0]

    def help(self):
        return self.knobs

    # Attribute methods
    @cached_property
    def knobs(self):
        """Get list of avaliable knobs"""
        return [self.escape_knob(knob) for knob in self.get("help").strip().split('\n')]

    @cached_property
    def is_ai(self):
        """True if site is ai else False"""
        return self.get('is_adc', '').startswith('1')

    @cached_property
    def is_ao(self):
        """True if site is ao else False"""
        return self.knob_exists('dac_dec')

    @cached_property
    def is_dio(self):
        """True if site is dio else False"""
        return self.knob_exists('DO32')

    @cached_property
    def features(self):
        "return a list of features"
        features = []
        if self.get('is_adc', '').startswith('1'):
            features.append('ai')
        if self.knob_exists('dac_dec'):
            features.append('ao')
        if self.knob_exists('DO32'):
            features.append('dio')
        return features

    @property
    def input_range(self):
        """return max scale channel array"""
        input_range = self.gains
        if input_range: return input_range

        input_range = 10
        PART_NUM = self.PART_NUM
        match = re.search(r'([.\d]+)V', PART_NUM)

        if match: input_range = int((match.group(1)))
        if PART_NUM.find('2V5') >= 0: input_range = 2.5
        if PART_NUM.startswith('ACQ480'): input_range = 2.5
        
        return [(-abs(input_range), input_range)] * self.nchan

    @property
    def eslo(self):
        """return eslo array"""
        return list(map(float, self.AI__CAL__ESLO.split(" ")[2:]))

    @property
    def eoff(self):
        """return eoff array"""
        return list(map(float, self.AI__CAL__EOFF.split(" ")[2:]))

    @property
    def gains(self):
        """return channel gains array"""
        gains = []
        try:
            for chan in range(1, self.nchan + 1):
                gain = self.get(f"gain{chan}")

                if gain.startswith('M'):
                    gain = gain.removeprefix('M')
                lower, upper = gain.split('-')
                gains.append((-abs(float(lower)), float(upper)))
            return gains
        except: return None

    @property
    def calibration(self):
        """Return channel calibration"""
        return list(zip(self.eslo, self.eoff, self.input_range))

    @property
    def role(self):
        """return site role"""
        return self.get('module_role', 'UNKNOWN').upper()

    @property
    def is_master(self):
        """True if module role is master else False"""
        return self.role == 'MASTER'

    @cached_property
    def data_size(self):
        """Return data size in bytes"""
        return 4 if int(self.data32) else 2

    @cached_property
    def nchan(self):
        """Return number of channels"""
        return int(self.active_chan)

    @property
    def spec(self):

        if self.is_ai:
            fmt ='{nchan}CH_{data_size}B'
        elif self.is_dio:
            fmt ='{nchan}DIO'
        else: return None

        spec = {
            'nchan': self.nchan,
            'data_size': self.data_size,
            'fmt': fmt,
        }

        return spec

class Bolo8(Site):
    """BOLO8 overlay"""
    @property
    def data_size(self):
        """Return data size in bytes"""
        bypass_enabled = int(self.carrier.dsp.DSP_BYPASS) == 1
        if bypass_enabled: return 2
        return 4 if int(self.data32) else 2
        
    @property
    def nchan(self):
        """Return number of channels"""
        bypass_enabled = int(self.carrier.dsp.DSP_BYPASS) == 1
        if bypass_enabled: return 16
        return int(self.active_chan)

class Mgt(Site):
    """Mgt overlay"""
    @property
    def role(self):
        """return site role"""
        #TODO handle MGTA or B or HUDP or ETH or WR here
        #perhaps a commns site 
        #sites > 9 are comms site
        #sites == 14 are dsp sites
        return self.get('module_role', 'COMMS').upper()


OVERLAYS = {
    "BOLO8BLF": Bolo8,
    "MGT482": Mgt,
}

def load_overlay(site, model):
    """Load site overlay if present"""
    overlay = OVERLAYS.get(model)
    if not overlay: return
    logging.debug(f"{model} overlay applied to site {site.site}")
    site.__class__ = overlay

