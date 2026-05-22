#!/usr/bin/env python3

"""
Wait for UUTs to reach STATE
"""

import argparse
from acq400_cli import Collection, CAPTURE_STATE

def main(args):
    uuts = Collection(args.uutnames)
    print(f"Waiting for {args.state} Timeout {args.timeout}s {uuts.names}")
    uuts.wait_for_state(args.state, args.timeout)
    print(f"Reached {args.state} {uuts.names}")

def get_parser():
    parser = argparse.ArgumentParser(description='Wait for UUTs to reach STATE')
    state_names = [m.name for m in CAPTURE_STATE]
    parser.add_argument('--timeout', default=0, type=int, help='Timeout before error')
    parser.add_argument('--state', choices=state_names, required=True, help=f"State to wait for")
    parser.add_argument('uutnames', nargs='+', help="uut hostnames")
    return parser

if __name__ == '__main__':
    main(get_parser().parse_args())