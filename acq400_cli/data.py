"""
Data handling
"""

import os
import io
import math
import logging

import numpy as np

from acq400_cli.sample import SampleFormatFromTag
from acq400_cli.utils import DotDict

class Dataset:pass


class UUTData(np.ndarray):
    """Wrapper class for UUT data"""

    def __new__(cls, input_array, sample_format):

        obj = np.asanyarray(input_array).view(cls)
        obj.sample_format = sample_format
        obj.channels = {chan: obj[str(chan)].view(np.ndarray) for chan in sample_format.channels}
        obj.adc = {chan: obj[str(chan)] for chan in sample_format.types.get('ADC', [])}
        obj.dio = {chan: obj[str(chan)] for chan in sample_format.types.get('DIO', [])}
        obj.spd = {idx: obj[str(chan)] for idx, chan in enumerate(sample_format.types.get('SPD', []))}
        obj.samples = obj.view(np.ndarray)
        obj.length = len(obj.samples)

        return obj

    def __str__(self):
        if not hasattr(self, "sample_format"): return np.ndarray.__str__(self)
        return f"<UUT Data {len(self)} Samples x {self.sample_format.tag} ({self.sample_format.bytes} Bytes)>"

    @classmethod
    def from_file(cls, filepath):
        """Init from file using memory mapping"""
        
        parts = parse_filename_parts(filepath)
        if not parts.format: logging.error("No format tag")
        sample_format = SampleFormatFromTag(parts.format)

        sample_bytes = sample_format.bytes
        file_size = os.path.getsize(filepath)
        n_samples = file_size // sample_bytes

        data = np.memmap(
            filepath,
            dtype=sample_format.dtype,
            mode='r',
            shape=(n_samples,),
        )

        return cls(data, sample_format)



class StreamDataFile(io.BufferedWriter):
    """BufferedWriter with optional file rotation"""

    def __init__(self, savedir='DATA', filesize=None, sample_size=None, **kwargs):
        if filesize and sample_size: filesize = math.ceil(filesize / sample_size) * sample_size
        self.filesize = filesize
        self.sample_size = sample_size
        self.savedir = savedir
        self.kwargs = kwargs
        self.total_bytes = 0
        self.seq = 0
        self.filepath = self._filepath()
        super().__init__(io.FileIO(self.filepath, 'wb'))

    def _filepath(self):
        os.makedirs(self.savedir, exist_ok=True)
        seq = self.seq if self.filesize is not None else None
        filename = gen_data_filename(seq=seq, **self.kwargs)
        return os.path.join(self.savedir, filename)

    def _rotate(self):
        self.total_bytes = 0
        self.seq = (self.seq + 1) % 1000
        self.flush()
        self.raw.close()
        self.filepath = self._filepath()
        os.makedirs(self.savedir, exist_ok=True)
        io.BufferedWriter.__init__(self, io.FileIO(self.filepath, 'wb'))

    def write(self, buffer):
        if not self.filesize:
            nbytes = super().write(buffer)
            self.total_bytes += nbytes
            return nbytes

        nbytes = 0
        offset = 0
        while offset < len(buffer):
            space = self.filesize - self.total_bytes
            if not space:
                self._rotate()
                space = self.filesize
            n = min(len(buffer) - offset, space)
            nbytes += super().write(buffer[offset:offset + n])
            self.total_bytes += n
            offset += n
        return nbytes

def gen_data_filename(hostname, format, timestamp=None, seq=None, **kwargs):
    """Generate dat filename"""
    parts = [hostname]
    if timestamp: parts.append(timestamp)
    parts.append(format)
    if seq is not None: parts.append(f"{seq:03}")
    return '.'.join(parts) + '.dat'

def parse_filename_parts(filepath):
    parts = DotDict({})
    filename = os.path.splitext(os.path.basename(filepath))[0]

    for part in filename.split('.'):
        upper = part.upper()
        if upper.startswith(('ACQ', 'Z7IO', 'KMCUZ')):
            parts.hostname = part
        elif part.count('-') == 4:
            parts.timestamp = part
        elif any(m in upper for m in ('CHX', 'DIO', 'SPD')):
            parts.format = part
        elif part.isnumeric():
            parts.sequence = part
    return parts

def generate_array_mask(length, indexes, width=1):
    """Generates a array mask"""
    mask = np.full(length, True)
    for index in indexes:
        mask[index: index + width] = False
    return mask

def find_event_signatures(data):
    """Returns event signature indexes within data"""
    if data.itemsize % 4 != 0: return []

    event_signatures = [
        0xaa55f151,
        0xaa55f152,
        0xaa55f154,
    ]

    nchan = data.itemsize // 4
    view = data.view(np.uint32).reshape(-1, nchan).T
    for chan in view:
        for es in event_signatures:
            indexes = np.where(chan == es)[0]
            if len(indexes) > 0: return indexes
    return []