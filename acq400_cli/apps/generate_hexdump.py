#!/usr/bin/env python3

"""
Generate hexdump command for UUTs
"""

from acq400_cli import Collection, ArgParser

def main(args):
    uuts = Collection(args.uutnames)
    for uut in uuts:
        if args.transient:
            sample_format = uut.transient_sample_format
        if args.stream:
            sample_format = uut.stream_sample_format
        print(f"[{uut.hostname}]: {sample_format.hexdump}")

def get_parser():
    parser = ArgParser(description='Generate hexdump command for UUTs')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--transient', action='store_true', help='Transient format')
    group.add_argument('--stream', action='store_true', help='Stream format')
    parser.add_argument('uutnames', nargs='+', help="uut hostnames")
    return parser

if __name__ == '__main__':
    main(get_parser().parse_args())