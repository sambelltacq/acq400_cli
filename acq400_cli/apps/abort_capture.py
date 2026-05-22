#!/usr/bin/env python3

"""
Abort capture on UUTs
"""

import argparse
from acq400_cli import Collection

def main(args):
    uuts = Collection(args.uutnames)
    uuts.abort_capture()
    print(f"Capture Aborted {uuts.names}")

def get_parser():
    parser = argparse.ArgumentParser(description='Abort capture')
    parser.add_argument('uutnames', nargs='+', help="uut hostnames")
    return parser

if __name__ == '__main__':
    print('main running?')
    main(get_parser().parse_args())