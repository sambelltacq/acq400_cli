#!/usr/bin/env python3

"""
Generate waveform datafile from wdef file
"""

from acq400_cli import ArgParser, ArgTypes
from acq400_cli.waveform import WDEF, Waveform
from matplotlib import pyplot as plt
from pathlib import Path
import os

def main(args):
    print(f"Reading wavedef from {args.wavedef}")
    specs = WDEF.from_file(args.wavedef)
    waveform = Waveform(args.length, args.nchan, args.data_size, specs)

    if args.save:
        label = args.label if args.label else Path(args.wavedef).stem
        filename = f"{label}.{waveform.sample_format.tag}.wdat"
        os.makedirs(args.root, exist_ok=True)
        savepath = os.path.join(args.root, filename)
        print(f"Waveform saved to {savepath}")
        waveform.save_to_file(savepath)

    if not args.no_plot:
        for chan in waveform.sample_format.channels:
            plt.plot(waveform[f"{chan}"], label=f"CH{chan}")
        plt.legend(loc="upper right")
        plt.show()

def get_parser():
    parser = ArgParser(description='Generate waveform bin file from wdef file')
    parser.add_argument('--nchan', required=True, type=int, help='Total Channels')
    parser.add_argument('--length', required=True, type=ArgTypes.int_with_unit, help='Channel length in samples')
    parser.add_argument('--data_size', required=True, type=ArgTypes.int_with_unit, help='Channel size in bytes')
    parser.add_argument('--wavedef', required=True, default=None, type=ArgTypes.filepath, help="Waveform def file")
    parser.add_argument('--save', action='store_true', help="Save waveform")
    parser.add_argument('--label', default=None, type=str, help="Label for saved waveform")
    parser.add_argument('--root', default="WAVEFORMS", type=str, help="Waveform save root dir")
    parser.add_argument('--no_plot', action='store_true', help="Don't plot waveform")
    return parser

if __name__ == '__main__':
    main(get_parser().parse_args())