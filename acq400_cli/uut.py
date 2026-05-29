#!/usr/bin/env python3

"""
Carrier class representation 
"""
import logging
import socket
import time
import os
import numpy as np

from acq400_cli.utils import Triplet, chans_to_bitmask, bitmask_to_chans, FanoutProxy, DotDict
from acq400_cli.constants import PORTS, SITES, CAPTURE_STATE, TRG_LINE, MAX_ETH_RATE
from acq400_cli.exception import IOCNotReadyError
from acq400_cli.sample import TransientSample, StreamSample
from acq400_cli.data import UUTData, gen_data_filename
from acq400_cli.site import Site
from acq400_cli.hdmi import CarrierTree


class Carrier:
    """A class representing a single UUT"""

    # Magic methods
    def __init__(self, addr):
        logging.debug(f"Initing UUT {addr}")
        self.addr = addr
        self.__build_sites()
        self.hostname = self.s0.HN

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

        for site in SITES:
            try:

                new_site = Site(self.addr, site.value)

                self.site_indexes[site.value] = new_site
                self.site_aliases[site.name] = new_site

                if site.value == 0:
                    if not self.ioc_ready: raise IOCNotReadyError(f"{self.addr} IOC not Ready")
                    self.site_aliases['carrier'] = new_site
                    mgt_sites = dict(zip(self.mgt_sites, ['mgtA', 'mgtB']))
                    wr_site = dict(zip(self.wr_site, ['wr']))
                    hudp_site = dict(zip(self.hudp_site, ['hudp']))

                if site.value in mgt_sites:
                    self.site_aliases[mgt_sites[site.value]] = new_site

                if site.value in wr_site:
                    self.site_aliases[wr_site[site.value]] = new_site

                if site.value in hudp_site:
                    self.site_aliases[hudp_site[site.value]] = new_site

                if new_site.is_ai:
                    self.site_aliases.setdefault('ai_sites', [])
                    self.site_aliases['ai_sites'].append(new_site)

                    if not self.ai_master and new_site.is_master:
                        self.site_aliases['ai_master'] = new_site
                        logging.debug(f"{self.addr}.{site} is ai master")

                if new_site.is_ao:
                    self.site_aliases.setdefault('ao_sites', [])
                    self.site_aliases['ao_sites'].append(new_site)

                    if not self.ao_master and new_site.is_master:
                        self.site_aliases['ao_master'] = new_site
                        logging.debug(f"{self.addr}.{site} is ao master")
                
                if new_site.is_dio:
                    self.site_aliases.setdefault('dio_sites', [])
                    self.site_aliases['dio_sites'].append(new_site)

                    if not self.dio_master and new_site.is_master:
                        self.site_aliases['dio_master'] = new_site
                        logging.debug(f"{self.addr}.{site} is dio master")

                new_site.carrier = self

            except ConnectionRefusedError:
                logging.debug(f"{self.addr}.{site} Not available")
            except socket.gaierror:
                logging.error(f"{self.addr} is not reachable")
                raise

    # Attribute methods

    @property
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
        tstate = self.tstate
        cstate = self.cstate
        if tstate == cstate: return cstate
        if tstate != CAPTURE_STATE['IDLE']: return tstate
        if cstate != CAPTURE_STATE['IDLE']: return cstate

    @property
    def sample_count(self):
        """Return current sample count"""
        return int(self.s0.CONTINUOUS__SC)

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
        return dict(part.split("=", 1) for part in self.s0.aggregator.split())
    
    @property
    def distributor(self):
        return dict(part.split("=", 1) for part in self.s0.distributor.split())

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

    @property
    def wr_site(self):
        """Return White rabbit sites"""
        sites = self.s0.get('has_wr', 'NONE').upper()
        if sites == 'NONE': return []
        return list(map(int, sites.split(' ')))
    
    @property
    def hudp_site(self):
        sites = self.s0.get('has_hudp', 'NONE').upper()
        if sites == 'NONE': return []
        return list(map(int, sites.split(' ')))

    @property
    def mgt_sites(self):
        sites = self.s0.get('has_mgt', 'NONE').upper()
        if sites == 'NONE': return []
        return list(map(int, sites.split(' ')))

    @property
    def has_ai(self):
        """True if ai site else False"""
        return len(self.agg_sites) > 0

    @property
    def has_ao(self):
        """True if ao site else False"""
        return len(self.dist_sites) > 0
    
    @property
    def sample_rate(self):
        """sample rate"""
        # ACQ43X_SAMPLE_RATE
        return round(float(self.s0.SIG__CLK_S1__FREQ), -3)

    @property
    def transient_format(self):
        """Return the current transient sample format"""
        return TransientSample(self)

    @property
    def stream_format(self):
        """Return the current stream sample format"""
        return StreamSample(self)

    @property
    def data_rate_raw(self):
        """Return the data rate sans mask"""
        sample_format = StreamSample(self, None)
        return (sample_format.bytes * self.sample_rate) / 1_000_000

    @property
    def data_rate_masked(self):
        """Return the data rate with mask"""
        sample_format = StreamSample(self)
        return (sample_format.bytes * self.sample_rate) / 1_000_000
    
    @property
    def stream_enabled(self):
        invalid = ['--fill-scale', '--null-copy']
        options = self.s0.stream_subset.split('\n')[-1].strip()
        return not any(arg in options for arg in invalid)
    
    @property
    def rgm_enabled(self):
        return Triplet(self.s1.rgm).enabled == 1


    # Normal methods

    def abort_capture(self):
        if self.capture_state == CAPTURE_STATE['IDLE']: return
        logging.debug(f"Aborting capture {self.hostname}")
        self.s0.set_abort = 1
        self.s0.CONTINUOUS = 0
        self.wait_for_idle(timeout=20)

    def arm_transient(self):
        """Arm transient capture"""
        if self.capture_state == CAPTURE_STATE['ARM']: return
        logging.debug(f"Arming capture {self.hostname}")
        self.s0.set_arm = 1
        
    def wait_for_idle(self, timeout=None):
        """Blocks until UUT reaches IDLE"""
        self.wait_for_state(CAPTURE_STATE.IDLE, timeout)

    def wait_for_arm(self, timeout=None):
        """Blocks until UUT reaches ARM"""
        self.wait_for_state(CAPTURE_STATE.ARM, timeout)

    def wait_for_state(self, target_state, timeout=None):
        """Blocks until UUT reaches state"""
        if isinstance(target_state, str): target_state = CAPTURE_STATE[target_state.upper()]
        logging.debug(f"{self.addr} Wait for {target_state.name} timeout={timeout}")
        t0 = time.time()
        while self.capture_state != target_state:
            t1 = time.time() - t0
            if timeout and t1 > timeout: raise TimeoutError(f'{self.addr} failed to reach {target_state.name} after {timeout}s')
            time.sleep(1)
        logging.debug(f"{self.addr} reached {target_state.name}")

    def wait_for_nsamples(self, nsamples, timeout=None):
        """Blocks until UUT reaches nsamples"""
        if not self.ai_master: return
        logging.debug(f"{self.addr} Wait for {nsamples} samples timeout={timeout}")
        t0 = time.time()
        while self.sample_count < nsamples:
            t1 = time.time() - t0
            if timeout and t1 > timeout: raise TimeoutError(f'{self.addr} failed to reach {nsamples} samples after {timeout}s')
            time.sleep(1)
        logging.debug(f"{self.addr} reached {nsamples} samples")

    def wait_for_transient_complete(self, timeout=None):
        """Wait until transient post processing is complete"""
        if not self.ai_master: return
        logging.debug(f"{self.addr} Wait for transient complete timeout={timeout}")
        t0 = time.time()
        while self.s0.TRANS_ACT__CH__DATA_VALID != '1':
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
            data = UUTData(raw, sample_format, self.es_width)
        else:
            data = UUTData(self.read_from_port(PORTS.DATA0, sample_format.dtype, tsamples), sample_format, self.es_width)

        logging.info(f"Read {data.nbytes} bytes from {self.hostname}")
        return data

    def stream_to_host(self, bytes, port=PORTS.STREAM, sample_format=None, datafile=None, bufferlen=4*(1024*1014)):
        """Stream data to host"""

        if not self.stream_enabled: 
            logging.warning(f"{self.hostname} Streaming not enabled")
        
        if not self.rgm_enabled and self.data_rate_masked > MAX_ETH_RATE: 
            logging.warning(f"{self.hostname} Stream datarate above {MAX_ETH_RATE} MB/s")

        if isinstance(datafile, str): datafile = open(datafile, 'wb')
        savepath = getattr(datafile, 'name')
        logging.debug(f"Streaming to host {bytes} Bytes")


        bytes = int((bytes // sample_format.bytes) * sample_format.bytes)
        nsamples = int(bufferlen // sample_format.bytes)
        bufferlen = int(nsamples * sample_format.bytes)

        buffer = bytearray(bufferlen)
        view = memoryview(buffer).cast('B')
        array = np.ndarray((nsamples,), dtype=sample_format.dtype, buffer=view)

        spads = sample_format.types.get('SPD', [])
        spad0_chan = spads[0] if spads else None

        self.stream = DotDict({
            'total_bytes': 0,
            'time_start': 0,
            'missed': 0,
            'savepath': savepath,
            'bytes': bytes,
        })

        logging.info(f"{self.hostname} Init stream {bytes >> 20} MiB ({self.data_rate_masked}MB/s)")

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
                    self.stream.total_bytes += nbytes

                    if self.stream.time_start == 0: 
                        self.stream.time_start = time.time()

                    if cursor >= bufferlen:
                        #print(f"{self.stream.total_bytes:,} / {bytes:,}")
                        trim = max(0, self.stream.total_bytes - bytes)
                        if datafile: datafile.write(buffer[:cursor - trim])
                        cursor = 0

                        if spad0_chan != None:
                            spad0_data = array[str(spad0_chan)]
                            self.stream.missed += np.sum(np.diff(spad0_data, prepend=spad0_last) - 1)
                            spad0_last = spad0_data[-1]

                        if self.stream.total_bytes >= bytes: break

            except KeyboardInterrupt: pass

        if datafile: datafile.close()
        
        logging.info(f"{self.hostname} Finshed {self.stream.total_bytes >> 20}MB ({self.stream.total_bytes // sample_format.bytes} Samples)  streamed to {savepath}")
        if self.stream.missed > 0: logging.warning(f"{self.hostname} Stream {self.stream.missed} missing samples")

        return savepath
   
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

    def set_trigger_source(self, source):
        """Set trigger source in"""
        source = source.upper()
        line = TRG_LINE[source]
        if line.value == 0: self.s0.SIG__SRC__TRG__0 = source
        if line.value == 1: self.s0.SIG__SRC__TRG__1 = source

    def configure_trigger(self, trigger):
        print("configure trigger")
        #self.ai_master.trg
        #self.

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
        auto_soft_trigger=0,
        stream_mask=None,
        sites=None,
        spad=None,
        ):
        """Configures uut for capture"""
        if not self.ai_master: return
        logging.debug(f"{self.hostname} Configuring capture")

        # Auto soft trigger causes problems force off
        auto_soft_trigger=0
        self.s0.TRANSIENT__PRE = pre
        self.s0.TRANSIENT__POST = post
        self.s0.TRANSIENT__SOFT_TRIGGER = auto_soft_trigger

        self.s0.transient = f"PRE={int(pre)} POST={int(post)} SOFT_TRIGGER={auto_soft_trigger} DEMUX={demux}"
        self.ai_master.trg = trigger
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
        mask = self.s0.stream_subset_mask
        if mask.lower() == 'none': return None
        return bitmask_to_chans(mask)

    def get_stream_mask(self):
        """Get the stream mask channels"""
        sample = StreamSample(self, None)
        mask = self.get_stream_mask_raw()
        if not mask: return None
        return sorted(list({sample.physical[chan] for chan in mask}))

    def set_stream_mask(self, mask):
        """Set the stream mask chanmels"""
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

    def trigger(self, trigger=None, siggen=None):
        if trigger and trigger.line == 1: 
            logging.info(f'Soft triggering')
            self.trigger_soft_trigger()
        elif siggen:
            logging.info(f'Triggering {siggen}')
            siggen.trigger()


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
    

if __name__ == '__main__':

    uutnames = ['acq2106_130', 'acq2106_054']
    uuts = Collection(uutnames)
    print(uuts)
    uuts.set_sync_role(1000000)