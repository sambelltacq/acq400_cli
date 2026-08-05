#!/usr/bin/env python3

"""
Load GPG STL into UUTs
"""

from acq400_cli import ArgTypes, ArgParser, Collection

def main(args):
    uuts = Collection(args.uutnames)

    uuts.configure_gpg(
        stl=args.stl, 
        mode=args.mode,
        timescaler=args.timescaler,
        trigger=args.trigger,
        clock=args.clock,
        bit=args.bit
    )

def get_parser():
    parser = ArgParser(description='Load GPG STL into UUTs')

    parser.add_argument('--stl', type=str, required=True, help='stl file')
    parser.add_argument('--mode', default='ONCE', choices=ArgTypes.gpg_mode, type=str.upper, help='GPG mode')
    parser.add_argument('--timescaler', '--ts', default=1, type=int, help="GPG timescaler")
    parser.add_argument('--trigger', '--trg', default=None, type=ArgTypes.signal_triplet, help='gpg trg triplet')
    parser.add_argument('--clock', '--clk', default=None, type=ArgTypes.signal_triplet, help='gpg clk triplet')
    parser.add_argument('--bit', default=0, type=int, help='gpg target bit')

    parser.add_argument('uutnames', nargs='+', help="uut hostnames")
    return parser

if __name__ == '__main__':
    main(get_parser().parse_args())