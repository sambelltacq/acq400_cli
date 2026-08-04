
"""
Generate synthetic data for AWG or comparison


"""
import logging
import os
from dataclasses import dataclass
import numpy as np
from acq400_cli import SENSE, WAVE_FUNC, ArgTypes
from acq400_cli.sample import SampleFormatFromTag

class WDEF:
    @staticmethod
    def from_file(filepath):
        """import wdef file and return specs"""
        specs = []
        with open(filepath, 'r') as fp:
            for lno, line in enumerate(fp):
                line = line.strip()
                if not line or line.startswith("#"): continue
                try:
                    spec = WaveformSpec.from_spec(dict(item.split('=', 1) for item in line.rstrip(';').split(';')))
                    specs.append(spec)
                except Exception as e:
                    logging.warning(f"{filepath}:{lno} line invalid skipping")
                    continue
        return specs


@dataclass
class WaveformSpec:
    """
    A Class to define a waveform specification 

    Index: List of indexes to insert waveform
    Chans: List of channels to insert waveform (0 meaning all)
    Wavelength: Wavelength of one cycle
    Cycles: Total cycles of a waveform (-1 for fill)
    Truncate: Total samples to trim from the end of waveform
    Skip: Total samples to trim from start of waveform
    Sense: RISING (starts from index) or FALLING (ends at index)
    Phase Offset: Waveform offset in radians
    DC Offset: Verical offset as a fraction of full scale
    Shape: Waveform type (SINE, SQUARE, RAMP, DC)
    Scale: Amplitude relative to full scale
    Bits: TODO
    """
    index: list 
    chan: list
    wavelength: int
    cycles: int
    truncate: int
    skip: int
    sense: SENSE
    phase_offset: float
    dc_offset: float
    shape: WAVE_FUNC
    scale: float

    @classmethod
    def from_spec(cls, spec):
        return cls(
            index = ArgTypes.list_of_ints_or_ranges(spec.get('index', 0)),
            chan = ArgTypes.list_of_ints_or_ranges(spec.get('chan', 0)),
            wavelength = ArgTypes.int_with_unit(spec.get('wavelength', 5000)),
            cycles = int(spec.get('cycles', 1)),
            truncate = int(spec.get('truncate', 0)),
            skip = int(spec.get('skip', 0)),
            sense = SENSE(spec.get('sense', 1)),
            phase_offset = float(spec.get('phase_offset', 0)),
            dc_offset = float(spec.get('dc_offset', 0)),
            shape = WAVE_FUNC(spec.get('shape', 'SINE')),
            scale = float(spec.get('scale', 1)),
            #bits
        )


class Waveform(np.ndarray):
    """Generate synthetic data for AWG or comparison from specs"""

    def __new__(cls, tsamples, nchan, dsize, specs):
        tsamples = int(tsamples)
        nchan = int(nchan)
        specs = specs if isinstance(specs, (list, tuple)) else [specs]
        chan_dtype = np.int16 if dsize == 2 else np.int32
        dtype = np.dtype([(str(ch), chan_dtype) for ch in range(1, nchan + 1)])

        obj = np.zeros(tsamples, dtype=dtype).view(cls)
        obj.tsamples = tsamples
        obj.nchan = nchan
        obj.specs = specs
        obj.chan_dtype = chan_dtype
        obj.sample_format = SampleFormatFromTag(f"{nchan}CHx{dsize}B")
        info = np.iinfo(chan_dtype)
        obj.dtype_amplitude = min(abs(info.min), info.max)

        for spec in obj.specs:
            logging.debug(f"Inserting spec {spec}")
            obj.__apply_spec(spec)
        return obj

    def __apply_spec(self, spec):
        """Apply specs to Waveform arrays"""
        indexes = spec.index if isinstance(spec.index, (list, tuple)) else [spec.index]
        channels = list(self.__get_channels(spec.chan))

        for index in indexes:
            if isinstance(index, tuple):
                start, end, stride = index
                end = self.tsamples if end is None else end
                index_list = range(start, end, stride)
            else:
                index_list = [index]

            for index in index_list:
                if index > self.tsamples: continue

                waveform = self.__generate_waveform(spec, index)
                if waveform.size == 0: continue

                insert_len = self.__truncate_waveform(spec, waveform.size)
                if insert_len <= 0: continue

                for chan in channels:
                    if spec.sense == SENSE.FALLING:
                        self.__insert_falling(self[chan], index, waveform, insert_len)
                    if spec.sense == SENSE.RISING:
                        self.__insert_rising(self[chan], index, waveform, insert_len)

    def __get_channels(self, chans):
        """Resolve channels from spec.chan"""
        all_chans = [str(i) for i in range(1, self.nchan + 1)]
        if isinstance(chans, int): chans = [chans]

        valid_channels = []
        for chan in chans:
            if chan in (0, 'ALL'): return all_chans
            chan = int(chan)
            if 1 <= chan <= self.nchan:
                valid_channels.append(str(chan))
        return valid_channels

    def __truncate_waveform(self, spec, wavelength):
        """Truncate waveform"""
        if spec.truncate is not None and spec.truncate > 0:
            wavelength = min(wavelength, spec.truncate)
        return wavelength

    def __insert_falling(self, arr, index, waveform, insert_len):
        """Insert waveform segment before index (FALLING)"""
        segment = waveform[-insert_len:]
        seg_len = segment.size
        end = min(max(index, 0), self.tsamples)
        start = max(0, end - seg_len)
        slice_len = end - start
        if slice_len <= 0: return
        arr[start:end] = segment[-slice_len:]

    def __insert_rising(self, arr, index, waveform, insert_len): 
        """"Insert waveform segment after index (RISING)"""
        segment = waveform[:insert_len]
        seg_len = segment.size
        start = min(max(index, 0), self.tsamples)
        end = min(self.tsamples, start + seg_len)
        slice_len = end - start
        if slice_len <= 0: return
        arr[start:end] = segment[:slice_len]

    def __generate_waveform(self, spec, index):
        """Generate waveform from spec"""
        total_wavelength = self.__calculate_total_wavelength(spec, index)

        if total_wavelength <= 0: return np.array([], dtype=self.chan_dtype)

        if spec.shape == WAVE_FUNC.DC:
            return self.__scale_waveform(np.ones(total_wavelength), 0.0, spec.dc_offset)

        if spec.cycles == -1:
            num_cycles = total_wavelength / spec.wavelength
        else:
            num_cycles = spec.cycles

        phase = np.linspace(
            spec.phase_offset,
            spec.phase_offset + (num_cycles * 2) * np.pi,
            total_wavelength,
            endpoint=False,
        )

        if spec.shape == WAVE_FUNC.SINE:
            wave = np.sin(phase)
        elif spec.shape == WAVE_FUNC.SQUARE:
            wave = np.where(np.sin(phase) >= 0, 1.0, -1.0)
        elif spec.shape == WAVE_FUNC.RAMP:
            wave = 2.0 * ((phase / (2 * np.pi)) % 1.0) - 1.0

        if spec.skip: wave = wave[spec.skip:]

        return self.__scale_waveform(wave, spec.scale, spec.dc_offset)

    def __calculate_total_wavelength(self, spec, index):
        """Calculate total wavelength from wavelength and cycles"""
        if spec.shape == WAVE_FUNC.DC or spec.cycles == -1:
            available = (self.tsamples - index) if spec.sense == SENSE.RISING else index
        else:
            available = spec.cycles * spec.wavelength
        return max(0, int(available))

    def __scale_waveform(self, wave, scale, dc_offset=0.0):
        """Scale waveform to (dtype max * scale)"""
        full_scale = (wave * scale + dc_offset) * self.dtype_amplitude
        info = np.iinfo(self.chan_dtype)
        full_scale = np.clip(full_scale, info.min, info.max)
        return full_scale.astype(self.chan_dtype, copy=False)

    def save_to_file(self, filepath):
        """Save waveform to filepath"""
        logging.debug(f"Saving data to {filepath}")
        dirpath = os.path.dirname(filepath)
        if dirpath: os.makedirs(dirpath, exist_ok=True)
        self.tofile(filepath)

    
def calculate_phase_offset(ndarray, wavelength=None):
    """calculate the phase offset of a sine wave"""
    zero_crossings = find_zero_crossings(ndarray)
    if not wavelength: wavelength = estimate_wavelength(ndarray)
    if len(zero_crossings) == 0:
        return 0.0

    idx = zero_crossings[0]
    if idx + 1 >= len(ndarray):
        return 0.0

    y0 = ndarray[idx]
    y1 = ndarray[idx + 1]
    if y0 == y1:
        crossing_sample = idx
    else:
        frac = y0 / (y0 - y1)
        crossing_sample = idx + frac

    positive_crossing = y0 < 0 and y1 >= 0
    reference_phase = 0.0 if positive_crossing else np.pi

    sample_phase = (crossing_sample / wavelength) * 2 * np.pi
    phase_offset = reference_phase - sample_phase
    return (phase_offset + 2 * np.pi) % (2 * np.pi)

def estimate_wavelength(ndarray):
    """estimate the wavelength of a sine wave"""
    ndarray = np.asarray(ndarray)
    ndarray = ndarray - np.mean(ndarray)
    n = len(ndarray)
    nfft = 2 * n
    ndarray1 = np.fft.fft(ndarray, n=nfft)
    ndarray2 = ndarray1 * np.conj(ndarray1)
    corr = np.fft.ifft(ndarray2).real
    corr = corr[:n]
    peak = np.argmax(corr[1:]) + 1
    return peak

def find_zero_crossings(ndarray):
    """find zero crossings in array"""
    return np.nonzero(np.diff(np.signbit(ndarray)))[0]