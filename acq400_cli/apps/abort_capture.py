#!/usr/bin/env python3

"""
Abort capture on UUTs
"""

from acq400_cli import Collection, ArgParser

def main(args):
    uuts = Collection(args.uutnames)
    print(f"Aborting capture {uuts.names}")
    uuts.abort_capture()
    print(f"Capture Aborted {uuts.names}")

def get_parser():
    parser = ArgParser(description='Abort capture')
    parser.add_argument('uutnames', nargs='+', help="uut hostnames")
    return parser

if __name__ == '__main__':
    print('main running?')
    main(get_parser().parse_args())