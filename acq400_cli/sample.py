from itertools import groupby
from acq400_cli.utils import DotDict
import numpy as np

class SampleFormat:
    """Defines sample format"""

    delineator='+'

    def _uut_to_spec(self, uut):
        """Convert UUT to sample spec"""
        spec = []
        for site in uut.agg_sites:
            data_type = 'ADC' if uut[site].is_ai else 'DIO'
            data_size = uut[site].data_size
            nchan = uut[site].nchan
            spec.append((nchan, (data_size, data_type)))

        spad_length = uut.spad_length
        if spad_length > 0:
            spec.append((spad_length, (4, 'SPD')))
        return spec

    def _tag_to_spec(self, tag):
        """Convert tag to sample spec"""
        spec = []
        for part in tag.upper().split(self.delineator):
            if part.endswith('DIO'):
                nchan = int(part.split('DIO')[0])
                spec.append((nchan, (4, 'DIO')))
            elif part.endswith('SPD'):
                nchan = int(part.split('SPD')[0])
                spec.append((nchan, (4, 'SPD')))
            else:
                nchan = int(part.split('CHX')[0])
                data_size = int(part.split('CHX')[1].split('B')[0])
                spec.append((nchan, (data_size, 'ADC')))
        return spec

    def _build_sample(self, spec, mask=None, spad_enabled=True):
        """build Sample from specs"""
        self.channels = {}
        self.physical = {}
        self.bytes = 0
        self.dtype = []
        self.types = {}

        logical_chan = 0
        physical_chan = 0
        min_chan_size = min(s[1][0] for s in spec)
    
        for nchan, (chan_size, chan_type) in spec:

            if chan_type == 'ADC' and chan_size == 2: dtype = np.int16
            if chan_type == 'ADC' and chan_size == 4: dtype = np.int32
            if chan_type == 'DIO': dtype = np.uint32
            if chan_type == 'SPD': dtype = np.uint32

            self.types.setdefault(chan_type, [])

            for _ in range(nchan):

                logical_chan += 1
                physical_chan += 1

                channel = DotDict({
                    'chan_size': chan_size,
                    'chan_type': chan_type,
                    'logical': [logical_chan],
                    'physical': [physical_chan],
                    'start': self.bytes,
                    'dtype': dtype,
                })

                if chan_size > min_chan_size:
                    physical_chan += 1
                    channel['physical'].append(physical_chan)

                if mask and not any(x in mask for x in channel['physical']): continue
                if not spad_enabled and chan_type == 'SPD': continue

                self.types[chan_type].append(logical_chan)
                self.dtype.append((str(logical_chan), dtype))
                self.bytes += chan_size
                self.channels[logical_chan] = channel
                self.physical.update({chan: channel for chan in channel['physical']})

        self.dtype = np.dtype(self.dtype)
        self.spec = self.__generate_spec()
        self.tag = self.__generate_tag()
        self.hexdump = self.__generate_hexdump()

    def __generate_spec(self):
        """Generate spec"""""
        specs = ((self.channels[c].chan_size, self.channels[c].chan_type) for c in self.channels)
        return [[len(list(group)), size] for size, group in groupby(specs)]

    def __generate_tag(self):
        """Generate tag"""
        tag = []
        for nchan, (chan_size, chan_type) in self.spec:
            if chan_type == 'ADC': label = "{nchan}CHx{chan_size}B"
            if chan_type == 'DIO': label = "{nchan}DIO"
            if chan_type == 'SPD': label = "{nchan}SPD"
            tag.append(label.format(nchan=nchan, chan_size=chan_size))
        return self.delineator.join(tag)

    def __generate_hexdump(self):
        fmt = [f'{nchan}/{chan_size} "%0{chan_size * 2}x,"' for nchan, (chan_size, chan_type) in self.spec]
        fmt.append(r'"\n"')
        fmt_str = ' '.join(fmt)
        return f"hexdump -e '{fmt_str}'"

    def __str__(self):
        return f"<SampleFormat tag='{self.tag}' bytes='{self.bytes}'>"


class TransientSample(SampleFormat):
    """Defines Transient sample format"""

    def __init__(self, uut, spad_enabled=None):
        spec = self._uut_to_spec(uut)
        if spad_enabled == None: spad_enabled = not uut.is_demuxed
        self._build_sample(spec, spad_enabled=spad_enabled)


class StreamSample(SampleFormat):
    """Defines Stream sample format"""

    def __init__(self, uut, mask=[]):
        spec = self._uut_to_spec(uut)
        if mask == []: mask = uut.get_stream_mask_raw()
        self._build_sample(spec, mask=mask)


class SampleFormatFromTag(SampleFormat):
    """Defines sample format from tag"""

    def __init__(self, tag):
        spec = self._tag_to_spec(tag)
        self._build_sample(spec)