import threading
import atexit
import logging
import socket
import re
import time

from acq400_cli.exception import KnobNotFoundError
from acq400_cli.constants import PORTS
from acq400_cli.utils import RThread, background_task, generate_timestamp
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

    def __init__(self, uuts, savedir='DATA', filebytes=None, filesamples=None, timestamp=False, hexdump=False, save=True):
        self.uuts=uuts
        self.savedir=savedir
        self.filebytes=filebytes
        self.filesamples=filesamples
        self.timestamp=timestamp
        self.hexdump=hexdump
        self.save=save
        self.streams = {}

    def start(self, port=PORTS.STREAM, seconds=10, samples=None, bytes=None):
        """stream from each UUT in a thread"""
        logging.debug("Starting stream client")
        timestamp = generate_timestamp() if self.timestamp else None

        def wrapper(uut):
            if not uut.stream_enabled:
                logging.error(f"Streaming not enabled on {uutname}")
                return

            sample_format = uut.stream_sample_format

            filebytes = self.filebytes
            if self.filesamples: filebytes = sample_format.bytes * self.filesamples
            if filebytes: logging.info(f"{uut.addr} File {filebytes} Bytes")

            if samples: bytes = sample_format.bytes * samples
            elif seconds: bytes = int(seconds * sample_format.bytes * uut.sample_rate)

            datafile = None
            if self.save:
                datafile = StreamDataFile(
                    self.savedir,
                    filesize=filebytes,
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

    def finshed(self):
        """True if streams finshed else False"""
        return all(not stream.is_alive() for stream in self.streams.values())

    @background_task
    def print_status(self):
        """Print UUT status until finshed"""
        while not self.finshed():
            for status in self.uuts.get_stream_status().values():
                if status is not None:
                    print(status)
            time.sleep(1)

class StatusMontior:
    """Monitor status in background"""

    def __init__(self, addr):
        self.addr = addr
        self.port = 2227
        self.lock = threading.Lock()
        self.sock = None
        self.online = True

        self._status = {
            'state': None,
            'pre': 0,
            'post': 0,
            'elapsed': 0,
            'extra': 0,
            'shot': 0,
            'complete': False,
        }

        atexit.register(self.close)
        threading.Thread(target=self.__monitor, daemon=True).start()

    def __getattr__(self, key):
        if key in self._status:
            with self.lock:
                return self._status[key]
        return super().__getattr__(key)

    def is_complete(self):
        with self.lock:
            if self._status['complete']:
                self._status['captured'] = False
                return True
            return False

    def close(self):
        """Close socket"""
        if self.sock:
            self.sock.close()
            self.sock = None

    def __monitor(self):
        rate = 1
        last = None
        last_update = time.time()
        prev_state = '0'

        self.close()
        sock = socket.socket()
        sock.connect((self.addr, self.port))
        try:
            while True:
                line = sock.recv(200).strip()

                if not line: break
                if not line.startswith(b'STX'): continue
                
                now = time.time()
                if last == line[:5] and now - last_update < rate: continue

                state, pre, post, elapsed, extra = line.decode().split(' ')[1:]
                with self.lock:

                    if prev_state != '0' and state == '0':
                        self._status['shot'] += 1
                        self._status['complete'] = True
                    if state == '0': self._status['complete'] = False

                    self._status['state'] = state
                    self._status['pre'] = pre
                    self._status['post'] = post
                    self._status['elapsed'] = elapsed
                    self._status['extra'] = extra

                prev_state = state
                last = line[:5]
                last_update = now
        except Exception: pass
        
        logging.debug(f"{self.addr} monitor disconnected")
        self.online = False
        self.close()
