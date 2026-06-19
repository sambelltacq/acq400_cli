#!/usr/bin/env python3

"""
Stream data from UUTs to host

Usage:
    acq400_cli stream_to_host --stream_mask=1-4,33 --filesamples=1000000 --overwrite --hexdump acq2106_054
"""

from acq400_cli import ArgTypes, Collection, StreamClient, ArgParser

def main(args):
    uuts = Collection(args.uutnames)

    uuts.abort_capture()

    print(f"Configuring {uuts.names}")
    uuts.configure_capture(
        trigger=args.trigger,
        rgm=args.rgm,
        translen=args.translen,
        stream_mask=args.stream_mask
    )

    print(f"Init Stream {uuts.names}")
    stream = StreamClient(
        uuts,
        savedir=args.savedir,
        filebytes=args.filebytes,
        filesamples=args.filesamples,
        timestamp=args.timestamp,
        hexdump=args.hexdump,
        save=True,
    )

    print(f"Start stream {uuts.names}")
    stream.start(
        seconds=args.seconds,
        samples=args.samples,
        bytes=args.bytes
    )

    uuts.wait_for_arm()
    print('Armed')

    stream.print_status()

    uuts.trigger_capture(siggen=args.siggen, line=args.trigger.line)

    uuts.wait_for_idle()

    [thread.join() for thread in stream.streams.values()]


def get_parser():
    parser = ArgParser(description='Stream data from UUTs to host')

    parser.add_argument('--trigger', default='1,1,1', type=ArgTypes.signal_triplet, help='Capture Trigger')
    parser.add_argument('--rgm', default='0,0,0', type=ArgTypes.rgm_triplet, help='RGM triplet')
    parser.add_argument('--translen', default=0, type=ArgTypes.int_with_unit, help='Translen value')
    parser.add_argument('--stream_mask', default=None, type=ArgTypes.list_of_channels, help='Stream mask channels')

    parser.add_argument('--seconds', default=10, type=int, help='Total seconds to stream')
    parser.add_argument('--bytes', default=None, type=ArgTypes.int_with_unit, help='Total bytes to stream')
    parser.add_argument('--samples', default=None, type=ArgTypes.int_with_unit, help='Total samples to stream')

    parser.add_argument('--filebytes', default=None, type=ArgTypes.int_with_unit, help='Max filesize in bytes')
    parser.add_argument('--filesamples', default=None, type=ArgTypes.int_with_unit, help='Max filesize in samples')

    parser.add_argument('--savedir', default="DATA", help='Save dir')
    parser.add_argument('--timestamp', action='store_true', help='Timestamp datafiles')

    parser.add_argument('--siggen', default=None, type=ArgTypes.siggen, help='Siggen hostname to EXT trigger')
    parser.add_argument('--hexdump', action='store_true', help='Print hexdump command')
    
    parser.add_argument('uutnames', nargs='+', help="uut hostnames")
    return parser

if __name__ == '__main__':
    main(get_parser().parse_args())
