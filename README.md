# acq400_cli

- Command Line Interface for acq400 UUTs

## Installation

```
git clone git://eigg/Software/acq400_cli
cd acq400_cli
pip3 install -e .
```

## Usage

### Transient

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


### Continuous

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

### Configure Sites

Configure sites capture format

- **run0** - Set enabled sites and spad size:
```bash
acq400_cli configure_sites --sites=1,2,3 --spad=8 <uutnames>
```

- **Spad ident** - Add markers into spad columns:
```bash
acq400_cli configure_sites --ident <uutnames>
```

- **Spad microsecond** - Add microsecond to spad[1]:
```bash
acq400_cli configure_sites --us <uutnames>
```

### Configure Clocking

Configure UUTs sync role

- **run0** - Set enabled sites and spad size:
```bash
acq400_cli configure_clock --clk=1M <uutnames>
```


### Configure Capture

Configure UUTs capture

- **Post** - Capture 100K samples and an external trigger
```bash
acq400_cli configure_capture --trigger=EXT,RISING --post=100K <uutnames>
```

- **Pre + Post** - Capture 50K pre 50K post samples on external event:
```bash
acq400_cli configure_capture --pre=50K --post=50K --trigger=SOFT,RISING --event=EXT,RISING <uutnames>
```

- **Stream** - Stream with mask on external trigger
```bash
acq400_cli configure_capture --stream_mask=1-4 --trigger=EXT,RISING <uutnames>
```

- **RTM Stream** - Stream 5000 sample bursts on external trigger
```bash
acq400_cli configure_capture --rgm=RTM,RISING --translen=5000 --trigger=SOFT,RISING <uutnames>
```

### Plot Datafile

Plot a datafile from disk

- **By carrier** - Plot channel 1 each UUT gets its own figure
```bash
acq400_cli <datafile>
```

- **Channels** - Plot channel 1,2,3 each UUT gets its own figure
```bash
acq400_cli --chans=1,2,3 <datafile>
```

- **Plot start** - Plot channel 1,2,3 from 50K samples
```bash
acq400_cli --chans=1,2,3 --pses=50K:: <datafile>
```

- **Plot stride** - Plot channel 1,2,3 every 100th sample
```bash
acq400_cli --chans=1,2,3 --pses=::100 <datafile>
```

### Generate Hexdump




## Definitions

### Triggers

Trigger sources:

| Source | Description |
|--------|-------------|
| **EXT** | External trigger input (front panel) |
| **HDMI** | HDMI trigger input |
| **WRTT0** | White Rabbit trigger (line 0) |
| **FREE** | Free running. Only enables trigger when UUTs are armed |
| **INT** | Software soft trigger |
| **SOFT** | Software soft trigger |
| **WRTT1** | White Rabbit trigger (line 0) |
| **AUTO** | Auto soft trigger. Only enables trigger when UUTs are armed |


### Capture States

| State | Value | Description |
|-------|-------|-------------|
| **IDLE** | 0 | ready to be armed |
| **ARM** | 1 | Armed and waiting for a trigger |
| **RUN** | 2 | Stream Capturing |
| **RUN_PRE** | 2 | Transient Pre Capturing |
| **RUN_POST** | 3 | Transient Post Capturing |
| **POST_PROCESS** / **POPROCESS** | 4 | Post-capture demuxing |
| **CLEANUP** | 5 | Cleanup of capture processes |


### Plot Configuration File (.pcfg)
### Waveform Configuration File (.wcfg)
### Datafiles (.data, .chan)
### Test Configuration File (.tcfg)

