"""
argparsing classes
"""


import argparse
from acq400_cli.utils import Triplet
from acq400_cli.constants import TRG_LINE, SENSE


class ArgTypes:
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
    def si_numeral(arg):
        prefixes = {
            "K": 1e3,
            "M": 1e6,
            "G": 1e9,
            "kB": 1024,
            "MB": 1024**2,
            "GB": 1024**3,
        }

        scaler = 1
        num = arg
        for prefix in sorted(prefixes, key=len, reverse=True):
            if arg.upper().endswith(prefix):
                scaler = prefixes.get(prefix, 1)
                num = arg[:-len(prefix)]
                break
        return int(float(num) * scaler)

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
    def trigger(arg):
        parts = arg.upper().split(',')
        try:
            if len(parts) == 2:
                source, sense = parts
                trigger = Triplet([1, TRG_LINE[source].value, SENSE[sense].value])
                trigger.source = source
            if len(parts) == 3:
                trigger = Triplet(parts)
                trigger.source = None
            return trigger
        except: pass
        raise ValueError

    @staticmethod
    def spad(arg):
        if arg.count(',') == 2: return arg
        length = int(arg)
        enabled = 1 if length > 0 else 0
        return f"{enabled},{length},0"

class CustomParser(argparse.ArgumentParser):
    pass
        


def get_parser():
    parser = CustomParser(
        prog='acq400_cli',
        description='ACQ400 Regression Testing Framework',
        add_help=False
    )
    parser.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)
    

