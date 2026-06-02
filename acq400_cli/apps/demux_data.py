#!/usr/bin/env python3

"""Demux datafiles into chan datafiles"""

import argparse

from acq400_cli import ArgTypes
from acq400_cli.data import demux_datafile

def main(args):
    for filename in args.filenames:
        save_dir = demux_datafile(filename)
        print(f"Demuxed {filename} --> {save_dir}")

def get_parser():
    parser = argparse.ArgumentParser(description='Demux datafiles into channels')
    parser.add_argument('--savedir', default='DEMUXED_DATA', help='Dir to save demuxed dir to')
    parser.add_argument('--chunk_samples', type=int, default=1000000, help='Samples per chunk')
    parser.add_argument('--max_samples', default=None, type=ArgTypes.si_numeral, help='Max samples to demux')
    parser.add_argument('filenames', nargs='+', help='data filenames')
    return parser


if __name__ == '__main__':
    main(get_parser().parse_args())
