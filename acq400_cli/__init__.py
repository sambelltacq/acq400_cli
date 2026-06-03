"""acq400_cli package initialization."""

import os
import sys

from acq400_cli.logger import Logger

loglevel = 'TRACE' if os.environ.get('SITECLIENT_TRACE') == '1' else os.environ.get('ACQ400_LOGLEVEL', 'INFO')
logger = Logger.configure(level=loglevel, logger_name=__name__)
logger.debug(f"Command: {' '.join(sys.argv)}")

from acq400_cli.uut import Carrier, Collection
from acq400_cli.parser import ArgTypes, ArgParser
from acq400_cli.signal_generator import SignalGenerator
from acq400_cli.utils import generate_timestamp
from acq400_cli.plotting import plot_by_carrier
from acq400_cli.clients import StreamClient
from acq400_cli.data import parse_filename_parts
from acq400_cli.constants import *

