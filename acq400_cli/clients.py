import threading
import atexit
import logging
import socket
import re

from acq400_cli.exception import KnobNotFoundError
from acq400_cli.constants import PORTS
from acq400_cli.utils import RThread, generate_timestamp
from acq400_cli.data import StreamDataFile

class Client:
    pass


class CommandClient(Client):
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
            logging.debug(f"{self.addr}:{self.port} Initing Socket")
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
            logging.trace(f"{self.addr}:{self.port} > {repr(rc)}")
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
            logging.debug(f"{self.addr}:{self.port} Closing Socket")
            self.sock.close()


class StreamClient():
    """Client to handle streaming from multiple UUTs"""

    def __init__(self, uuts, savedir='DATA', filebytes=None, filesamples=None, overwrite=False, hexdump=False, save=True):
        self.uuts=uuts
        self.savedir=savedir
        self.filebytes=filebytes
        self.filesamples=filesamples
        self.overwrite=overwrite
        self.hexdump=hexdump
        self.save=save
        self.streams = {}

    def start(self, port=PORTS.STREAM, seconds=10, samples=None, bytes=None):
        """stream from each UUT in a thread"""
        logging.debug("Starting stream client")
        timestamp = None if self.overwrite else generate_timestamp()

        def wrapper(uut):
            sample_format = uut.stream_sample_format

            filebytes = self.filebytes
            if self.filesamples: filebytes = sample_format.bytes * self.filesamples

            if samples: bytes = sample_format.bytes * samples
            elif seconds: bytes = int(seconds * sample_format.bytes * uut.sample_rate)

            datafile = None
            if self.save:
                datafile = StreamDataFile(
                    self.savedir,
                    filebytes,
                    sample_size=sample_format.bytes,
                    hostname=uut.hostname,
                    format=sample_format.tag,
                    timestamp=timestamp
                )

            savepath = uut.stream_to_host(bytes, port, sample_format, datafile)

            if self.hexdump: print(f"{sample_format.hexdump} {savepath}")

        for uutname, uut in self.uuts.items():
            self.streams[uutname] = RThread(target=wrapper, args=(uut,))
            self.streams[uutname].start()

    def trigger_when_armed(self, trigger=None, siggen=None):
        """Trigger UUTs when ARMED"""
        def wrapper():
            print("Waiting for ARM")
            self.uuts.wait_for_arm(timeout=30)
            print("Armed")
            if trigger and trigger.line == 1: 
                logging.info(f'Soft triggering')
                self.uuts.trigger_soft_trigger()
            elif siggen:
                logging.info(f'Triggering {siggen}')
                siggen.trigger()

        thread = RThread(target=wrapper, daemon=True)
        thread.start()

    def finshed(self):
        """True if streams finshed else False"""
        return all(not stream.is_alive() for stream in self.streams.values())

    def print_status(self):
        """Print UUT status until finshed"""
        while not self.finshed():
            for status in self.uuts.get_stream_status().values():
                if status is not None:
                    print(status)
