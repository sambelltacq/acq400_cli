"""
UUT defined constants
"""

import os
from enum import IntEnum

TIMESTAMP_FMT = "%y-%m-%d_%H-%M-%S"

DATE_FMT = "%y-%m-%d"

POWER_MW_SCALE = 1.25 * 3.64e-6 * 1000

MAX_ETH_RATE=30


class AutoIntEnum(IntEnum):
    """IntEnum with auto resolution"""
    @classmethod
    def names(cls):
        return ', '.join(cls.__members__)

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            name = value.strip().upper()
            if name in cls.__members__: return cls[name]
            if name.isdigit(): return cls(int(name))
        return None


class PORTS(AutoIntEnum):
    """UUT port constants"""
    TSTAT = 2235
    STREAM = 4210
    SITE0 = 4220
    SEGSW = 4250
    SEGSR = 4251
    DPGSTL = 4521
    GPGSTL= 4541
    GPGDUMP = 4543

    WRPG = 4606

    DIO482_PG_STL = 45001
    DIO482_PG_DUMP = 45003

    BOLO8_CAL = 45072
    BOLO8_CAL1 = 45073
    BOLO8_CAL2 = 45074

    DATA0 = 53000
    DATAT = 53333
    MULTI_EVENT_TMP = 53555
    MULTI_EVENT_DISK = 53556
    DATA_SPY = 53667
    LIVETOP = 53998
    ONESHOT = 53999
    AWG_ONCE = 54201
    AWG_AUTOREARM = 54202
    AWG_CONTINUOUS = 54205
    AWG_STREAM = 54207
    AWG_SEGMENT_SELECT = 54210
    AWG_SEGMENT_LOAD_ONESHOT = 54212
    MGTDRAM = 53993
    MGTDRAM_PULL_DATA = 53991
    SLOWMON = 53666



class SITES(AutoIntEnum):
    """UUT site constants"""
    s0=     0
    s1=     1
    s2=     2
    s3=     3
    s4=     4
    s5=     5
    s6=     6
    cA=     13
    cB=     12
    cC=     11
    cD=     10
    dsp=    14


class CAPTURE_STATE(AutoIntEnum):
    IDLE=           0
    ARM =           1
    RUN=            2
    RUN_PRE =       2
    RUN_POST=       3
    POST_PROCESS=   4
    POPROCESS=      4
    CLEANUP=        5

class SIG_LINE(AutoIntEnum):
    EXT=    0 # External
    HDMI=   0 # HDMI
    WRTT0=  0 # White Rabbit
    FREE=   0 # Free Running
    INT=    1 # Internal
    SOFT=   1 # Soft
    WRTT1=  1 # White Rabbit
    AUTO=   1 # Auto Soft

class SENSE(AutoIntEnum):
    FALLING=    0
    RISING=     1


class GPG_MODE(AutoIntEnum):
    ONCE=       0
    LOOP=       2
    LOOPWAIT=   3

class RGM_MODE(AutoIntEnum):
    OFF=    0
    RGM=    2
    RTM=    3

class COUNTERS(AutoIntEnum):
    EXT=    -1
    MB=     0
    S1=     1
    S2=     2
    S3=     3
    S4=     4
    S5=     5
    S6=     6

class COLORS:
    RESET = '\033[0m'
    COLOR_EN = bool(int(os.getenv("HAPI_COLOUR", "1")))

    _CODES = {
        'IDLE': '\033[31m',
        'ARM': '\033[38;5;208m',
        'RUN': '\033[32m',
        'RUN_PRE': '\033[32m',
        'RUN_POST': '\033[32m',
        'POST_PROCESS': '\033[35m',
        'POPROCESS': '\033[35m',
        'CLEANUP': '\033[36m',
    }

    @staticmethod
    def get(name, default=None):
        return COLORS._CODES.get(name, default)

    @staticmethod
    def format(color, string):
        if not color or not COLORS.COLOR_EN: return string
        return f"{color}{string}{COLORS.RESET}"


PLOT_TRACE_COLORS = (
    '#1515c4',
    '#f21a1a',
    '#21b321',
    '#000000',
    '#8000ff',
    '#ffaa00',
    '#ff00f0',
    '#f38484',
)

#http://eigg:8090/mediawiki/index.php/Products:ACQ400:ACQ400_Data_Format
class EventSignature:
    pass
