#!/usr/bin/env python3

"""
Capture transient data on UUTs
"""

import os
from acq400_cli import ArgTypes, Collection, ArgParser, generate_timestamp

def main(args):
    uuts = Collection(args.uutnames)

    uuts.abort_capture()

    print(f"Configuring capture {uuts.names}")
    uuts.configure_capture(
        pre=args.pre,
        post=args.post,
        trigger=args.trigger,
        event0=args.event0,
        rgm=args.rgm,
        translen=args.translen,
    )

    uuts.print_status()

    uuts.arm_transient()
    print('Arming')

    uuts.wait_for_arm()
    print('Armed')

    uuts.trigger_capture(args.siggen, args.trigger.line)

    if args.pre > 0:
        print(f"Wait for {args.pre} samples")
        uuts.wait_for_nsamples(args.pre)
        uuts.trigger_capture(args.siggen, args.event0.line)

    uuts.wait_for_idle()
    print("Complete")

    print('Reading data')
    data = uuts.read_transient_data()

    timestamp = generate_timestamp() if args.timestamp else None

    for uutname, dat in data.items():
        savepath = uuts[uutname].savepath(
            sample_format=dat.sample_format.tag,
            timestamp=timestamp,
            savedir=args.savedir,
        )

        print(f"Saving {uutname} data to {savepath}")
        dat.save_to_file(savepath)
        uuts[uutname].save_metadata(savepath.with_suffix('.meta'))
        
        if args.hexdump: print(f"Hexdump: {dat.sample_format.hexdump} {savepath}")


def get_parser():
    parser = ArgParser(description='Capture transient data on UUTs')

    parser.add_argument('--pre', default=0, type=ArgTypes.int_with_unit, help='Pre samples')
    parser.add_argument('--post', default=100000, type=ArgTypes.int_with_unit, help='Post samples')
    parser.add_argument('--trigger', default='1,1,1', type=ArgTypes.signal_triplet, help='Capture Trigger')
    parser.add_argument('--event0', default='0,0,0', type=ArgTypes.signal_triplet, help='Capture Event0')
    parser.add_argument('--rgm', default='0,0,0', type=ArgTypes.rgm_triplet, help='RGM triplet')
    parser.add_argument('--translen', default=0, type=int, help='Translen value')

    parser.add_argument('--siggen', default=None, type=ArgTypes.siggen, help='Siggen hostname to EXT trigger')

    parser.add_argument('--savedir', default="DATA", help='Save dir')

    parser.add_argument('--hexdump', action='store_true', help='Print hexdump command')
    parser.add_argument('--timestamp', action='store_true', help='Timestamp data file')
    
    parser.add_argument('uutnames', nargs='+', help="uut hostnames")
    return parser

if __name__ == '__main__':
    main(get_parser().parse_args())