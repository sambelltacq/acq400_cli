"""
Utility classes and functions
"""

import time
import inspect
import threading
import logging
import socket
import weakref

from acq400_cli.constants import TIMESTAMP_FMT

class Triplet(str):
    """Helper class for Triplets"""
    keys = ['enabled', 'line', 'sense']
    def __new__(cls, value):
        if isinstance(value, list):
            value = ",".join(map(str, value))
        value = value.split(' ')[0].lstrip("=")
        return str.__new__(cls, value)
    
    def __getitem__(self, key):
        return int(self.split(',')[key])

    def __getattr__ (self, attr):
        return int(self[self.keys.index(attr)])
    
    def override(self, name, value):
        arr = self.split(',')
        arr[self.keys.index(name)] = str(value)
        return ','.join(arr)

class DotDict(dict):
    __delattr__ = dict.__delitem__
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class cached_property:
    """Instanced functools.cached_property"""

    _instance_locks = weakref.WeakKeyDictionary()

    def __init__(self, func):
        self.func = func
        self.attrname = None
        self.__doc__ = func.__doc__

    def __set_name__(self, owner, name):
        self.attrname = name

    def _lock(self, instance):
        locks = self._instance_locks.setdefault(instance, {})
        return locks.setdefault(self.attrname, threading.Lock())

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        cache = instance.__dict__
        if self.attrname in cache:
            return cache[self.attrname]
        with self._lock(instance):
            if self.attrname in cache:
                return cache[self.attrname]
            val = self.func(instance)
            cache[self.attrname] = val
            return val


class RThread(threading.Thread):
    """Thread with return"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.value = None
        self.exception = None
    
    def run(self):
        try: self.value = self._target(*self._args, **self._kwargs)
        except Exception as e:
            self.exception = e
            logging.debug(f"{self.name} {e}")

    
    def join(self, *args, **kwargs):
        super().join(*args, **kwargs)
        if self.exception: raise self.exception
        return self.value

class FanoutProxy(dict):
    """Proxy UUT attributes and methods"""

    def __init__(self, uuts, blocking=True, pending=None):
        super().__init__(uuts)
        object.__setattr__(self, '_blocking', blocking)
        object.__setattr__(self, '_pending', [] if pending is None else pending)
    
    def __getattr__(self, name):
        threads = []
        for key, target in self.items():
            thread = RThread(target=getattr, args=(target, name))
            thread._fanout_key = key
            thread.start()
            threads.append(thread)
        results = {thread._fanout_key: thread.join() for thread in threads}
        return self.__class__(results, self._blocking, self._pending)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return

        threads = []
        for key, target in self.items():
            thread = RThread(target=setattr, args=(target, name, value))
            thread._fanout_key = key
            thread.start()
            threads.append(thread)
        
        if not self._blocking:
            self._pending.extend(threads)
            return

        for thread in threads:
            thread.join()

    def __call__(self, *args, **kwargs):
        threads = []

        for key, fn in self.items():
            thread = RThread(target=fn, args=args, kwargs=kwargs)
            thread._fanout_key = key
            thread.start()
            threads.append(thread)

        if not self._blocking:
            self._pending.extend(threads)
            return

        results = {thread._fanout_key: thread.join() for thread in threads}
        return self.__class__(results, self._blocking, self._pending)

    def wait_for_complete(self):
        """Wait for threads to complete then enable blocking"""
        results = {thread._fanout_key: thread.join() for thread in self._pending}
        self._pending.clear()
        self._blocking = True
        return self.__class__(results, self._blocking, self._pending)

    def disable_blocking(self):
        """disable blocking"""
        self._blocking = False

class StopWatch(list):
    """easy delta time between marks"""
    def __init__(self):
        """Start timer"""
        super().__init__([(0, 'START')]) 
        self.t0 = time.time()

    def mark(self, reason=None):
        t1 = time.time()
        if not reason: reason= f"MARK {len(self)}"
        self.append((t1 - self.t0, reason))

    def __str__(self):
        lines = ['Stopwatch:']
        for elapsed, reason in self:
            lines.append(f"{elapsed:.2f}\t{reason}")
        return '\n'.join(lines)

class SigGen:
    """Send SCPI commands to siggen"""
    def __init__(self, addr):
        logging.debug(f"Initing Siggen {addr}")
        self.addr = addr
        self.socket = socket.socket()
        self.socket.connect((self.addr, 5025))

    def send(self, message):
        logging.trace(message)
        self.socket.send(f"{message}\n".encode())
        if message.endswith('?'): return self.socket.recv(100)

    def trigger(self):
        """Trigger SigGen"""
        self.send("TRIG")
        
    def sync_out(self, enabled=True):
        """Enable of disable output sync"""
        self.send(f"OUTP:SYNC {'ON' if enabled else 'OFF'}")

    def config_free_running(self, freq, voltage, shape='SINE'):
        """Configure free running waveform"""
        self.send('BURS:STAT OFF')
        self.send(f"FREQ {freq}")
        self.send(f"VOLT {voltage}")
        self.send(f"FUNC:SHAP {shape}")
        self.send('TRIG:SOUR IMM')

    def config_burst(self, freq, voltage, cycles=1, shape='SINE', period=None, source='BUS'):
        """Config burst waveform"""
        self.send('BURS:STAT ON')
        self.send(f"FREQ {freq}")
        self.send(f"VOLT {voltage}")
        self.send(f"FUNC:SHAP {shape}")
        self.send(f"BURS:NCYC {cycles}")
        if period: self.send(f"BURS:INT:PER {period}")
        self.send(f"TRIG:SOUR {source}")

    def config_dc(self, voltage, scaler=2):
        """Config DC out"""
        voltage /= scaler
        self.send("SOUR:FUNC DC")
        self.send(f"SOUR:VOLT:LEV:IMM:OFFS {voltage}")

def chans_to_bitmask(chans):
    """Converts list of chans to a hex bitmask"""
    return hex(sum(1 << (int(chan) - 1) for chan in sorted(chans)))

def generate_timestamp():
    """Return timestamp"""
    return time.strftime(TIMESTAMP_FMT, time.localtime())

def bitmask_to_chans(mask):
    """Converts a hex bitmask to list of chans"""
    mask = int(mask, 16)
    return [i + 1 for i in range(mask.bit_length()) if mask & (1 << i)]

def background_task(func):
    """Runs passed func in the background returns thread"""
    def wrapper(*args, **kwargs):
        thread = RThread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread
    return wrapper

def run_on_all_uuts(func):
    """Run decorated function on all UUTs"""
    sig = inspect.signature(func)
    is_method = sig.parameters.get('self', sig.parameters.get('cls')) != None

    def wrapper(uuts, *args, **kwargs):
        threads = {}
        for uut in uuts:
            threads[uut.hostname] = RThread(target=func, args=[uut, *args], kwargs=kwargs)
            threads[uut.hostname].start()
        for thread in threads.values():
            thread.join()
            if thread.exception is not None: raise thread.exception
        return {uutname: thread.value for uutname, thread in threads.items()}

    def object_wrapper(obj, uuts, *args, **kwargs):
        threads = {}
        for uut in uuts:
            threads[uut.hostname] = RThread(target=func, args=[obj, uut, *args], kwargs=kwargs)
            threads[uut.hostname].start()
        for thread in threads.values():
            thread.join()
            if thread.exception is not None: raise thread.exception
        return {uutname: thread.value for uutname, thread in threads.items()}

    return object_wrapper if is_method else wrapper