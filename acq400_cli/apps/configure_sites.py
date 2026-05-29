#!/usr/bin/env python3

"""
Configure sites on UUTs
"""

import argparse
from acq400_cli import ArgTypes, Collection

def main(args):
    uuts = Collection(args.uutnames)

    print(f"Configuring sites")
    uuts.run0(args.sites, args.spad)
    uuts.ident_spad(args.ident)
    uuts.set_spad1_count(args.us)

    for uutname, sample_format in uuts.transient_format.items():
        print(f"  {uutname} Sample {sample_format.tag} {sample_format.bytes} Bytes")

def get_parser():
    parser = argparse.ArgumentParser(description='Configure sites on UUTs')

    parser.add_argument('--spad', default=None, type=ArgTypes.spad, help='Spad length')
    parser.add_argument('--sites', default=None, help='run0 sites (1,2,3 or ALL)')
    parser.add_argument('--ident', action='store_true', help='Ident SPAD')
    parser.add_argument('--us', action='store_true', help='Insert microseconds into SPAD[1]')
    
    parser.add_argument('uutnames', nargs='+', help="uut hostnames")
    return parser

if __name__ == '__main__':
    main(get_parser().parse_args())