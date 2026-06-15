#!/usr/bin/env python3

"""
Configure capture on UUTs
"""

from acq400_cli import ArgTypes, Collection, ArgParser

def main(args):
    uuts = Collection(args.uutnames)

    uuts.wait_for_idle()

    uuts.configure_capture(
        pre=args.pre,
        post=args.post,
        trigger=args.trigger,
        event0=args.event0,
        event1=args.event1,
        rgm=args.rgm,
        translen=args.translen,
        demux=args.demux,
        stream_mask=args.stream_mask,
        sites=args.sites,
        spad=args.spad,
    )
    print(f"Capture Configured {uuts.names}")

def get_parser():
    parser = ArgParser(description='Configure capture on UUTs')

    parser.add_argument('--pre', default=0, type=ArgTypes.int_with_unit, help='Pre samples')
    parser.add_argument('--post', default=0, type=ArgTypes.int_with_unit, help='Post samples')
    parser.add_argument('--trigger', default='0,0,0', type=ArgTypes.signal_triplet, help='Capture Trigger')
    parser.add_argument('--event0', default='0,0,0', type=ArgTypes.signal_triplet, help='Capture Event0')
    parser.add_argument('--event1', default='0,0,0', type=ArgTypes.signal_triplet, help='Capture Event1')
    parser.add_argument('--rgm', default='0,0,0', type=ArgTypes.rgm_triplet, help='RGM triplet')
    parser.add_argument('--translen', default=0, type=int, help='Translen value')
    parser.add_argument('--demux', action='store_true', help='Demux data')
    parser.add_argument('--stream_mask', default=None, type=ArgTypes.list_of_channels, help='Stream mask channels')
    parser.add_argument('--spad', default=None, type=ArgTypes.spad, help='Spad length')
    parser.add_argument('--sites', default=None, help='run0 sites (1,2,3 or ALL)')

    parser.add_argument('uutnames', nargs='+', help="uut hostnames")
    return parser

if __name__ == '__main__':
    main(get_parser().parse_args())