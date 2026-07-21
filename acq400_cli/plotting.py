#!/usr/bin/env python3
"""
Plotting code

"""
import logging
import numpy as np

from matplotlib import pyplot as plt
from dataclasses import dataclass, replace
from acq400_cli.constants import PLOT_TRACE_COLORS, POWER_MW_SCALE
from acq400_cli.parser import ArgTypes

@dataclass
class FigSpec:
    figure: int                 #  `-1` auto figure or set explicitly `0,1` (default `-1`)
    row: int                    #  row within the figure, `-1` auto-increments (default `-1`)
    chan: list | None           #  channels to plot, comma list and/or ranges (`1,3,5-8`)
    spad: list | None           #  SPAD channels to plot
    view: str                   #  Y-axis data type, `RAW`, `VOLTS` or `POWER` (default `RAW`)
    source: list                #  source indexes to read from, comma list (`0,1`) or `-1` for all (default `-1`)

    bitmask: int | None         #  hex bit mask
    bitslice: int | None        #  hex bit mask; each set bit is plotted as its own trace
    mask: list | None           #  sample indexes and/or ranges to exclude

    title: str | None           #  subplot row title
    label: str | None           #  legend label format string
    legend: bool                #  show legend on the row, `true`/`false` (default `true`)
    figure_title: str | None    #  figure suptitle (first line wins)
    drawstyle: str              #  draw style (`default`, `steps`, `steps-pre`, `steps-mid`, `steps-post`)
    linestyle: str              #  line style (`-`, `--`, `:`, `-.`)


    @classmethod
    def from_spec(cls, spec):
        chan = spec.get("chan", None)
        if chan and not isinstance(chan, list):
            chan = ArgTypes.list_of_channels(chan)

        spad = spec.get("spad", None)
        if spad and not isinstance(spad, list):
            spad = ArgTypes.list_of_channels(spad)

        return cls(
            figure=int(spec.get("figure", -1)),
            row=int(spec.get("row", -1)),
            chan=chan,
            spad=spad,
            view=spec.get("view", "RAW"),
            source=ArgTypes.list_of_ints_comma(spec.get("source", -1)),

            bitmask=ArgTypes.hexstring(spec['bitmask']) if spec.get("bitmask", None) else None,
            bitslice=ArgTypes.hexstring(spec['bitslice']) if spec.get("bitslice", None) else None,
            mask=ArgTypes.sample_indexes(spec['mask']) if spec.get("mask", None) else None,

            title=spec.get("title", None),
            label=spec.get("label", None),
            legend=ArgTypes.bool_string(spec.get("legend"), True),
            figure_title=spec.get("figure_title", None),
            drawstyle=spec.get("drawstyle",'default'),
            linestyle=spec.get("linestyle", '-')
        )

    @classmethod
    def resolve_relative(cls, specs, max_rows=4):
        """Convert relative values to absolute"""
        current_figure = 0
        current_rows = {}
        resolved = []
        for spec in specs:
            if spec.figure > -1:
                current_figure = spec.figure

            last_row, auto_count = current_rows.get(current_figure, (-1, 0))

            if spec.row > -1:
                row = spec.row
                current_rows[current_figure] = (row, auto_count)
            else:
                if auto_count >= max_rows and spec.figure <= -1:
                    current_figure += 1
                    last_row, auto_count = current_rows.get(current_figure, (-1, 0))
                row = last_row + 1
                if row >= max_rows and spec.figure <= -1:
                    current_figure += 1
                    last_row, auto_count = current_rows.get(current_figure, (-1, 0))
                    row = last_row + 1
                current_rows[current_figure] = (row, auto_count + 1)

            resolved.append(replace(spec, figure=current_figure, row=row))
        return resolved


class PCFG:

    def __init__(self, filepath):
        print(filepath)
        self.specs = []
        with open(filepath, 'r') as fp:
            if filepath.endswoth('pcfg2'):
                self.import_pcfg2(fp)
                #TODO
            if filepath.endswoth('pcfg'):
                self.import_pcfg(fp)
        


    @staticmethod
    def import_pcfg2(filepath):
        """import pcfg2 file and return specs"""
        fig_specs = []
        with open(filepath, 'r') as fp:
            for lno, line in enumerate(fp):
                line = line.strip()
                if not line or line.startswith("#"): continue
                try:
                    spec = FigSpec.from_spec(dict(item.split('=', 1) for item in line.rstrip(';').split(';')))
                    fig_specs.append(spec)
                except Exception as e:
                    print(e)
                    logging.warning(f"{filepath}:{lno} line invalid skipping")
                    continue
        return fig_specs

    @staticmethod
    def import_pcfg(filepath):
        print("TODO")


class Plotter:
    def __init__(
        self,
        specs,
        sources,
        pses=(0, None, 1),
        units='SAMPLES',
        max_scale=10,
        sample_rate=None,
        max_samples=100_000,
        fig_width=10,
        row_height=2,
    ):
        self.figs = {}

        self.sources = sources
        self.pses = self.__clamp_pses(pses, max_samples)
        self.units = units.upper()
        self.max_scale = max_scale
        self.sample_rate = sample_rate

        self.fig_width=fig_width
        self.row_height=row_height

        self.footer = self.__gen_footer(specs)
        self.timebase = self.__gen_timebase(self.units, sources)
        self.max_rows = self.__calc_max_rows(specs)
        self.__plot_specs(specs)

    def show(self):
        """Show built plot"""
        plt.show()

    def __calc_max_rows(self, specs):
        """Read specs and calc max rows foreach figure"""
        max_rows = {}
        for spec in specs:
            max_rows[spec.figure] = max(max_rows.get(spec.figure, 0), spec.row + 1)
        return max_rows

    def __clamp_pses(self, pses, max_samples):
        """Limit pses to max_samples """
        start, end, stride = pses
        stride = max(1, stride)
        if end is not None and len(range(start, end, stride)) <= max_samples:
            return pses
        return (start, start + max_samples * stride, stride)

    def __calc_range(self, length):
        """Calc range from pses and length"""
        start, end, stride = self.pses
        plot_start = max(0, min(start, length))
        plot_end = length if end is None or end < 0 else end
        plot_end = max(plot_start, min(plot_end, length))
        return np.arange(plot_start, plot_end, stride)

    def __gen_timebase(self, units, sources):
        """Generate timebase for sources"""
        timebase = []
        if units == 'SECONDS':
            if not self.sample_rate and all(source.sample_rate is None for source in sources):
                self.units = units = 'SAMPLES'
                logging.warning('Unknown sample rate defaulting to SAMPLES')

        for source in sources:
            rate = source.sample_rate or self.sample_rate
            length = len(source)
            if units == 'SAMPLES':
                timebase.append(np.arange(length))
            elif units == 'SECONDS':
                timebase.append(np.arange(length) / rate)
        return timebase

    def __sample_mask(self, length, mask):
        """Return bool array: True = keep sample"""
        mask_arr = np.ones(length, dtype=bool)
        for item in mask:
            if isinstance(item, tuple):
                mstart, mend, mstride = item
                if mend is None or mend < 0:
                    mend = length
                mask_arr[mstart:mend:mstride] = False
            else:
                mask_arr[item] = False
        return mask_arr

    def __get_figure(self, figure):
        """Create figure if needed then return"""
        if figure in self.figs: return self.figs[figure]
        rows = self.max_rows[figure]

        fig, axs = plt.subplots(
            rows, 1,
            figsize=(self.fig_width, max(4, self.row_height * rows)),
            sharex=True,
            squeeze=False,
        )

        for ax in axs.flat:
            ax.set_prop_cycle(color=PLOT_TRACE_COLORS)

        self.figs[figure] = (fig, axs)
        return self.figs[figure]

    def __get_row(self, figure, row):
        """Return fig and row"""
        fig, axs = self.__get_figure(figure)
        return fig, axs[row, 0]

    def __get_source(self, indexes):
        """Return source arrays"""
        if -1 in indexes: indexes = list(range(len(self.sources)))
        return {idx: self.sources[idx] for idx in indexes if 0 <= idx < len(self.sources)}

    def __set_xlabel(self):
        """Set xlabel"""
        for fig, axs in self.figs.values():
            axs[-1, 0].set_xlabel(self.units.title())

    def __enable_legend(self, loc="upper right"):
        """Enable legends on all axs"""
        for fig, axs in self.figs.values():
            for ax in axs:
                ax[0].legend(loc=loc)

    def __gen_label(self, label_fmt, spec, index, chan, bit=None):
        """Return formatted label"""
        label_fmt = label_fmt if spec.legend else '__nolabel__'
        label_fmt = spec.label if spec.label else label_fmt
        if len(self.footer[spec.figure]) > 1: label_fmt = f"[{index}] {label_fmt}"
        return label_fmt.format(chan=chan, bit=bit)

    def __plot_data(self, row, x, y, label_fmt, index, chan, spec):
        """Plot channel to row"""
        drawstyle = spec.drawstyle if spec.drawstyle else 'default'
        linestyle = spec.linestyle if spec.linestyle else '-'

        start, end, stride = self.pses
        y = y[start:end:stride]
        x = x[start:end:stride]

        if spec.bitslice:
            label_fmt = f"{label_fmt} d{{bit}}"
            for bit in range(y.dtype.itemsize * 8):
                if spec.bitslice & (1 << bit):
                    label = self.__gen_label(label_fmt, spec, index, chan, bit)
                    row.plot(x, (y >> bit) & 1, label=label, drawstyle=drawstyle, linestyle=linestyle)
        else:
            if spec.bitmask:
                y = y & spec.bitmask
            label = self.__gen_label(label_fmt, spec, index, chan)
            row.plot(x, y, label=label, drawstyle=drawstyle, linestyle=linestyle)

    def __gen_footer(self, specs):
        """gen map of figures to sources for footer"""
        footer = {}
        for spec in specs:
            footer.setdefault(spec.figure, set())
            if -1 in spec.source: 
                footer[spec.figure].update(range(len(self.sources)))
                continue
            for index in spec.source:
                footer[spec.figure].add(index)
        return footer

    def __add_footer(self):
        """Add footers to bottom of figures"""
        for figure, sources in self.footer.items():
            fig = self.figs[figure][0]
            footer = []
            for index in sources:
                prefix = f"[{index}] " if len(sources) > 1 else ''
                source = self.sources[index].filepath
                footer.append('{prefix}{source}'.format(prefix=prefix, source=source))
            footer.insert(0, f"pses = {self.pses}")
       
            
            padding = min(0.4, 0.03 + len(footer) * 0.012)
            fig.tight_layout(rect=[0, padding, 1, 1])
            fig.text(
                0.01, padding * 0.5,
                "\n".join(footer),
                ha="left",
                va="bottom",
                fontsize=8,
            )

    def __gen_title(self):
        """Auto generate the title if none set"""
        for figure, (fig, axs) in self.figs.items():
            if fig.get_suptitle(): continue
            title = []
            parts = {}
            for index in self.footer[figure]:
                for key, value in self.sources[index].params.items():
                    parts.setdefault(key, set()).add(value)

            for key, value in parts.items():
                if key == 'hostname': continue
                if len(value) == 1:
                    parts[key].clear()
                    parts[key].add(None)

            keys = list(parts.keys())
            for values in product(*parts.values()):
                combo = dict(zip(keys, values))
                title_text = []
                if combo['hostname']:
                    title_text.append(combo['hostname'])
                if combo['timestamp']:
                    title_text.append(combo['timestamp'])
                if combo['format']:
                    title_text.append(combo['format']) 
                title.append(' '.join(title_text))
            fig.suptitle(' - '.join(title))

    def __plot_specs(self, specs):
        """Plot each spec"""
        for spec in specs:

            fig, row = self.__get_row(spec.figure, spec.row) 

            if spec.figure_title and not fig.get_suptitle():
                fig.suptitle(spec.figure_title)

            if spec.title and not row.get_title():
                row.set_title(spec.title)

            for index, source in self.__get_source(spec.source).items():

                x = self.timebase[index]

                if not row.get_ylabel():
                    if spec.view == 'VOLTS':
                        y_label = 'Volts (V)'
                    elif spec.view == 'POWER':
                        y_label = 'Power (mW)'
                    else:
                        y_label = 'Codes'
                    row.set_ylabel(y_label)

                if spec.mask:
                    mask = self.__sample_mask(len(source), spec.mask)
                    x = x[:int(mask.sum())] 

                if spec.chan is not None:
                    for chan in spec.chan:
                        logging.info(f"Plot CH{int(chan):03} from source[{index}] to figure[{spec.figure}] row[{spec.row}]")
                   
                        label_fmt = 'CH{chan}'
                        y = source.channels.get(int(chan))
                        if spec.view == 'VOLTS':
                            y = source.chan2volts(int(chan))
                        elif spec.view == 'POWER':
                            y = y * POWER_MW_SCALE
                        if spec.mask is not None: y = y[mask]

                        self.__plot_data(row, x, y, label_fmt, index, chan, spec)

                if spec.spad is not None:
                    for spad in spec.spad:
                        logging.info(f"Plot SPD{int(spad):02} from source[{index}] to figure[{spec.figure}] row[{spec.row}]")

                        label_fmt = 'SPD{chan}'
                        y = source.spd.get(int(spad))
                        if y is None: continue
                        if spec.mask is not None: y = y[mask]

                        self.__plot_data(row, x, y, label_fmt, index, spad, spec)

        self.__gen_title()
        self.__add_footer()
        self.__set_xlabel()
        self.__enable_legend()
