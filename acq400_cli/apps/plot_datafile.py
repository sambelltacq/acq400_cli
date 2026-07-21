#!/usr/bin/env python3

"""
Plot datafiles
"""

from acq400_cli import ArgTypes, ArgParser
from acq400_cli.data import UUTData
from acq400_cli.plotting import FigSpec, Plotter, PCFG

def main(args):

    sources = [UUTData.from_file(filename, format=args.format) for filename in args.filenames]
    view = 'VOLTS' if args.egu else 'RAW'
    units = 'SECONDS' if args.secs else 'SAMPLES'

    if args.pcfg:
        specs = PCFG.import_pcfg2(args.pcfg)
    else:
        specs = []

        if args.plot_by == 'channel':
            for chan in args.chan:
                specs.append(FigSpec.from_spec({
                    'chan': [chan],
                    'view': view,
                    'mask': args.mask,
                }))

            for spad in args.spad:
                specs.append(FigSpec.from_spec({
                    'spad': [spad],
                    'mask': args.mask,
                }))

        if args.plot_by == 'source':
            for index in range(len(sources)):
                specs.append(FigSpec.from_spec({
                    'chan': args.chan,
                    'source': index,
                    'figure': index,
                    'view': view,
                    'mask': args.mask,
                }))

                if args.spad:
                    specs.append(FigSpec.from_spec({
                        'spad': args.spad,
                        'source': index,
                        'figure': index,
                        'mask': args.mask,
                    }))

    specs = FigSpec.resolve_relative(specs, max_rows=args.max_rows)

    plt = Plotter(
        specs=specs,
        sources=sources,
        pses=args.pses,
        units=units,
        sample_rate=args.rate,
        max_samples=args.max_samples,
        sharey=args.sharey,
    )
    plt.show()



def get_parser():
    parser = ArgParser(description='Plot datafiles')
    parser.add_argument('--max_samples', default=100000, type=ArgTypes.int_with_unit, help='Max samples to load into memory')
    parser.add_argument('--max_rows', default=4, type=int, help='Max rows per figure')

    parser.add_argument('--egu', action='store_true', help='Plot y axis in volts')
    parser.add_argument('--scale', default=None, type=int, help='Set max scale for EGU without calibration')

    parser.add_argument('--secs', action='store_true', help='Plot X axis in seconds')
    parser.add_argument('--rate', '--clock', default=None, type=ArgTypes.int_with_unit, help='Set sample rate for SECS without calibration')

    parser.add_argument('--pses', default=(0, None, 1), type=ArgTypes.start_end_stride, help='Plot start:end:stride')
    parser.add_argument('--mask', default=None, help='Mask samples')

    parser.add_argument('--chan', '--chans', default=[1], type=ArgTypes.list_of_channels, help='Channels to plot')
    parser.add_argument('--spad', default=[], type=ArgTypes.list_of_channels, help='Spad Channels to plot')

    parser.add_argument('--plot_by', default='channel', choices=['source', 'channel'], help='Plot by source or by channel')

    parser.add_argument('--format', default=None, help='Set format fallback if file lacks tag')

    parser.add_argument('--sharey', action='store_true', help='Rows share y axis scale')

    parser.add_argument('--pcfg', default=None, help='Plot config file')

    parser.add_argument('filenames', nargs='+', type=ArgTypes.filepath, help='data filenames')
    return parser

if __name__ == '__main__':
    main(get_parser().parse_args())