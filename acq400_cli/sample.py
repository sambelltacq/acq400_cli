from itertools import groupby
from acq400_cli.utils import DotDict, RThread
from acq400_cli.constants import SIGNEDNESS
import numpy as np

class SampleFormat:
    """Defines sample format"""

    delineator='+'

    def _uut_to_spec(self, uut):
        """Convert UUT to sample spec"""
        def async_wrapper(site):
            data_size = uut[site].data_size
            nchan = uut[site].nchan
            if uut[site].is_ai:
                signedness = SIGNEDNESS.UNSIGNED if 0 in uut[site].input_range[0] else SIGNEDNESS.SIGNED
                return (nchan, ((data_size, signedness), 'ADC'))
            return ((nchan * data_size) // 4, ((4, SIGNEDNESS.UNSIGNED), 'DIO'))

        threads = []
        for site in uut.agg_sites:
            thread = RThread(target=async_wrapper, args=(site,))
            thread.start()
            threads.append(thread)
        spec = [thread.join() for thread in threads]

        spad_length = uut.spad_length
        if spad_length > 0:
            spec.append((spad_length, ((4, SIGNEDNESS.UNSIGNED), 'SPD')))
        return spec

    def _tag_to_spec(self, tag):
        """Convert tag to sample spec"""
        spec = []
        for part in tag.upper().split(self.delineator):
            if part.endswith('DIO'):
                nchan = int(part.split('DIO')[0])
                spec.append((nchan, ((4, SIGNEDNESS.UNSIGNED), 'DIO')))
            elif part.endswith('SPD'):
                nchan = int(part.split('SPD')[0])
                spec.append((nchan, ((4, SIGNEDNESS.UNSIGNED), 'SPD')))
            else:
                nchan = int(part.split('CHX')[0])
                size_part = part.split('CHX')[1].split('B')[0]
                signedness = SIGNEDNESS.UNSIGNED if 'U' in size_part else SIGNEDNESS.SIGNED
                data_size = int(size_part.replace('U', ''))
                spec.append((nchan, ((data_size, signedness), 'ADC')))
        return spec

    def _build_sample(self, spec, mask=None, spad_enabled=True):
        """build Sample from specs"""
        self.channels = {}
        self.physical = {}
        self.bytes = 0
        self.data_bytes = 0
        self.dtype = []
        self.types = {}

        logical_chan = 0
        physical_chan = 0
        min_chan_size = min(s[1][0][0] for s in spec)
    
        for nchan, ((chan_size, signedness), chan_type) in spec:

            if chan_type == 'ADC' and chan_size == 2 and signedness == SIGNEDNESS.SIGNED: dtype = np.int16
            if chan_type == 'ADC' and chan_size == 2 and signedness == SIGNEDNESS.UNSIGNED: dtype = np.uint16
            if chan_type == 'ADC' and chan_size == 4 and signedness == SIGNEDNESS.SIGNED: dtype = np.int32
            if chan_type == 'ADC' and chan_size == 4 and signedness == SIGNEDNESS.UNSIGNED: dtype = np.uint32
            if chan_type == 'DIO': dtype = np.uint32
            if chan_type == 'SPD': dtype = np.uint32

            self.types.setdefault(chan_type, [])

            for _ in range(nchan):

                logical_chan += 1
                physical_chan += 1

                channel = DotDict({
                    'chan_size': chan_size,
                    'signedness': signedness,
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
                if chan_type != 'SPD': self.data_bytes += chan_size
                self.channels[logical_chan] = channel
                self.physical.update({chan: channel for chan in channel['physical']})

        self.dtype = np.dtype(self.dtype)
        self.spec = self.__generate_spec()
        self.tag = self.__generate_tag()
        self.hexdump = self.gen_hexdump_cmd()

    def __generate_spec(self):
        """Generate spec"""""
        specs = ((self.channels[c].chan_size, self.channels[c].signedness, self.channels[c].chan_type) for c in self.channels)
        return [[len(list(group)), key] for key, group in groupby(specs)]

    def __generate_tag(self):
        """Generate tag"""
        tag = []
        for nchan, (chan_size, signedness, chan_type) in self.spec:
            if chan_type == 'ADC':
                signedness_char = 'u' if signedness == SIGNEDNESS.UNSIGNED else ''
                label = f"{{nchan}}CHx{{chan_size}}{signedness_char}B"
            if chan_type == 'DIO': label = "{nchan}DIO"
            if chan_type == 'SPD': label = "{nchan}SPD"
            tag.append(label.format(nchan=nchan, chan_size=chan_size))
        return self.delineator.join(tag)

    def gen_hexdump_cmd(self, as_width=None):
        fmt = []
        for nchan, (chan_size, signedness, chan_type) in self.spec:
            if as_width:
                nchan = nchan * chan_size // as_width
                chan_size = as_width
            fmt.append(f'{nchan}/{chan_size} "%0{chan_size * 2}x,"')
        fmt.append(r'"\n"')
        return f"hexdump -e '{' '.join(fmt)}' -s $(({self.bytes} * 0)) $DATAFILE | cut -d, -f1- | head"

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