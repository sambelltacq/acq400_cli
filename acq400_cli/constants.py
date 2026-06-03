"""
UUT defined constants
"""

from enum import IntEnum

TIMESTAMP_FMT = "%y-%m-%d_%H-%M-%S"

MAX_ETH_RATE=30

class PORTS(IntEnum):
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



class SITES(IntEnum):
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


class CAPTURE_STATE(IntEnum):
    IDLE=           0
    ARM =           1
    RUN=            2
    RUN_PRE =       2
    RUN_POST=       3
    POST_PROCESS=   4
    POPROCESS=      4
    CLEANUP=        5

class TRG_LINE(IntEnum):
    EXT=    0
    HDMI=   0
    WRTT0=  0
    FREE=   0
    INT=    1
    SOFT=   1
    WRTT1=  1

class SENSE(IntEnum):
    FALLING=    0
    RISING=     1



#http://eigg:8090/mediawiki/index.php/Products:ACQ400:ACQ400_Data_Format
class EventSignature:
    pass
