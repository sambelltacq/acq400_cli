"""
Utility classes and functions
"""

import time
import inspect
import threading
import logging
import socket
import weakref
import functools
from typing import Any, Callable

from acq400_cli.constants import TIMESTAMP_FMT

class Triplet(str):
    """Helper class for Triplets"""
    def __new__(cls, value, keys=['enabled', 'line', 'sense']):
        if isinstance(value, list):
            value = ",".join(map(str, value))
        value = value.split(' ')[0].lstrip("=")
        obj = super().__new__(cls, value)
        obj.keys = keys
        return obj
    
    def __getitem__(self, key):
        return int(self.split(',')[key])

    def __getattr__(self, attr):
        if attr not in self.keys:
            raise AttributeError(f"{type(self).__name__!r} object has no attribute {attr!r}")
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
    """Thread with return and stop"""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('daemon', True)
        super().__init__(*args, **kwargs)
        self.value = None
        self.exception = None
        self.stop_event = threading.Event()
        self.status = {}
        self.last_status = 0
    
    def run(self):
        try: self.value = self._target(*self._args, **self._kwargs)
        except Exception as e:
            self.exception = e
            logging.debug(f"{self.name} {e}")

    def join(self, *args, **kwargs):
        super().join(*args, **kwargs)
        if self.exception: raise self.exception
        return self.value

    def stop(self):
        self.stop_event.set()

class BackgroundTask:
    """Non blocking proxy UUT thread handler"""

    def __init__(self, thread=None, result=None):
        self.thread = thread
        self._result = result

    @classmethod
    def wrap(cls, obj):
        return cls(result=obj)

    def _value(self):
        if self.thread is None:
            return self._result
        return self.thread.join()

    def _spawn(self, fn):
        thread = RThread(target=fn)
        thread.start()
        return BackgroundTask(thread=thread)

    def __getattr__(self, name):
        return self._spawn(lambda: getattr(self._value(), name))

    def __call__(self, *args, **kwargs):
        return self._spawn(lambda: self._value()(*args, **kwargs))

    @property
    def finished(self):
        return self.thread is None or not self.thread.is_alive()

    def join(self, *args, **kwargs):
        if self.thread is None:
            return self._result
        return self.thread.join(*args, **kwargs)

    def stop(self):
        if self.thread is not None:
            self.thread.stop()

class FanoutProxy(dict):
    """Proxy UUT attributes and methods"""

    def _fanout(self, fn, *args):
        threads = {}
        for key, target in self.items():
            thread = RThread(target=fn, args=(target, *args))
            thread.start()
            threads[key] = thread
        return {key: thread.join() for key, thread in threads.items()}

    def __getattr__(self, name):
        return self.__class__(self._fanout(getattr, name))

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return
        self._fanout(setattr, name, value)

    def __call__(self, *args, **kwargs):
        results = self._fanout(lambda fn: fn(*args, **kwargs))
        if results and all(isinstance(v, BackgroundTask) for v in results.values()):
            return results
        return self.__class__(results)

class StopWatch:
    """easy delta time between marks"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            cls._instance.t0 = time.time()
            cls._instance.marks = [(0.0, 'START')]
        return cls._instance

    def mark(self, reason=None):
        if not reason: reason = f"MARK {len(self.marks)}"
        self.marks.append((time.time() - self.t0, reason))

    def __str__(self):
        lines = ['Stopwatch:']
        for elapsed, reason in self.marks:
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

    def volt_offset_from_range(self, v_min, v_max):
        """Convert input_range to voltage and offset"""
        amplitude = (float(v_max) - float(v_min)) / 2
        offset = (float(v_max) + float(v_min)) / 2
        return amplitude, offset

    def config_free_running(self, freq, voltage, offset=0, shape='SINE'):
        """Configure free running waveform"""
        if isinstance(voltage, (tuple, list)):
            voltage, offset = self.volt_offset_from_range(*voltage)
        self.send('BURS:STAT OFF')
        self.send(f"FREQ {freq}")
        self.send(f"VOLT {voltage}")
        self.send(f"VOLT:OFFS {offset}")
        self.send(f"FUNC:SHAP {shape}")
        self.send('TRIG:SOUR IMM')

    def config_burst(self, freq, voltage, offset=0, shape='SINE', cycles=1, period=None):
        """Config burst waveform"""
        if isinstance(voltage, (tuple, list)):
            voltage, offset = self.volt_offset_from_range(*voltage)
        self.send('BURS:STAT ON')
        self.send(f"FREQ {freq}")
        self.send(f"VOLT {voltage}")
        self.send(f"VOLT:OFFS {offset}")
        self.send(f"FUNC:SHAP {shape}")
        self.send(f"BURS:NCYC {cycles}")
        if period: self.send(f"BURS:INT:PER {period}")
        self.send(f"TRIG:SOUR BUS")

    def config_dc(self, voltage, scaler=2):
        """Config DC out"""
        voltage /= scaler
        self.send("SOUR:FUNC DC")
        self.send(f"SOUR:VOLT:LEV:IMM:OFFS {voltage}")


class Ansi:

    CLEAR = '\033[K'

    @staticmethod
    def move_up(nlines=1):
        if nlines < 1: return
        print(f'\033[{nlines}A', end='')

def is_task_stop():
    """return True if in a thread and thread stop else False"""
    stop = getattr(threading.current_thread(), 'stop_event', None)
    if not stop: return True
    return stop.is_set()

def write_task_status(status, limit=1):
    """write status to thread if status available"""
    thread = threading.current_thread()
    if not hasattr(thread, 'status'): return
    now = time.time()
    if now - thread.last_status < limit: return
    thread.last_status = now
    thread.status = status

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

def background_task(func: Callable[..., Any]) -> Callable[..., RThread]:
    """Runs passed func in the background returns thread"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> RThread:
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

def require_ai_master(fn):
    def wrapper(self, *args, **kwargs):
        if not self.ai_master: return None
        return fn(self, *args, **kwargs)
    return wrapper

def require_ao_master(fn):
    def wrapper(self, *args, **kwargs):
        if not self.ao_master: return None
        return fn(self, *args, **kwargs)
    return wrapper