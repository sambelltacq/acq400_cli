"""
argparsing classes
"""


import argparse
from acq400_cli.utils import Triplet, SigGen
from acq400_cli.constants import SIG_LINE, SENSE, RGM_MODE, GPG_MODE

class ArgTypes:
    sig_src = list(SIG_LINE.__members__)
    gpg_mode = list(GPG_MODE.__members__)

    @staticmethod
    def list_of_ints_comma(arg):
        return list(map(int, arg.split(',')))

    @staticmethod
    def list_of_strings_comma(arg):
        return arg.split(',')

    @staticmethod
    def list_of_strings_slash(arg):
        return arg.split('/')

    @staticmethod
    def list_of_channels(arg):
        if arg.upper() == 'ALL': return []
        channels = []
        for chan in arg.split(','):
            if '-' in chan:
                start, end = map(int, chan.split('-'))
                channels.extend(list(range(start, end + 1)))
            else:
                channels.append(int(chan))
        return channels

    @staticmethod
    def int_with_unit(value):
        """Converts values with units to intergers"""
        units = {
            "k": 1e3,
            "M": 1e6,
            "G": 1e9,
            "kB": 1024,
            "MB": 1024**2,
            "GB": 1024**3,
        }

        scaler = 1
        for unit in units:
            if value.lower().endswith(unit.lower()):
                scaler = units.get(unit, 1)
                value = value[:-len(unit)]
                break
        return int(float(value) * scaler)

    @staticmethod
    def list_of_triplets_old(triplets): #TODO remove me
        def _type(arg):
            if arg.lower() == 'all': return [Triplet(triplet) for triplet in triplets]
            args = arg.split('/')
            if not set(args).issubset(triplets):raise argparse.ArgumentTypeError(f"Invalid trinary value(s). Allowed: {triplets}")
            return [Triplet(trinary) for trinary in args]
        return _type

    @staticmethod
    def triplet(arg):
        arg = arg.split(',')
        if not len(arg) == 3: raise ValueError
        return Triplet(arg)

    @staticmethod
    def start_end_stride(value, default=(0, None, 1)):
        """Parses start:end:stride arg into tuple"""
        parts = value.strip().split(':')
        start = ArgTypes.int_with_unit(parts[0]) if parts and parts[0] else default[0]
        end = ArgTypes.int_with_unit(parts[1]) if len(parts) > 1 and parts[1] else default[1]
        stride = ArgTypes.int_with_unit(parts[2]) if len(parts) > 2 and parts[2] else default[2]
        if stride <= 0:
            raise argparse.ArgumentTypeError("stride must be greater than 0")
        if end is not None and end <= start:
            raise argparse.ArgumentTypeError("end must be greater than start")
        return (start, end, stride)

    @staticmethod
    def signal_triplet(arg):
        """Signal triplet arg type"""
        parts = arg.upper().split(',')
        try:
            if len(parts) == 1:
                trigger = Triplet([1, SIG_LINE[parts[0]].value, 1])
                trigger.source = parts[0]
            if len(parts) == 2:
                trigger = Triplet([1, SIG_LINE[parts[0]].value, SENSE[parts[1]].value])
                trigger.source = parts[0]
            if len(parts) == 3:
                trigger = Triplet(parts)
                trigger.source = None
            return trigger
        except Exception as e:
            print(e)
        raise ValueError

    @staticmethod
    def rgm_triplet(arg):
        """RGM triplet arg type"""
        parts = arg.upper().split(',')
        try:
            if len(parts) == 1:
                event = Triplet([RGM_MODE[parts[0]].value, 0, 1])
            if len(parts) == 2:
                event = Triplet([RGM_MODE[parts[0]].value, 0, SENSE[parts[1]].value])
            if len(parts) == 3:
                event = Triplet(parts)
            return event
        except: pass
        raise ValueError

    @staticmethod
    def spad(arg):
        if arg.count(',') == 2: return arg
        length = int(arg)
        enabled = 1 if length > 0 else 0
        return f"{enabled},{length},0"

    @staticmethod
    def siggen(arg):
        try: return SigGen(arg)
        except: pass
        raise ValueError
    
class ArgParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('formatter_class', argparse.ArgumentDefaultsHelpFormatter)
        kwargs.setdefault('add_help', False)
        super().__init__(*args, **kwargs)
        self.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
