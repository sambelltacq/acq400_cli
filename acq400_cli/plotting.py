

from matplotlib import pyplot as plt


"""
thinking about plotting


by channel every channel gets its own subplot

by carrier ecvery uut gets its own subplot

only plot data channels not DIO

plot spad in seprate subplots
"""


def plot_by_carrier(dataset, chans=(1, 2, 3)):
    """Plot data by carrier"""
    rows = len(dataset)
    fig, axs = plt.subplots(rows, 1, figsize=(15, max(4, 3 * rows)), sharex=True, squeeze=False, constrained_layout=True)

    for row, (uutname, dat) in enumerate(dataset.items()):
        ax = axs[row, 0]
        for chan in chans:
            chandat = dat.adc.get(int(chan))
            if chandat is None: continue
            ax.plot(chandat, label=f'CH{chan}')
        ax.set_title(uutname)
        ax.set_ylabel('codes')
        ax.legend()

    axs[-1, 0].set_xlabel('samples')
    plt.show()
    return fig
