

from matplotlib import pyplot as plt



"""
Plot config file define figures and position and channel

Plot spad in subplot
Plot dio bits individually subplot
Find and plot event signautres subplot
    strip es out of data

max 8 subplots per figure?

spad no smoothing
"""

def plot_by_carrier(dataset, chans=(1), pses=(0, None, 1)):
    """Plot data by carrier"""
    start, end, stride = pses
    rows = len(dataset)
    fig, axs = plt.subplots(rows, 1, figsize=(15, max(4, 3 * rows)), sharex=True, squeeze=False, constrained_layout=True)

    for row, (uutname, dat) in enumerate(dataset.items()):
        ax = axs[row, 0]
        for chan in chans:
            chandat = dat.adc.get(int(chan))
            if chandat is None: continue
            length = len(chandat)
            plot_end = length if end is None or end < 0 else end
            plot_start = max(0, min(start, length))
            plot_end = max(plot_start, min(plot_end, length))
            x = range(plot_start, plot_end, stride)
            ax.plot(x, chandat[plot_start:plot_end:stride], label=f'CH{chan}')
        ax.set_title(uutname)
        ax.set_ylabel('codes')
        ax.legend()

    axs[-1, 0].set_xlabel('samples')
    plt.show()
    return fig

def plot_by_channel(): pass



def plot_from_config(): pass


def parser_pcfg(): pass


class Plotter:
    def __init__(self):
        self.figs = [
            {
                "source": 'filename',
                "subplots": {
                    'a': {}
                },
                "rows": [['a'],[]]
            }
        ]

