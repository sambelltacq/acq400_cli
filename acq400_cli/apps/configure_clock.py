#!/usr/bin/env python3

"""
Config CLK and HDMI on UUTS
"""

import argparse
from acq400_cli import ArgTypes, Collection

def main(args):

    uuts = Collection(args.uutnames)

    print(f"Sync Role {uuts.names}")

    uuts.set_sync_role(
        clk=args.clk,
        master_role=args.mrole,
        slave_role=args.srole,
    )
    
    for ii, (uutname, uut) in enumerate(uuts.masters.items()):
        if ii == 0: print('[ Masters ]')
        print(f"- {uutname} '{uut.s0.sync_role}' {uut.data_rate} MB/s")

    for ii, (uutname, uut) in enumerate(uuts.slaves.items()):
        if ii == 0: print('[ Slaves ]')
        print(f"- {uutname} '{uut.s0.sync_role}' {uut.data_rate} MB/s")

    print('[ Tree ]')
    print(uuts.tree)

def get_parser():
    parser = argparse.ArgumentParser(description='Config CLK and HDMI on UUTS')

    parser.add_argument('--mrole', default='master', help='Master role')
    parser.add_argument('--srole', default='slave', help='Slave role')
    parser.add_argument('--clk', required=True, type=ArgTypes.int_with_unit, help='Clock frequency')
    
    parser.add_argument('uutnames', nargs='+', help="uut hostnames")
    return parser

if __name__ == '__main__':
    main(get_parser().parse_args())