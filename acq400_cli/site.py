
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
import time

from acq400_cli.constants import PORTS
from acq400_cli.exception import KnobNotFoundError
from acq400_cli.utils import cached_property, Triplet, convert_to_broadcast


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
            if value:
                logging.trace(f"{self.addr}:{self.port} < {knob} < {value}")
            else:
                logging.trace(f"{self.addr}:{self.port} > {message} > {repr(rc[:100])}")
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

    def get_gain(self, chan):
        """Get gain for channel"""
        if not self.is_ai: return None
        gain = self.get(f"GAIN__{chan:02d}", None)
        if not gain: return None
        gain = gain.removeprefix('+/-').removesuffix('V')
        lower = upper = gain
        if '-' in gain: lower, upper = gain.split('-')
        return (-abs(float(lower)), float(upper))

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
        if self.knob_exists('DO32'): return True
        return self.get('module_name', None) == 'timbus'

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
        elif PART_NUM.find('2V5') >= 0: input_range = 2.5
        elif PART_NUM.startswith('ACQ48'): input_range = 2.5
        
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
        """return array of channel gains"""
        # GAINS knob is slow so use lookup table
        try:
            enums = self.get("gains").strip()
            lookup = {}
            gains = []
            for chan, enum_id in enumerate(enums[:self.nchan], 1):
                if enum_id not in lookup:
                    lookup[enum_id] = self.get_gain(chan)
                gains.append(lookup[enum_id])
            return gains
        except:
            return None


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
    def live_clock(self):
        """return the module live clock value"""
        return float(self.carrier.s0.get(f"SIG__CLK_S{self.site}__FREQ"))

    @property
    def trg(self):
        """Return trigger triplet"""
        return Triplet(self.get('trg').removeprefix('=').split(' ')[0])

    @property
    def event0(self):
        """Return event0 triplet"""
        return Triplet(self.get('event0').removeprefix('=').split(' ')[0])

    @property
    def rgm(self):
        """Return rgm triplet"""
        return Triplet(self.get('rgm').removeprefix('=').split(' ')[0])

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

class Bolo8:
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


class MGT:
    """MGT overlay"""

    @property
    def role(self):
        """return site role"""
        return self.get('module_role', 'COMMS').upper()


class HUDP:
    """HUDP overlay"""

    def disable(self):
        self.tx_reset = 1
        self.hudp_gt_reset = 1

    def enable(self):
        self.hudp_gt_reset = 0
        self.tx_reset = 0

    def set_disco(self, disco=None):
        if disco is None:
            self.disco_en = 0
        else:
            print(f"{self.carrier.hostname}: enable disco at {disco}")
            self.disco_idx = disco
            self.disco_en = 1

    def init(self, ip, gw, netmask):
        self.disable()
        self.ip = ip
        self.gw = gw
        self.netmask = netmask

    def init_arp_req(self, timeout=15):
        self.arp_request = 1
        self.arp_request = 0
        t0 = time.time()
        while True:
            if self.arp_mac_resp != '00:00:00:00:00:00:00': break
            if time.time() - t0 > timeout:
                raise TimeoutError(f'{self.carrier.hostname} failed get arp mac after {timeout}s')
            time.sleep(0.5)
            print(f"{self.carrier.hostname} waiting for arp")
        logging.info(f"arp_mac_resp: {self.arp_mac_resp}")

    def config_tx(self, dst_ip, src_port, dst_port, decim, broadcast=False, netmask='255.255.255.0'):
        self.hudp_decim = decim
        self.src_port = src_port
        self.dst_port = dst_port
        self.dst_ip = convert_to_broadcast(dst_ip, netmask) if broadcast else dst_ip

    def config_rx(self, src_ip, src_port):
        self.rx_src_ip = src_ip
        self.rx_port = src_port

    def config_relay(self, offset):
        self.udp_data_src = 1
        if offset > 0:
            tx_ssb = int(self.carrier.s0.dssb) - offset
            self.slice_len = tx_ssb // 4
            self.slice_off = offset // 4
        else:
            tx_ssb = int(self.slice_len) * 4
        return tx_ssb


class Mgt508:
    """MGT 508 overlay"""
    pass


OVERLAYS = {
    "BOLO8BLF": Bolo8,
    "MGT": MGT,
    "HUDP": HUDP,
}
def load_overlay(site, name):
    """Add an overlay to a site"""
    overlay = OVERLAYS.get(name)
    if not overlay: return
    if overlay in site.__class__.__mro__: return
    cls = type(f"{overlay.__name__}_{site.__class__.__name__}", (overlay, site.__class__), {})
    object.__setattr__(site, '__class__', cls)
    logging.debug(f"{name} overlay applied to site {site.site}")
