#!/usr/bin/env python3

"""
Plot 
"""

import os
from acq400_cli import ArgTypes, SigGen, ArgParser, plot_by_carrier, parse_filename_parts
from acq400_cli.data import UUTData

def main(args):
    
    for filename in args.filenames:

        parts = parse_filename_parts(filename)
        #TODO: if egu get calibration from UUT
        #TODO: if secs and not rate read clock from UUT
        data = UUTData.from_file(filename, max_samples=args.max_samples)
        print(data)
        uutname = parts.hostname or os.path.basename(filename)
        plot_by_carrier({uutname: data}, chans=args.chans, pses=args.pses)








def get_parser():
    parser = ArgParser(description='Demux datafiles into channels')
    parser.add_argument('--tofile', action='store_true', help='Save plot to file')
    parser.add_argument('--savedir', default='PLOTS', help='Dir to save plot to')

    parser.add_argument('--max_samples', default=None, help='Max samples to load into memory')

    #parser.add_argument('--pspad', default=None, type=ArgTypes.list_of_channels, help='Plot spad Channels (1,2)')

    parser.add_argument('--egu', action='store_true', help='Plot y axis in volts')
    #parser.add_argument('--scale', default=10, type=int, help='Max volts for egu')
    parser.add_argument('--secs', action='store_true', help='Plot X axis in seconds')
    parser.add_argument('--rate', default=1000000, type=ArgTypes.int_with_unit, help='Sample rate')

    parser.add_argument('--pses', default=(0, None, 1), type=ArgTypes.start_end_stride, help='Plot start:end:stride')
    parser.add_argument('--chans', default=[1], type=ArgTypes.list_of_channels, help='Channels to plot')# pchans?

    parser.add_argument('--plot_carrier', action='store_true', help='Plot by carrier or file')
    parser.add_argument('--plot_channel', action='store_true', help='Plot by channel')

    parser.add_argument('--pcfg', default=None, help='Plot config file')


    parser.add_argument('filenames', nargs='+', help='data filenames')
    return parser

if __name__ == '__main__':
    main(get_parser().parse_args())