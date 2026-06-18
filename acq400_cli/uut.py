#!/usr/bin/env python3

"""
Carrier class representation 
"""
import logging
import socket
import time
import threading
import urllib.request
import numpy as np
from acq400_cli.utils import Triplet, background_task, chans_to_bitmask, bitmask_to_chans, FanoutProxy, DotDict, RThread, StopWatch, cached_property
from acq400_cli.constants import *
from acq400_cli.exception import *
from acq400_cli.sample import TransientSample, StreamSample
from acq400_cli.data import UUTData, gen_data_filename
from acq400_cli.site import Site
from acq400_cli.hdmi import CarrierTree
from acq400_cli.clients import StatusMontior


class Carrier:
    """A class representing a single UUT"""

    # Magic methods
    def __init__(self, addr):
        logging.debug(f"Initing UUT {addr}")
        self.addr = addr
        self.lock = threading.Lock()
        self.__build_sites()
        self.hostname = self.s0.HN
        self.status = {}
        self.status_monitor = StatusMontior(self.addr)

    def __getitem__(self, site):
        """Access Site via index notation"""
        return self.site_indexes[site]

    def __getattr__(self, key):
        """Fallback missing attributes to site aliases."""
        if key in self.site_aliases:
            return self.site_aliases[key]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")

    def __str__(self):
        spec = []
        spec.append(f" ----- {self.addr} -----")
        spec.append(f" Capture: {self.capture_state.name}")
        spec.append(f" Sync Role: {self.s0.sync_role}")
        spec.append(f" Sites:")
        for site in self.site_indexes:
            spec.append(f" {site}\t{self.site_indexes[site]}")
        return '\n'.join(spec)
    
    # Internal methods
    def __build_sites(self):
        """build sites"""
        self.site_indexes = {}
        self.site_aliases = {}

        self.site_aliases.setdefault('ai_master', None)
        self.site_aliases.setdefault('ao_master', None)
        self.site_aliases.setdefault('dio_master', None)
        self.site_aliases.setdefault('ai_sites', {})
        self.site_aliases.setdefault('ao_sites', {})
        self.site_aliases.setdefault('dio_sites', {})

        def init_site(site):
            try:
                new_site = Site(self.addr, site.value)

                with self.lock:
                    self.site_indexes[site.value] = new_site
                    self.site_aliases[site.name] = new_site
                    new_site.carrier = self

                    if site.value in self.mgt_sites:
                        self.site_aliases[self.mgt_sites[site.value]] = new_site

                    if site.value in self.wr_site:
                        self.site_aliases[self.wr_site[site.value]] = new_site

                    if site.value in self.hudp_site:
                        self.site_aliases[self.hudp_site[site.value]] = new_site

                    if new_site.is_ai:
                        self.site_aliases['ai_sites'][site.value] = new_site
                        if not self.ai_master and new_site.is_master:
                            self.site_aliases['ai_master'] = new_site
                            logging.debug(f"{self.addr}.{site} is ai master")

                    if new_site.is_ao:
                        self.site_aliases['ao_sites'][site.value] = new_site

                        if not self.ao_master and new_site.is_master:
                            self.site_aliases['ao_master'] = new_site
                            logging.debug(f"{self.addr}.{site} is ao master")
                    
                    if new_site.is_dio:
                        self.site_aliases['dio_sites'][site.value] = new_site

                        if not self.dio_master and new_site.is_master:
                            self.site_aliases['dio_master'] = new_site
                            logging.debug(f"{self.addr}.{site} is dio master")

            except ConnectionRefusedError:
                #logging.debug(f"{self.addr}.{site} Not available")
                pass
            except socket.gaierror:
                logging.error(f"{self.addr} is not reachable")
                raise

        init_site(SITES.s0)

        threads = []
        for site in SITES:
            if site == SITES.s0: continue
            thread = RThread(target=init_site, args=(site,))
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()


    # Attribute methods

    @cached_property
    def sites(self):
        """Return a list of all sites"""
        carrier, sitelist = self.s0.SITELIST.split(',', 1)
        return [int(site.split('=')[0]) for site in sitelist.split(',')]

    @property
    def ssb(self):
        """Return sample size in bytes"""
        return int(self.s0.ssb)

    @property
    def spad_length(self):
        """Return spad length"""
        return (int(self.s0.ssb) - int(self.s0.spadstart)) // 4

    @property
    def stream_sample_format(self):
        """Return Stream sample format"""
        return StreamSample(self)

    @property
    def transient_sample_format(self):
        """Return Transient sample format"""
        return TransientSample(self)

    @property
    def role(self):
        """Return sync role role"""
        return self.s0.sync_role.split(' ')[0].upper()

    @property
    def is_master(self):
        """True if UUT is master else False"""
        return 'MASTER' in self.role

    @property
    def is_demuxed(self):
        """True if data is demuxed else False"""
        return int(self.s0.raw_data_size) == 0

    @property
    def tstate(self):
        """Return current transient state"""
        return CAPTURE_STATE[self.s0.TRANS_ACT__STATE]

    @property
    def cstate(self):
        """Return current continuous state"""
        return CAPTURE_STATE[self.s0.CONTINUOUS__STATE]

    @property
    def capture_state(self):
        """Get the overall capture state"""
        state = self.status_monitor.state
        if state is not None: return CAPTURE_STATE(int(state))
        #Fallback in case of dead monitor
        tstate = self.tstate
        cstate = self.cstate
        if tstate == cstate: return cstate
        if tstate != CAPTURE_STATE['IDLE']: return tstate
        if cstate != CAPTURE_STATE['IDLE']: return cstate

    @property
    def sample_count(self):
        """Return current sample count"""
        return int(self.status_monitor.elapsed) & 0xFFFFFFFF

    @property
    def ioc_ready(self):
        """True if IOC_READY else False"""
        try: return self.s0.get('IOC_READY', '0') == '1'
        except: pass
        return False

    @property
    def es_width(self):
        #TODO: try epics?
        return 1

    @property
    def total_transient_samples(self):
        """Return Transient capture total samples"""
        return int(self.ai_master.ch_data_size) // int(self.ai_master.word_size)

    @property
    def aggregator(self):
        return DotDict(part.split("=", 1) for part in self.s0.aggregator.split())
    
    @property
    def distributor(self):
        return DotDict(part.split("=", 1) for part in self.s0.distributor.split())

    @property
    def agg_sites(self):
        """Return sites in the aggregator"""
        sites = self.aggregator['sites']
        if sites.upper() == 'NONE': return []
        return list(map(int, sites.split(',')))

    @property
    def dist_sites(self):
        """Return sites in the aggregator"""
        sites = self.distributor['sites']
        if sites.upper() == 'NONE': return []
        return list(map(int, sites.split(',')))

    @cached_property
    def wr_site(self):
        """Return White rabbit site"""
        value = self.s0.get('has_wr', 'none')
        if value == 'none': return {}
        return dict(zip(map(int, value.split()), ['wr']))

    @cached_property
    def hudp_site(self):
        """Return HUDP site"""
        value = self.s0.get('has_hudp', 'none')
        if value == 'none': return {}
        return dict(zip(map(int, value.split()), ['hudp']))

    @cached_property
    def mgt_sites(self):
        """Return MGT sites"""
        value = self.s0.get('has_mgt', 'none')
        if value == 'none': return {}
        return dict(zip(map(int, value.split()), ['mgtA', 'mgtB']))

    @property
    def has_ai(self):
        """True if ai site else False"""
        return len(self.agg_sites) > 0

    @property
    def has_ao(self):
        """True if ao site else False"""
        return len(self.dist_sites) > 0

    @cached_property
    def has_gpg(self):
        """True if gpg available else False """
        return self.s0.get("GPG__ENABLE", None) is not None
   
    @property
    def sample_rate(self):
        """sample rate"""
        if self.ai_master.model.upper().startswith('ACQ48'):
            clk = self.ai_master.ACQ480__OSR
        else:
            clk = self.s0.SIG__CLK_S1__FREQ
        return round(float(clk), -3)

    @property
    def vmax(self,):
        """master voltage maximum"""
        return self.ai_master.vmax

    @cached_property
    def calibration(self):
        """get channel calibration"""
        threads = []

        for num, site in sorted(self.ai_sites.items()):
            thread = RThread(target=getattr, args=(site, 'calibration'))
            thread.start()
            threads.append(thread)

        calibration = {}
        chan = 1
        for thread in threads:
            for eslo, eoff in thread.join():
                calibration[chan] = (eslo, eoff)
                chan += 1
        return calibration

    @property
    def rtm_translen(self):
        """rtm_translen"""
        RTM_TRANSLEN = int(self.ai_master.RTM_TRANSLEN)
        rtm_translen = int(self.ai_master.rtm_translen)
        if rtm_translen == 16777216: return 0
        return RTM_TRANSLEN

    @property
    def data_rate(self):
        """Return the data rate sans mask"""
        return (int(self.s0.ssb) * self.sample_rate) / 1_000_000

    @property
    def data_rate_masked(self):
        """Return the data rate with mask"""
        sample_format = StreamSample(self)
        return (sample_format.bytes * self.sample_rate) / 1_000_000
    
    @property
    def stream_enabled(self):
        if not self.s0.knob_exists('stream_subset'): return True
        invalid = ['--fill-scale', '--null-copy']
        options = self.s0.stream_subset.split('\n')[-1].strip()
        return not any(arg in options for arg in invalid)
    
    @property
    def rgm_enabled(self):
        return Triplet(self.s1.rgm).enabled == 1

    @property
    def trigger_line(self):
        """Return trigger line int"""
        return int(self.ai_master.TRG__DX.removeprefix('d'))

    @cached_property
    def fpga(self):
        """Return fpga and timestamp"""
        return self.s0.fpga_version.upper().split(' ')

    @cached_property
    def fpga_features(self):
        """Return fpga features"""
        features = DotDict({
            'size': 0,
            'decimation': 0,
            'comms': [],
        })
        fpga, timestamp = self.fpga
        features.timestamp = timestamp
        features.wr = ('WR' in fpga) or ('E_W' in fpga) or ('U_W' in fpga) or ('A_W' in fpga)
        features.udp = 'UDP' in fpga
        features.udpx = 'UDPX' in fpga
        features.cntr = 'CNTR' in fpga
        features.pg = 'PG' in fpga
        features.pwm = 'PWM' in fpga
        features.dma = 2 if '2DMA' in fpga else 1
        features.qen = 'QEN' in fpga

        if '32B' in fpga: features.size = 32
        if '64B' in fpga: features.size = 64
        if 'DEC4' in fpga: features.decimation = 4
        if 'DEC10' in fpga: features.decimation = 10

        for comm in ['9080', '9011', '9091', '9511', '9815']:
            if comm in fpga:
                features.comms.append(comm)

        return features

    @property
    def transient_values(self):
        """Return transient values dict"""
        return DotDict(part.split("=", 1) for part in self.s0.transient.split())

    @property
    def auto_soft_enabled(self):
        """True if auto soft trigger enabled else false"""
        return bool(int(self.transient_values.SOFT_TRIGGER))
    
    @cached_property
    def enabled_packages(self):
        """Return enabled packages"""
        url = f"http://{self.hostname}/tmp/esw_status"
        with urllib.request.urlopen(url, timeout=5) as resp:
            text = resp.read().decode()
        packages = []
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith('+') or '/packages/' not in line:
                continue
            packages.append(line.split('/packages/', 1)[1].strip())
        return packages

    @property
    def system_configuration(self):
        """Return system configuration dict"""
        software_version = self.s0.software_version
        fpga_version = self.s0.fpga_version
        config = {
            'uutname'        : self.hostname,
            'fpga'           : fpga_version.split(' ')[0],
            'fpga_timestamp' : fpga_version.split(' ')[-1],
            'version'        : int(software_version.split('-')[1]),
            'firmware'       : software_version,
            'serial'         : self.s0.SERIAL,
            'model'          : self.s0.MODEL,
            'packages'       : self.enabled_packages,
            'modules'        : [],
        }
        for site in self.sites:
            config['modules'].append(
                {
                    'site': site,
                    'model': self[site].MODEL.split(' ')[0],
                    'full_model': self[site].PART_NUM,
                    'serial': self[site].SERIAL,
                    'chans': self[site].nchan,
                    'data_size': self[site].data_size,
                }
            )

        return config

    # Normal methods

    def abort_capture(self):
        if self.capture_state == CAPTURE_STATE['IDLE']: return
        logging.debug(f"Aborting capture {self.hostname}")
        
        self.s0.CONTINUOUS = "0"
        self.s0.set_abort = 1
        self.wait_for_idle(timeout=20)

    def arm_transient(self):
        """Arm transient capture"""
        if self.capture_state == CAPTURE_STATE['ARM']:
            logging.warning("Not Arming - System aleady ARMED")
            return
        logging.debug(f"Arming capture {self.hostname}")
        self.s0.set_arm = 1
        
    def wait_for_idle(self, timeout=None):
        """Blocks until UUT reaches IDLE"""
        self.wait_for_state(CAPTURE_STATE.IDLE, timeout)

    def wait_for_arm(self, timeout=None):
        """Blocks until UUT reaches ARM"""
        t0 = time.time()

        while True:
            if self.capture_state in (CAPTURE_STATE.ARM, CAPTURE_STATE.RUN): break
            if self.status_monitor.is_complete():
                logging.warning(f"{self.addr} Shot finished before ready")
                break
            t1 = time.time() - t0
            if timeout and t1 > timeout: 
                raise TimeoutError(f'{self.addr} failed to reach ARM after {timeout}s stuck in {self.capture_state.name}')
            time.sleep(1)
        logging.debug(f"{self.addr} reached ARM")

    def wait_for_state(self, target_state, timeout=None):
        """Blocks until UUT reaches state"""
        if isinstance(target_state, str): target_state = CAPTURE_STATE[target_state.upper()]
        logging.debug(f"{self.addr} Wait for {target_state.name} timeout={timeout}")
        t0 = time.time()
        while self.capture_state != target_state:
            t1 = time.time() - t0
            if timeout and t1 > timeout: 
                raise TimeoutError(f'{self.addr} failed to reach {target_state.name} after {timeout}s stuck in {self.capture_state.name}')
            time.sleep(1)
        logging.debug(f"{self.addr} reached {target_state.name}")

    def wait_for_nsamples(self, nsamples, timeout=None):
        """Blocks until UUT reaches nsamples"""
        if not self.has_ai: return
        logging.debug(f"{self.addr} Wait for {nsamples} samples timeout={timeout}")
        t0 = time.time()
        while self.sample_count < nsamples:
            t1 = time.time() - t0
            if timeout and t1 > timeout: raise TimeoutError(f'{self.addr} failed to reach {nsamples} samples after {timeout}s')
            time.sleep(1)
        logging.debug(f"{self.addr} reached {nsamples} samples")

    def wait_for_transient_complete(self, timeout=None):
        """Wait until transient post processing is complete"""
        if not self.has_ai: return
        logging.debug(f"{self.addr} Wait for transient complete timeout={timeout}")
        t0 = time.time()
        while self.s0.TRANS_ACT__CH__DATA_VALID != '1':
            t1 = time.time() - t0
            if timeout and t1 > timeout: raise TimeoutError(f'{self.addr} transient failed to complete after {timeout}s')
            time.sleep(1)
        logging.debug(f"{self.addr} transient completed")

    def wait_for_complete(self, timeout=None):
        """Wait until shot is complete"""
        if not self.has_ai: return
        logging.debug(f"{self.addr} Wait for shot complete timeout={timeout}")
        t0 = time.time()
        while self.ai_master.shot != self.ai_master.completed_shot:
            t1 = time.time() - t0
            if timeout and t1 > timeout: raise TimeoutError(f'{self.addr} transient failed to complete after {timeout}s')
            time.sleep(1)
        logging.debug(f"{self.addr} transient completed")

    def read_from_port(self, port, dtype, total_samples):
        """Read data from a port"""
        nbytes = np.dtype(dtype).itemsize * total_samples
        with socket.socket() as sock:
            sock.connect((self.addr, port))
            parts = []
            while True:
                block = sock.recv(262144)
                if not block:
                    break
                parts.append(block)
        buf = b"".join(parts)
        if nbytes > len(buf):
            logging.warning(f"{self.addr}:{port} read {len(buf) / (1024 * 1024) :.2f} MB expected {nbytes / (1024 * 1024) :.2f} MB")
        return np.frombuffer(buf, dtype=dtype, count=total_samples)

    def read_transient_data(self):
        """Read transient data into a structured array"""
        self.wait_for_transient_complete(timeout=30)
        sample_format = TransientSample(self)
        tsamples = self.total_transient_samples
        
        if self.is_demuxed:
            raw = np.empty(tsamples, dtype=sample_format.dtype)
            for chan in sample_format.channels:
                raw[str(chan)] = self.read_from_port(PORTS.DATA0 + chan, sample_format.channels[chan].dtype, tsamples)
            data = UUTData(raw, sample_format)
        else:
            data = UUTData(self.read_from_port(PORTS.DATA0, sample_format.dtype, tsamples), sample_format)

        nsamples = data.nbytes // sample_format.bytes
        logging.info(f"Read {nsamples} samples ({data.nbytes / (1024 * 1024):.2f} MB) from {self.hostname}")
        return data

    def stream_to_host(self, target_bytes, port=PORTS.STREAM, sample_format=None, datafile=None, bufferlen=4*(1024*1014)):
        """Stream data to host"""

        if not self.stream_enabled: 
            logging.warning(f"{self.hostname} Streaming not enabled")
        
        if not self.rgm_enabled and self.data_rate_masked > MAX_ETH_RATE: 
            logging.warning(f"{self.hostname} Stream datarate above {MAX_ETH_RATE} MB/s")

        if not sample_format:
            sample_format = self.stream_sample_format

        if isinstance(datafile, str): datafile = open(datafile, 'wb')
        savepath = getattr(datafile, 'name', None)
        logging.debug(f"Streaming to host {target_bytes} Bytes")


        target_bytes = int((target_bytes // sample_format.bytes) * sample_format.bytes)
        nsamples = int(bufferlen // sample_format.bytes)
        bufferlen = int(nsamples * sample_format.bytes)

        buffer = bytearray(bufferlen)
        view = memoryview(buffer).cast('B')
        array = np.ndarray((nsamples,), dtype=sample_format.dtype, buffer=view)

        spads = sample_format.types.get('SPD', [])
        spad0_chan = spads[0] if spads else None

        self.status = DotDict({
            'state': 'streaming',
            'total_bytes': 0,
            'time_start': 0,
            'missed': 0,
            'spad0_chan': spad0_chan,
            'savepath': savepath,
            'target_bytes': target_bytes,
            'stop_flag': False,
            'ssb': sample_format.bytes,
        })

        logging.info(f"{self.hostname} Init stream {target_bytes >> 20} MiB ({self.data_rate_masked}MB/s)")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, max(bufferlen, 8 * 1024 * 1024))
            sock.connect((self.addr, port))

            cursor = 0
            spad0_last = np._NoValue

            try:
                while True:
                    nbytes = sock.recv_into(view[cursor:])
                    if nbytes == 0: break

                    cursor += nbytes
                    self.status.total_bytes += nbytes

                    if self.status.time_start == 0: 
                        sock.settimeout(30)
                        self.status.time_start = time.time()

                    if cursor >= bufferlen:

                        if datafile: 
                            trim = max(0, self.status.total_bytes - target_bytes)
                            datafile.write(buffer[:cursor - trim])

                        if spad0_chan != None:
                            spad0_data = array[str(spad0_chan)]
                            self.status.missed += np.sum(np.diff(spad0_data, prepend=spad0_last) - 1)
                            spad0_last = spad0_data[-1]
                        
                        cursor = 0

                        if self.status.stop_flag: break
                        if self.status.total_bytes >= target_bytes: break

            except KeyboardInterrupt: pass

        if datafile: datafile.close()
        
        logging.info(f"{self.hostname} Finshed {self.status.total_bytes >> 20}MB ({self.status.total_bytes // sample_format.bytes} Samples) streamed to {savepath}")
        if self.status.missed > 0: logging.warning(f"{self.hostname} Stream {self.status.missed} missing samples")
        return savepath

    def read_stream_sample(self, nsamples=1):
        """Read samples from running stream"""
        sample_format = self.stream_sample_format
        nbytes = nsamples * sample_format.bytes
        buffer = bytearray(nbytes)
        view = memoryview(buffer).cast('B')
        cursor = 0
        with socket.socket() as sock:
            sock.connect((self.addr, PORTS.DATA_SPY))
            while True:
                n = sock.recv_into(view[cursor:], nbytes - cursor)
                if n == 0: break
                if cursor >= nbytes: break
                cursor += n
        raw = np.frombuffer(buffer, dtype=sample_format.dtype, count=nsamples)
        return UUTData(raw, sample_format)

    def run0(self, sites=None, spad=None):
        """Run run0"""

        if isinstance(sites, str) and sites.upper() == 'ALL': sites = self.sites
        if isinstance(sites, list): sites = ','.join(map(str, sites))
        if isinstance(spad, list): spad = ','.join(map(str, spad))

        sites = sites if sites else self.s0.sites
        spad = spad if spad else self.s0.spad

        self.s0.run0 = f"{sites} {spad}"

    def set_spad1_count(self, enabled=True, site=None, sense=1):
        """enable or disable spad1 microsecond count"""
        enabled = 1 if enabled else 0
        line = site if site else self.ai_master.site
        self.s0.spad1_us = f"{enabled},{line},{sense}"

    def get_counter_freq(self, signal="TRG", line=-1):
        """Get counter frequency"""
        counter = COUNTERS(line).name
        return float(getattr(self.s0, f"SIG__{signal}_{counter}__FREQ"))

    def get_counter_count(self, signal="TRG", line=-1):
        """Get counter count"""
        counter = COUNTERS(line).name
        return int(getattr(self.s0, f"SIG__{signal}_{counter}__COUNT"))

    def set_trigger_source(self, source):
        """Config sync trigger source in for master UUT"""
        
        if not self.is_master: return

        line = SIG_LINE.__members__.get(source, None)

        if line is None: raise ValueError(f"Invalid trigger source {source!r} ({SIG_LINE.names()})")

        logging.debug(f"Trigger d{line} source is {source}")

        # d0
        if source == 'EXT': self.s0.SIG__SRC__TRG__0 = "EXT"
        if source == 'HDMI': self.s0.SIG__SRC__TRG__0 = "HDMI"
        if source == 'WRTT0': self.s0.SIG__SRC__TRG__0 = "WRTT0"
        if source == 'FREE': self.s0.SIG__SRC__TRG__0 = "NONE"

        # d1
        if source == 'INT': self.s0.SIG__SRC__TRG__1 = "STRIG"
        if source == 'SOFT': self.s0.SIG__SRC__TRG__1 = "STRIG"
        if source == 'WRTT1': self.s0.SIG__SRC__TRG__1 = "WRTT1"
        if source == 'AUTO': self.s0.SIG__SRC__TRG__1 = "NONE"

        # Free running triggers need to be until UUT is armed
        if source == 'EXT' and self.get_counter_freq() > 0:
            logging.warning(f"Free Running Trigger Detected - Changing to FREE")
            self.s0.SIG__SRC__TRG__0 = "NONE" # NONE is a placeholder for EXT

        if source == 'HDMI' and self.get_counter_freq() > 0:
            logging.warning(f"Free Running Trigger Detected - Changing to FREE")
            self.s0.SIG__SRC__TRG__0 = "nc" # nc is a placeholder for HDMI

        # Auto soft triggers need to be set to NONE until UUT is armed
        if source in ('SOFT', 'INT') and self.auto_soft_enabled:
            logging.warning(f"Auto Soft Trigger - Changing to AUTO")
            self.s0.SIG__SRC__TRG__1 = "NONE"

    def trigger_capture(self, siggen=None):
        """Trigger capture based on UUT signal config"""

        if not self.is_master: return

        trigger_line = self.trigger_line

        # d0 Trigger
        if trigger_line == 0:
            trigger_source = self.s0.SIG__SRC__TRG__0

            if trigger_source in ('NONE', 'nc'): # Handle source placeholders
                trigger_source = 'EXT' if trigger_source == 'NONE' else 'HDMI'
                logging.info(f"Enabling external trigger ({trigger_source})")
                self.s0.SIG__SRC__TRG__0 = trigger_source

            if trigger_source == 'EXT' and siggen:
                logging.info(f'Triggering {siggen}')
                siggen.trigger()

            if trigger_source == 'HDMI' and siggen:
                logging.info(f'Triggering {siggen}')
                siggen.trigger()

            if trigger_source == 'WRTT0':
                logging.info("Triggering WRTT0")
                #TODO: how to trigger WR?

        # d1 trigger
        if trigger_line == 1:
            trigger_source = self.s0.SIG__SRC__TRG__1
            
            if trigger_source == 'NONE':
                logging.info("Enabling Soft trigger")
                self.s0.SIG__SRC__TRG__1 = 'STRID'
                logging.info(f'Soft triggering')
                self.trigger_soft_trigger()
            
            if trigger_source == 'STRID':
                logging.info(f'Soft triggering')
                self.trigger_soft_trigger()

            if trigger_source == 'WRTT1': 
                logging.info("Triggering WRTT1")
                #TODO: how to trigger WR?












    def configure_capture(
        self,
        pre=0,
        post=0,
        trigger='0,0,0',
        event0='0,0,0',
        event1='0,0,0',
        rgm='0,0,0',
        translen=0,
        demux=0,
        stream_mask=None,
        sites=None,
        spad=None,
        ):
        """Configures uut for capture"""
        if not self.ai_master: return
        logging.debug(f"{self.hostname} Configuring capture")

        auto_soft_trigger = 1 if getattr(trigger, 'source', None) == 'AUTO' else 0

        self.s0.TRANSIENT__PRE = pre
        self.s0.TRANSIENT__POST = post
        self.s0.TRANSIENT__SOFT_TRIGGER = auto_soft_trigger

        self.s0.transient = f"PRE={int(pre)} POST={int(post)} SOFT_TRIGGER={auto_soft_trigger} DEMUX={demux}"
        self.ai_master.trg = trigger
        if hasattr(trigger, 'source') and trigger.source: self.set_trigger_source(trigger.source)
        self.ai_master.event0 = event0
        self.ai_master.event1 = event1
        self.ai_master.rgm = rgm
        self.ai_master.RTM_TRANSLEN = translen
        self.set_stream_mask(stream_mask)
        
        # Slave UUTs cannot soft trigger
        if not self.is_master and trigger != '0,0,0':
            if not isinstance(trigger, Triplet): trigger = Triplet(trigger)
            self.ai_master.trg = trigger.override('line', 0)

        if sites or spad: self.run0(sites, spad)

    def ident_spad(self, enable=True):
        for id in ['1', '2', '3', '4' , '5', '6', '7']:
            if not enable: id = '0'
            self.s0.set(f"spad{id}", id * 8)

    def get_stream_mask_raw(self):
        """Returns raw stream mask channels"""
        if not self.s0.knob_exists('stream_subset_mask'): return None
        mask = self.s0.stream_subset_mask
        if mask.lower() == 'none': return None
        return bitmask_to_chans(mask)

    def get_stream_mask(self):
        """Get the stream mask channels"""
        if not self.s0.knob_exists('stream_subset_mask'): return None
        sample = StreamSample(self, None)
        mask = self.get_stream_mask_raw()
        if not mask: return None
        return sorted(list({sample.physical[chan] for chan in mask}))

    def set_stream_mask(self, mask):
        """Set the stream mask chanmels"""
        if not self.s0.knob_exists('stream_subset_mask'): return
        if not mask: 
            self.s0.stream_subset_mask = 'none'
            return
        sample = StreamSample(self, None)
        self.s0.stream_subset_mask = chans_to_bitmask([item for chan in mask for item in sample.channels[chan].physical])

    def has_hdmi_output(self):
        """Returns True if HDMI out connected else False"""
        return self.s0.SIG__SYNC_BUS__OUT__CABLE_DET == 'CONNECTED'

    def trigger_soft_trigger(self):
        """Trigger soft trigger"""
        self.s0.soft_trigger = 1

    def auto_stream_mask(self, max_rate=30):
        """
        ajust the datarate using the stream mask
        """

    def seconds_to_bytes(self, seconds, sample_format):
        """Return total bytes for capture runtime"""
        return int(seconds * sample_format.bytes * self.sample_rate)

    def data_filename(self, sample_format, timestamp=None, seq=None):
        """Generate data filename"""
        return gen_data_filename(self.hostname, sample_format, timestamp, seq)

    def get_stream_status(self):
        """return the stream status string"""
        if not self.status: return None
        current = self.status.total_bytes // self.status.ssb
        target = self.status.target_bytes // self.status.ssb
        runtime = int(time.time() - self.status.time_start) if self.status.time_start > 0 else 0
        missed = '' if self.status.spad0_chan is None else f"({self.status.missed:,})"
        return f"{self.hostname} [{self.cstate.name}] {runtime}s {current:,} / {target:,} {missed}"

    def set_mgt_agg(self, enable=True, decimate=None):
        """Set MGT aggregator"""
        mode = 'on' if enable else 'off'
        spad_en = int(self.spad_length > 0)
        for idx, name in self.mgt_sites.items():
            logging.debug(f"Comm site {name} {mode}")
            self[idx].aggregator = f"sites={self.aggregator.sites} spad={spad_en} {mode}"
            if decimate: self[idx].decimate = decimate

    def get_translen_period(self, ajust=1):
        """return ideal translen period in seconds"""
        return self.rtm_translen * ajust / self.sample_rate

    def read_stl(self):
        """Read STL from UUT"""
        with socket.socket() as sock:
            sock.connect((self.addr, PORTS.GPGDUMP))
            parts = []
            while True:
                block = sock.recv(4096)
                if not block:
                    break
                parts.append(block)
        return b"".join(parts).decode()

    def configure_gpg(self, stl, mode, timescaler=1, trigger=None, clock=None, repeat=0):
        """Configure GPG for output"""
        if not self.has_gpg: raise GPGNotAvailableError(f"{self.addr} GPG not available (enable package)")

        self.s0.GPG__ENABLE = 0

        self.s0.GPG__MODE = GPG_MODE(mode).value
        self.s0.gpg_timescaler = timescaler

        if trigger:
            logging.debug(f"{self.addr} GPG Trigger = {trigger}")
            self.s0.GPG_TRG = trigger.enabled
            self.s0.GPG_TRG__DX = trigger.line
            self.s0.GPG_TRG__SENSE = trigger.sense

        if clock:
            logging.debug(f"{self.addr} GPG Clock = {clock}")
            self.s0.GPG_CLK = clock.enabled
            self.s0.GPG_CLK__DX = clock.line
            self.s0.GPG_CLK__SENSE = clock.sense

        self.s0.SIG_EVENT_SRC_0 = 'GPG'
        self.s0.SIG_FP_GPIO = 'EVT0'

        if isinstance(stl, str):
            logging.debug(f"{self.addr} reading file {stl}")
            with open(stl, 'r') as fp:
                stl = []
                for line in fp.readlines():
                    line = line.strip()
                    if not line or line.startswith('#'): continue
                    stl.append(line)

        tail = stl[1:]
        for _ in range(repeat):
            stl.extend(tail)
        stl.append("EOF")

        with socket.socket() as sock:
            with socket.socket() as sock:
                sock.connect((self.addr, PORTS.GPGSTL))
                for line in stl:
                    sock.send(f"{line}\n".encode())
                    rx = sock.recv(4096).decode().strip()
                    logging.trace(f"{self.addr} {line} {rx}")

        self.s0.GPG__ENABLE = 1




class Collection(list):
    """A class representing multiple UUTs"""

    def __init__(self, uutnames):
        self.uuts = {uutname: Carrier(uutname) for uutname in uutnames}
        self.extend(sorted(self.uuts.values()))
        self._proxy = FanoutProxy(self.uuts)
        self.names = ' '.join(sorted(self.uuts.keys()))

    def __getitem__(self, key):
        if isinstance(key, (int, slice)):
            return super().__getitem__(key)
        return self.uuts[key]

    def __contains__(self, uutname):
        return uutname in self.uuts

    def __getattr__(self, key):
        return getattr(self._proxy, key)

    def __str__(self):
        lines = ['Collection:']
        for uutname in self.uuts:
            lines.append(f"- {uutname}")
        return '\n'.join(lines)

    #Normal methods

    def set_sync_role(self, clk, master_role='master', slave_role="slave"):
        """set sync role"""
        #TODO: handle TRG:DX and TRG:SENSE
        #TODO: handle CLK:DX and CLK:SENSE
        #TODO: handle CLKDIV

        master_params = f"{master_role} {clk}"
        slave_params = f"{slave_role} {clk}"
        logging.debug(f"Master sync role {master_params}")
        logging.debug(f"Slave sync role {slave_params}")

        self.masters.disable_blocking()
        self.masters.s0.sync_role = master_params

        self.slaves.disable_blocking()
        self.slaves.s0.sync_role = slave_params

        self.masters.wait_for_complete()
        self.slaves.wait_for_complete()

    @background_task
    def trigger_when_armed(self, siggen=None, timeout=30):
        """Trigger capture when all UUTs are ARMED"""
        print("Waiting for ARM")
        self._proxy.wait_for_arm(timeout)
        print("Armed")
        self._proxy.trigger_capture(siggen)

    def print_status_until_idle(self,):
        """Print UUTs status untill all IDLE"""
        LINE_UP = '\033[1A'
        ERASE_LINE = '\033[2K'

        while True:
            all_idle = True
            for uutname, uut in sorted(self.uuts.items()):
                state = uut.capture_state.name
                sample_count = uut.sample_count
                if state != 'IDLE': all_idle = False
                print(f"{uutname} {COLORS.format(COLORS.get(state), state)} {sample_count}")
            if all_idle: return
            time.sleep(0.5)
            print(''.join(LINE_UP + ERASE_LINE for _ in range(len(self.uuts))), end='')

    # Attribute methods

    @property
    def tree(self):
        """Calculate the collection Tree"""
        if hasattr(self, '_tree'): return self._tree
        self._tree = CarrierTree(list(self))
        return self._tree

    @property
    def masters(self):
        """Proxy for master uuts"""
        if hasattr(self, '_masters'): return self._masters
        masters, slaves = self.tree.partition(depth=0)
        self._masters = FanoutProxy({uutname: self[uutname] for uutname in masters})
        self._slaves = FanoutProxy({uutname: self[uutname] for uutname in slaves})
        return self._masters

    @property
    def slaves(self):
        """Proxy for slave uuts"""
        if hasattr(self, '_slaves'): return self._slaves
        masters, slaves = self.tree.partition(depth=0)
        self._masters = FanoutProxy({uutname: self[uutname] for uutname in masters})
        self._slaves = FanoutProxy({uutname: self[uutname] for uutname in slaves})
        return self._slaves
    


def factory(*uutnames):
    """Init UUTs"""
    return Collection(uutnames)

if __name__ == '__main__':

    uutnames = ['acq2106_130', 'acq2106_054']
    uuts = Collection(uutnames)
    print(uuts)
    uuts.set_sync_role(1000000)