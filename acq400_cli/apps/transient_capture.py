#!/usr/bin/env python3

"""
Capture transient data on UUTs
"""

import argparse
import os
from acq400_cli import ArgTypes, Collection, SignalGenerator, generate_timestamp, plot_by_carrier

def main(args):
    
    uuts = Collection(args.uutnames)

    if args.siggen: siggen = SignalGenerator(args.siggen)

    uuts.abort_capture()

    print('Configuring capture')
    uuts.configure_capture(
        pre=args.pre,
        post=args.post,
        trigger=args.trigger,
        event0=args.event0,
        rgm=args.rgm,
        translen=args.translen,
    )

    print('Arming')
    uuts.arm_transient()
    uuts.wait_for_arm()
    print('Armed')

    if args.trigger.line == 1: uuts.trigger_soft_trigger()
    elif siggen: siggen.trigger()

    uuts.wait_for_idle()
    print("Complete")

    print('Reading data')
    data = uuts.read_transient_data()
    timestamp = None if args.overwrite else generate_timestamp()

    for uutname, dat in data.items():
        filename = uuts[uutname].data_filename(dat.sample_format, timestamp)
        filepath = os.path.join(args.savedir, filename)
        print(f"Saving {uutname} data to {filepath}")
        dat.save_to_file(filepath)
        if args.hexdump: print(f"Hexdump: {dat.sample_format.hexdump} {filepath}")

    if args.pchans:
        print('Plotting')
        plot_by_carrier(data, args.pchans)


def get_parser():
    parser = argparse.ArgumentParser(description='Capture transient data on UUTs')

    parser.add_argument('--pre', default=0, type=ArgTypes.int_with_unit, help='Pre samples')
    parser.add_argument('--post', default=100000, type=ArgTypes.int_with_unit, help='Post samples')
    parser.add_argument('--trigger', default='1,1,1', type=ArgTypes.trigger, help='Capture Trigger')
    parser.add_argument('--event0', default='0,0,0', type=ArgTypes.triplet, help='Capture Event0')
    parser.add_argument('--rgm', default='0,0,0', type=ArgTypes.triplet, help='RGM triplet')
    parser.add_argument('--translen', default=0, type=int, help='Translen value')

    parser.add_argument('--siggen', default=None, type=int, help='Siggen hostname to EXT trigger')

    parser.add_argument('--savedir', default="DATA", help='Save dir')
    parser.add_argument('--pchans', default=None, type=ArgTypes.list_of_channels, help='Channels to plot')

    parser.add_argument('--hexdump', action='store_true', help='Print hexdump command')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite data file')
    
    parser.add_argument('uutnames', nargs='+', help="uut hostnames")
    return parser

if __name__ == '__main__':
    main(get_parser().parse_args())