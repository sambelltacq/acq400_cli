#!/usr/bin/env python3

"""
Stream data from UUTs to host

Usage:
    acq400_cli stream_to_host --stream_mask=1-4,33 --filesamples=1000000 --overwrite --hexdump acq2106_054
"""

import argparse
from acq400_cli import ArgTypes, Collection, SignalGenerator, StreamClient

def main(args):
    uuts = Collection(args.uutnames)

    siggen = SignalGenerator(args.siggen) if args.siggen else None

    uuts.abort_capture()

    print(f"Configuring {uuts.names}")
    uuts.configure_capture(
        trigger=args.trigger,
        rgm=args.rgm,
        translen=args.translen,
        stream_mask=args.stream_mask
    )

    print(f"Setup Host {uuts.names}")
    stream = StreamClient(
        uuts,
        savedir=args.savedir,
        filebytes=args.filebytes,
        filesamples=args.filesamples,
        overwrite=args.overwrite,
        hexdump=args.hexdump,
        save=True,
    )

    print(f"Start stream {uuts.names}")
    stream.start(
        seconds=args.seconds,
        samples=args.samples,
        bytes=args.bytes
    )

    stream.trigger_when_armed(trigger=args.trigger, siggen=siggen)

    stream.print_status()


def get_parser():
    parser = argparse.ArgumentParser(description='Stream data from UUTs to host')

    parser.add_argument('--trigger', default='1,1,1', type=ArgTypes.trigger, help='Capture Trigger')
    parser.add_argument('--rgm', default='0,0,0', type=ArgTypes.triplet, help='RGM triplet')
    parser.add_argument('--translen', default=0, type=ArgTypes.int_with_unit, help='Translen value')
    parser.add_argument('--stream_mask', default=None, type=ArgTypes.list_of_channels, help='Stream mask channels')

    parser.add_argument('--seconds', default=10, type=int, help='Total seconds to stream')
    parser.add_argument('--bytes', default=None, type=ArgTypes.int_with_unit, help='Total bytes to stream')
    parser.add_argument('--samples', default=None, type=int, help='Total samples to stream')

    parser.add_argument('--filebytes', default=None, type=ArgTypes.int_with_unit, help='Max filesize in bytes')
    parser.add_argument('--filesamples', default=None, type=int, help='Max filesize in samples')

    parser.add_argument('--savedir', default="DATA", help='Save dir')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite datafiles')

    parser.add_argument('--siggen', default=None, type=int, help='Siggen hostname to EXT trigger')
    parser.add_argument('--hexdump', action='store_true', help='Print hexdump command')
    
    parser.add_argument('uutnames', nargs='+', help="uut hostnames")
    return parser

if __name__ == '__main__':
    main(get_parser().parse_args())
