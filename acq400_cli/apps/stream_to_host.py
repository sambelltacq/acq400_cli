#!/usr/bin/env python3

"""
Stream data from UUTs to host

Usage:
    acq400_cli stream_to_host --stream_mask=1-4,33 --filesamples=1000000 --overwrite --hexdump acq2106_054
"""

from acq400_cli import ArgTypes, Collection, ArgParser, generate_timestamp, PORTS
from acq400_cli.data import StreamDataFile
import logging
import time

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

    timestamp = generate_timestamp() if args.timestamp else None
    stream_tasks = {}

    print(f"Start stream tasks: {uuts.names}")
    for uut in uuts:
        if not uut.stream_enabled:
            logging.error(f"Streaming not enabled on {uut.hostname}")
            continue

        sample_format = uut.stream_sample_format

        filebytes = None
        if args.filebytes:
            filebytes = args.filebytes
            logging.info(f"{uut.addr} Max filesize {filebytes} Bytes")
        if args.filesamples:
            filebytes = sample_format.bytes * args.filesamples
            logging.info(f"{uut.addr} samples {args.filesamples} Max filesize {filebytes} Bytes")
        elif args.filebursts:
            rtm_translen = uut.rtm_translen
            filebytes = sample_format.bytes * uut.rtm_translen
            logging.info(f"{uut.addr} rtm_translen: {rtm_translen} Max filesize {filebytes} Bytes")

        if args.samples:
            target_bytes = sample_format.bytes * args.samples
        elif args.bytes:
            target_bytes = args.bytes
        else:
            target_bytes = int(args.seconds * sample_format.bytes * uut.sample_rate)

        datafile = None
        if args.save:
            datafile = StreamDataFile(
                args.savedir,
                filesize=filebytes,
                sample_size=sample_format.bytes,
                hostname=uut.hostname,
                format=sample_format.tag,
                timestamp=timestamp,
                max_files=args.max_files,
            )

        stream_tasks[uut.hostname] = uut.bg.stream_to_host(target_bytes, PORTS.STREAM, sample_format, datafile)

    if not stream_tasks: return
    
    for uutname, task in stream_tasks.items(): uuts[uutname].print_stream_status(task.thread.status)
    print("Waiting for ARM")
    uuts.wait_for_arm()
    print('Armed')

    uuts.trigger_line(siggen=args.siggen, line=args.trigger.line)

    try:
        while not all(task.finished for task in stream_tasks.values()):
            for uutname, task in stream_tasks.items():
                uuts[uutname].print_stream_status(task.thread.status)
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupt")
        for task in stream_tasks.values():
            task.stop()

    for uutname, task in stream_tasks.items():
        savepath = task.join()
        if savepath:
            uuts[uutname].save_metadata(savepath.with_suffix('.meta'))
            if args.hexdump:
                print(f"{uuts[uutname].stream_sample_format.hexdump} {savepath}")


def get_parser():
    parser = ArgParser(description='Stream data from UUTs to host')

    parser.add_argument('--trigger', default='AUTO,RISING', type=ArgTypes.signal_triplet, help='Capture Trigger')
    parser.add_argument('--rgm', default='OFF', type=ArgTypes.rgm_triplet, help='RGM triplet')
    parser.add_argument('--translen', default=0, type=ArgTypes.int_with_unit, help='Translen value')
    parser.add_argument('--stream_mask', default=None, type=ArgTypes.list_of_channels, help='Stream mask channels')

    parser.add_argument('--seconds','--secs', default=10, type=int, help='Total seconds to stream')
    parser.add_argument('--bytes', default=None, type=ArgTypes.int_with_unit, help='Total bytes to stream')
    parser.add_argument('--samples', default=None, type=ArgTypes.int_with_unit, help='Total samples to stream')

    parser.add_argument('--filebytes', default=None, type=ArgTypes.int_with_unit, help='Limit max filesize in bytes')
    parser.add_argument('--filesamples', default=None, type=ArgTypes.int_with_unit, help='Limit max filesize in samples')
    parser.add_argument('--filebursts', action='store_true', help='Limit max filesize to rtm_translen')
    parser.add_argument('--max_files', default=1000, type=int, help='Set max files before overwriting')

    parser.add_argument('--savedir', default="DATA", help='Save dir')
    parser.add_argument('--save', default=True, action='store_true', help='Save stream to file')
    parser.add_argument('--timestamp', action='store_true', help='Timestamp datafiles')

    parser.add_argument('--siggen', default=None, type=ArgTypes.siggen, help='Siggen hostname to external trigger')
    parser.add_argument('--hexdump', action='store_true', help='Print hexdump command')
    
    parser.add_argument('uutnames', nargs='+', help="uut hostnames")
    return parser

if __name__ == '__main__':
    main(get_parser().parse_args())
