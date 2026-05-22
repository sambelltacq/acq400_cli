#!/usr/bin/env python3

"""Demux datafiles into chan datafiles"""

import argparse

from acq400_cli import ArgTypes, plot_by_carrier
from acq400_cli.data import UUTData


def main(args):
    print(args)
    print("no worky :(")

    for filename in args.filenames:
        print(filename)
        data = UUTData.from_file(filename)
        print(data)
    

def get_parser():
    parser = argparse.ArgumentParser(description='Demux datafiles into channels')

    parser.add_argument('--savedir', default="DEMUXED_DATA", help='Save dir')

    parser.add_argument('filenames', nargs='+', help='Datfiles')
    return parser


if __name__ == '__main__':
    main(get_parser().parse_args())