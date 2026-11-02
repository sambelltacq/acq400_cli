# acq400_cli

- Command Line Interface for acq400 UUTs

## Installation

```
git clone https://github.com/D-TACQ/acq400_cli
cd acq400_cli
pip3 install -e .
```

## Subcommands

After install, run subcommands as `acq400_cli <subcommand> …`.

| Subcommand | Description |
|-----|-------------|
| [abort_capture](#abort_capture) | Abort capture on UUTs |
| [configure_capture](#configure_capture) | Configure capture (sites, spad, trigger, RGM) |
| [configure_clock](#configure_clock) | Configure sync role / clock |
| [demux_data](#demux_data) | Demux muxed datafiles into seperate channels |
| [generate_hexdump](#generate_hexdump) | Generate hexdump commands for UUT data |
| [generate_waveform](#generate_waveform) | Build waveforms from `.wdef` or args |
| [load_gpg](#load_gpg) | Load GPG from an STL file |
| [plot_datafile](#plot_datafile) | Plot datafiles |
| [setup_hudp](#setup_hudp) | Configure Hardware UDP (HUDP) TX/RX |
| [stream_to_awg](#stream_to_awg) | Stream waveforms to AO continuously |
| [stream_to_host](#stream_to_host) | Stream capture data continuously to the host |
| [transient_capture](#transient_capture) | Arm and capture transient data to the host |
| [upload_waveform](#upload_waveform) | Upload waveform files to AO modules |
| [upload_waveform_segment](#upload_waveform_segment) | Upload waveforms into AWG segments |
| [wait_for_state](#wait_for_state) | Wait until UUTs reach a state |

## Usage

<a id="transient_capture"></a>
### Transient Capture

Capture transient data and save it to the host.

- **Post** - capture 100K samples on an external trigger:
```bash
acq400_cli transient_capture --post=100K --trigger=EXT,RISING <uutnames>
```

- **Pre + Post** - capture 50K pre 50K post sample on external event:
```bash
acq400_cli transient_capture --pre=50K --post=50K --trigger=SOFT,RISING --event=EXT,RISING <uutnames>
```

- **Burst** - capture 5000 sample bursts on each external event for 100K samples total:
```bash
acq400_cli transient_capture --post=100K --trigger=SOFT,RISING --rgm=RTM,RISING --translen=5000 <uutnames>
```


<a id="stream_to_host"></a>
### Continuous Stream

Stream data continuously to the host.

- **By time** - stream 10 seconds of data on an external trigger:
```bash
acq400_cli stream_to_host --trigger=EXT,RISING --seconds=10 <uutnames>
```

- **By samples** - stream 1M samples on an external trigger:
```bash
acq400_cli stream_to_host --trigger=EXT,RISING --samples=1M <uutnames>
```

- **By size** - stream 100MB on an external trigger:
```bash
acq400_cli stream_to_host --trigger=EXT,RISING --bytes=100MB <uutnames>
```

- **Filesamples Limit** - stream 10M samples on an external trigger, 1M samples per file:
```bash
acq400_cli stream_to_host --trigger=EXT,RISING --samples=10M --filesamples=1M <uutnames>
```

- **Filessize Limit** - stream 1M samples on an external trigger, 10MB Bytes per file:

```bash
acq400_cli stream_to_host --trigger=EXT,RISING --samples=1M --filebytes=10MB <uutnames>
```
Note: `--filebytes` will round up to the nearest whole sample.

<a id="configure_clock"></a>
### Configure Clocking

Configure UUTs sync role

- **run0** - Set enabled sites and spad size:
```bash
acq400_cli configure_clock --clk=1M <uutnames>
```


<a id="configure_capture"></a>
### Configure Capture

Configure UUTs capture.

- **Post** - Capture 100K samples on an external trigger:
```bash
acq400_cli configure_capture --trigger=EXT,RISING --post=100K <uutnames>
```

- **Pre + Post** - Capture 50K pre 50K post samples on external event:
```bash
acq400_cli configure_capture --pre=50K --post=50K --trigger=AUTO,RISING --event0=EXT,RISING <uutnames>
```

- **RTM Stream** - Stream 5000 sample bursts on external trigger:
```bash
acq400_cli configure_capture --rgm=RTM,RISING --translen=5000 --trigger=AUTO,RISING <uutnames>
```

- **Stream** - Stream with mask on external trigger:
```bash
acq400_cli configure_capture --stream_mask=1-4 --trigger=EXT,RISING <uutnames>
```

- **run0** - Set enabled sites and spad size:
```bash
acq400_cli configure_capture --sites=1,2,3 --spad=8 <uutnames>
```

- **Spad ident** - Add markers into spad columns:
```bash
acq400_cli configure_capture --ident <uutnames>
```

- **Spad microsecond** - Add microsecond to spad[1]:
```bash
acq400_cli configure_capture --us <uutnames>
```

- **Disable event signature** - Disable ES in data:
```bash
acq400_cli configure_capture --no_es <uutnames>
```

<a id="abort_capture"></a>
### Abort Capture

Abort capture on UUTs.

```bash
acq400_cli abort_capture <uutnames>
```

<a id="wait_for_state"></a>
### Wait for State

Block until UUTs reach a capture state (`IDLE`, `ARM`, `RUN`, …).

```bash
acq400_cli wait_for_state --state=IDLE --timeout=30 <uutnames>
```

<a id="load_gpg"></a>
### Load GPG

Configure GPG from an STL file

- **Once** - Load STL and run once:
```bash
acq400_cli load_gpg --stl=sos0.stl <uutnames>
```

- **Loop** - Load STL and loop:
```bash
acq400_cli load_gpg --stl=sos0.stl --mode=LOOP <uutnames>
```

- **Timescaler** - Load STL with timescaler:
```bash
acq400_cli load_gpg --stl=sos0.stl --timescaler=10 <uutnames>
```

- **Trigger** - Load STL with GPG trigger:
```bash
acq400_cli load_gpg --stl=sos0.stl --trigger=EXT,RISING <uutnames>
```

- **Clock** - Load STL with GPG clock:
```bash
acq400_cli load_gpg --stl=sos0.stl --clock=EXT,RISING <uutnames>
```

- **Bit** - Load STL targeting GPG bit:
```bash
acq400_cli load_gpg --stl=sos0.stl --bit=0 <uutnames>
```

| Arg | Default | Description |
|-----|---------|-------------|
| **--stl** | — | STL file (required) |
| **--mode** | `ONCE` | GPG mode: `ONCE`, `LOOP`, `LOOPWAIT` |
| **--timescaler**, **--ts** | `1` | GPG timescaler |
| **--trigger**, **--trg** | — | GPG trigger triplet (`SOURCE,SENSE` or `enable,line,sense`) |
| **--clock**, **--clk** | — | GPG clock triplet (`SOURCE,SENSE` or `enable,line,sense`) |
| **--bit** | `0` | GPG target bit |

<a id="setup_hudp"></a>
### Setup HUDP

Configure Hardware UDP between a TX UUT and an RX UUT (or `none` / `pc` for one side).

- **TX → RX**:
```bash
acq400_cli setup_hudp --tx_ip 10.12.198.128 --rx_ip 10.12.198.129 \
    --run0='1 1,16,0' --play0='1 16' acq2106_363 acq2106_364
```

- **TX → PC**:
```bash
acq400_cli setup_hudp --tx_ip 10.12.198.128 --rx_ip 10.12.198.254 \
    --run0='1 1,16,0' --spp=11 acq2106_363 none
```

- **Broadcast TX**:
```bash
acq400_cli setup_hudp --tx_ip 10.12.198.128 --rx_ip 10.12.198.129 \
    --broadcast --run0='1 1,16,0' acq2106_363 none
```

<a id="plot_datafile"></a>
### Plot Datafile

Plot a datafile from disk

- **Plot by channel** - Plot channel 1-4 each channel from each source in own row
```bash
acq400_cli plot_datafile --chan=1-4 --plot_by=channel <datafiles>
```

- **Plot by source** - Plot channel 1,3 from each source in own figure
```bash
acq400_cli plot_datafile --chan=1,3 --plot_by=source <datafiles>
```

- **Plot spad** - Plot channel 1 and spad 0
```bash
acq400_cli plot_datafile --chan=1 --spad=0 <datafiles>
```

- **Plot skip** - Plot channel 1 from 50K samples
```bash
acq400_cli plot_datafile --chan=1 --pses=50K <datafiles>
```

- **Plot truncate** - Plot channel 1 up to 50K samples
```bash
acq400_cli plot_datafile --chan=1 --pses=:50K <datafiles>
```

- **Plot stride** - Plot channel 1 every 100th sample
```bash
acq400_cli plot_datafile --chan=1 --pses=::100 <datafiles>
```

- **Plot exclude** - Plot channel 1 exclude every 5000th sample
```bash
acq400_cli plot_datafile --chan=1 --mask=::5000 <datafiles>
```

- **Plot seconds** - Plot channel 1 in seconds
```bash
acq400_cli plot_datafile --chan=1 --secs <datafiles>
```

- **Plot volts** - Plot channel 1 in volts
```bash
acq400_cli plot_datafile --chan=1 --egu <datafiles>
```

- **Plot format** - Plot data from pcfg2 file
```bash
acq400_cli plot_datafile --pcfg=<pcfg2 file> <datafiles>
```

<a id="generate_hexdump"></a>
### Generate Hexdump

Print `hexdump` commands for UUTs current stream and transient sample formats.

- **Default** — native channel width:
```bash
acq400_cli generate_hexdump <uutnames>
```

- **As width** — force 2 or 4-bytes (32×2B → 16×4B):
```bash
acq400_cli generate_hexdump --as_width=4 <uutnames>
```

<a id="demux_data"></a>
### Demux Datafile

Demux datafiles into individual channels

- **Demux** - Demux muxed datafiles into individual channels
```bash
acq400_cli demux_data <datafiles>
```

<a id="upload_waveform"></a>
### Upload Waveform

Upload waveform files to AO modules (oneshot, rearm, or continuous).

- **Oneshot** - load and play once:
```bash
acq400_cli upload_waveform <uutnames> sine.dat
```

- **Continuous** - load and play continuously:
```bash
acq400_cli upload_waveform <uutnames> sine.dat --mode=CONTINUOUS
```

- **Multiple files** - upload waveforms in sequence:
```bash
acq400_cli upload_waveform <uutnames> wf1.dat wf2.dat --trigger=EXT,RISING
```

- **Burst** - play bursts on each external event:
```bash
acq400_cli upload_waveform <uutnames> sine.dat --rgm=RTM,RISING --burstlen=5000 --trigger=AUTO
```

| Arg | Default | Description |
|-----|---------|-------------|
| **uutnames** | — | UUT hostnames |
| **filepaths** | — | Waveform files |
| **--mode** | `ONCE` | AWG mode (`ONCE`, `REARM`, `CONTINUOUS`) |
| **--trigger**, **--trg** | `EXT,RISING` | AWG trigger (`SOURCE,SENSE`) |
| **--rgm** | `0,0,0` | RGM trigger |
| **--burstlen** | `0` | Burst length |
| **--clock**, **--clk** | — | AWG clock |
| **--clock_div**, **--clkdiv** | — | AWG clock divider |
| **--prepend0** | off | Prepend one empty distributor sample (zeros) to the start of the waveform |

<a id="upload_waveform_segment"></a>
### Upload Waveform Segments

Load each file into a successive AWG segment (`A`, `B`, `C`, …) in REARM mode, then keep feeding a play pattern until Ctrl+C. Requires `awg_max_seg` large enough for the file count.

- **Default pattern** - files map to `A`, `B`, `C`; pattern is `ABC`:
```bash
acq400_cli upload_waveform_segment <uutnames> wfA.dat wfB.dat wfC.dat
```

- **Custom pattern** - play order `BCA` on each trigger:
```bash
acq400_cli upload_waveform_segment <uutnames> wfA.dat wfB.dat wfC.dat --pattern=BCA
```

Press Ctrl+C to stop feeding the pattern.

| Arg | Default | Description |
|-----|---------|-------------|
| **uutnames** | — | UUT hostnames |
| **filepaths** | — | Waveform files (index 0 → segment `A`) |
| **--pattern** | `ABC…` from file count | Segment play letters (`BCA`) |
| **--trigger**, **--trg** | `SOFT,RISING` | AWG trigger (`SOURCE,SENSE`) |
| **--rgm** | `0,0,0` | RGM trigger |
| **--burstlen** | `0` | Burst length |
| **--clock**, **--clk** | — | AWG clock |
| **--clock_div**, **--clkdiv** | — | AWG clock divider |

<a id="stream_to_awg"></a>
### Stream AWG

Stream waveform files to AO modules continuously until Ctrl+C.

- **Continuous** - stream a waveform file until Ctrl+C:
```bash
acq400_cli stream_to_awg <uutnames> sine.dat
```

- **Multiple files** - cycle through waveform files:
```bash
acq400_cli stream_to_awg <uutnames> wf1.dat wf2.dat --trigger=EXT,RISING
```

- **Burst** - stream bursts on each external event:
```bash
acq400_cli stream_to_awg <uutnames> sine.dat --rgm=RTM,RISING --burstlen=5000 --trigger=AUTO
```

| Arg | Default | Description |
|-----|---------|-------------|
| **uutnames** | — | UUT hostnames |
| **filepaths** | — | Waveform files |
| **--trigger**, **--trg** | `EXT,RISING` | AWG trigger (`SOURCE,SENSE`) |
| **--rgm** | `0,0,0` | RGM trigger |
| **--burstlen** | `0` | Burst length |
| **--clock**, **--clk** | — | AWG clock |
| **--clock_div**, **--clkdiv** | — | AWG clock divider|

Note: Stop with Ctrl+C.


<a id="generate_waveform"></a>
### Generate Waveform

Build a waveform from a `.wdef` file **or** from spec args. `--nchan`, `--length`, and `--data_size` are always required. `--wavedef` cannot be combined with spec args.

- **From wdef**:
```bash
acq400_cli generate_waveform --wavedef=my_wave.wdef --nchan=32 --length=3125 --data_size=2
```

- **From args** — 3 cycles of 2001 samples on channels 1 and 3:
```bash
acq400_cli generate_waveform --nchan=32 --length=6003 --data_size=2 --chan=1,3 --wavelength=2001 --cycles=3
```

- **Save** — `--save` writes a `.wdat` under `--root` (`WAVEFORMS`). `--save=label` sets the filename label; with `--wavedef` the label is the wdef name; otherwise a timestamp is used.

```bash
acq400_cli generate_waveform --nchan=32 --length=6003 --data_size=2 --chan=1,3 --wavelength=2001 --cycles=3 --save=bingbong --no_plot
```

All wdef options can be used as args for quick simple waveforms.

## Definitions

### Triggers

Capture commands `--trigger`, `--event0`, `--event1`

**Syntax**

- **Short form:** `SOURCE,SENSE` - e.g. `--trigger=EXT,RISING`
- **Source only:** `SOURCE` - defaults to rising edge, e.g. `--trigger=SOFT`
- **Full triplet:** `enable,line,sense` - e.g. `--trigger=1,0,1` (set source with `--trigger_source` )

#### Source:

| Source | Description |
|--------|-------------|
| **EXT** | External Trigger input (front panel) |
| **HDMI** | HDMI Trigger input |
| **WRTT0** | White Rabbit Trigger (line 0) |
| **FREE** | Free running. Disables Trigger in |
| **INT** | Software Trigger |
| **SOFT** | Software Trigger |
| **WRTT1** | White Rabbit Trigger (line 1) |
| **AUTO** | Auto Software Trigger |

#### Sense:

| Sense | Value | Description |
|-------|-------|-------------|
| **FALLING** | 0 | Trigger on falling edge|
| **RISING** | 1 | Trigger on rising edge|



### Capture States

| State | Value | Description |
|--------|-------|-------------|
| **IDLE** | 0 | Ready to be armed |
| **ARM** | 1 | Armed and waiting for a trigger |
| **RUN** | 2 | Stream Capturing |
| **RUN_PRE** | 2 | Transient Pre Capture |
| **RUN_POST** | 3 | Transient Post Capture |
| **POST_PROCESS** / **POPROCESS** | 4 | Post-capture demuxing |
| **CLEANUP** | 5 | Cleanup capture |


### Plot Configuration File V2 (.pcfg2)

A `.pcfg2` file controls layout and trace options for `plot_datafile`

 Each line defines **one subplot row**. Options are separated by **semicolons** (`;`) as `key=value` pairs


```bash
acq400_cli plot_datafile --pcfg=my_plot.pcfg2 <datafiles>
```

**Example**


| Option | Default | Description |
|--------|---------|-------------|
| **chan** | — | channels to plot. Comma list and/or ranges (`1,3,5-8`).|
| **spad** | — | SPAD channels to plot.|
| **source** | `-1` | Source indexes to read from. Comma list (`0,1`) or `-1` for all|
| **view** | `RAW` | Y-axis data type. `RAW` or `VOLTS` |
| **figure** | `-1` | `-1` auto figure or set explicitly `0,1`|
| **row** | `-1` | row within the figure. `-1` auto-increments |
| **mask** | — | indexes and/or range to **exclude**|
| **bitmask** | — | Hex bit mask |
| **bitslice** | — | Hex bit mask; each set bit is plotted as its own trace|
| **title** | — | Subplot row title. |
| **figure_title** | — | Figure suptitle (first line wins)|
| **label** | — | Legend label format string|
| **legend** | `true` | Show legend on the row `true`/`false`|
| **drawstyle** | `default` | draw style (`default`, `steps`, `steps-pre`, `steps-mid`, `steps-post`). |
| **linestyle** | `-` | line style (`-`, `--`, `:`, `-.`). |
| **color** | — | Trace color, or omit to use the default color cycle. |


### Waveform Definition File (.wdef)

Each line defines **one waveform placement**. Options are separated by **semicolons** (`;`) as `key=value` pairs.

**Example**

```text
# full-scale sine of 3125 samples on all channels
chan=0;wavelength=3125;shape=SINE

# half-scale sine on a 0.5 channel baseline
chan=1,3;wavelength=2001;cycles=1;scale=0.5;chan_offset=0.5
```

| Option | Default | Description |
|--------|---------|-------------|
| **chan** | `0` | Channels to write. `0` / `ALL` = all channels, or comma list and/or `start:end:stride` ranges. |
| **index** | `0` | Sample index where the waveform is anchored. Comma list and/or `start:end:stride` ranges. |
| **wavelength** | `5000` | Samples per cycle. |
| **cycles** | `1` | Number of cycles. `-1` fills from `index` to the end of the buffer. |
| **truncate** | `0` | Max samples to keep from the generated waveform (`0` = no truncate). |
| **skip** | `0` | Samples to drop from the start of the generated waveform. |
| **sense** | `RISING` | `RISING` — waveform starts at `index`; `FALLING` — waveform ends at `index`. |
| **phase_offset** | `0` | Phase offset in **radians** (e.g. `3.14159` for invert). |
| **wave_offset** | `0` | Vertical offset of the generated segment as a fraction of full scale. |
| **chan_offset** | `0` | Vertical offset of the whole channel as a fraction of full scale. |
| **shape** | `SINE` | Waveform type: `SINE`, `SQUARE`, `RAMP`, or `DC` |
| **scale** | `1` | Amplitude as a fraction of full scale for the channel data size (`1` = full scale). |


### Test Configuration File (.tcfg)
##TODO

### Datafile formats (.dat)

Datafile format is encoded in the filename as dot-separated parts:

```text
hostname.timestamp.format.sequence.dat
```

| Part | Required | Example | Description |
|------|----------|---------|-------------|
| **hostname** | no | `acq2106_054` | UUT name (`ACQ…` / `Z7IO…` / `KMCUZ…`) |
| **timestamp** | no | `26-06-19_15-21-41` | Capture time (`yy-mm-dd_HH-MM-SS`) |
| **format** | **yes** | `32CHx2B+8SPD` | Sample format tag |
| **sequence** | no | `001` | File sequence number |

Examples:

```text
acq2106_054.32CHx2B+8SPD.dat
acq2106_054.26-06-19_15-21-41.96CHx2B+8SPD.001.dat
acq2206_077.24CHx4B.dat
```

#### Format tag

The format tag describes sample format.

| Segment | Meaning | Bytes / channel | dtype |
|---------|---------|-----------------|-------|
| **`NCHxSB`** | `N` ADC channels, `S` bytes each | `S` (`2` or `4`) | `int16` (`2B`) / `int32` (`4B`) |
| **`NDIO`** | `N` DIO channels | `4` | `uint32` |
| **`NSPD`** | `N` SPAD words | `4` | `uint32` |

| Example tag | Layout | Sample size |
|-------------|--------|-------------|
| `32CHx2B` | 32 × 16-bit ADC | 64 B |
| `16CHx4B` | 16 × 32-bit ADC | 64 B |
| `32CHx2B+8SPD` | 32 × 16-bit ADC + 8 SPAD | 64 + 32 = 96 B |
| `96CHx2B+8SPD` | 96 × 16-bit ADC + 8 SPAD | 192 + 32 = 224 B |
| `16CHx2B+8DIO+8SPD` | 16 ADC + 8 DIO + 8 SPAD | 32 + 32 + 32 = 96 B |
