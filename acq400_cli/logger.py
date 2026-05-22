#!/usr/bin/env python3
"""
Custom logger
"""

import logging
from logging.handlers import RotatingFileHandler
import os

class ModuleFilter(logging.Filter):
    """Silence non acq400 loggers"""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name == "acq400_cli" or record.name.startswith(
            "acq400_cli."
        )


class ColoredLevelFormatter(logging.Formatter):
    """Per Level formatting"""

    def __init__(self, level_formats):
        super().__init__()
        self.level_formats = dict(level_formats)

    def format(self, record: logging.LogRecord) -> str:
        info_level_no = logging.INFO
        level_format = self.level_formats.get(record.levelno, self.level_formats[info_level_no])["format"]
        formatter = logging.Formatter(level_format)
        return formatter.format(record)


class Logger:
    """Custom logger"""

    file_fmt = "[%(asctime)s %(levelname)s]: %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    max_log_bytes = 1 * 1024 * 1024
    log_backup_count = 1

    escape_codes = {
        'reset': "\x1b[0m",
        'yellow': "\x1b[38;5;226m",
        'red': "\x1b[38;5;196m",
        'green': "\x1b[38;5;46m",
        'boldred': "\x1b[1;38;5;196m",
        'blue': "\x1b[34m",
    }
    
    custom_levels = {
        "trace": {
            "level": 5,
            "name": "TRACE",
            "console_format": "[{blue}%(levelname)s{reset}]: %(message)s",
        },
        "debug": {
            "level": logging.DEBUG,
            "name": "DEBUG",
            "console_format": "[%(levelname)s]: %(message)s",
        },
        "info": {
            "level": logging.INFO,
            "name": "INFO",
            "console_format": "%(message)s",
        },
        "warning": {
            "level": logging.WARNING,
            "name": "WARNING",
            "console_format": "[{yellow}%(levelname)s{reset}]: %(message)s",
        },
        "error": {
            "level": logging.ERROR,
            "name": "ERROR",
            "console_format": "[{red}%(levelname)s{reset}]: %(message)s",
        },
        "critical": {
            "level": logging.CRITICAL,
            "name": "CRITICAL",
            "console_format": "[{boldred}%(levelname)s{reset}]: %(message)s",
        },
        "success": {
            "level": 21,
            "name": "SUCCESS",
            "console_format": "[{green}%(levelname)s{reset}]: %(message)s",
        },
        "failure": {
            "level": 22,
            "name": "FAILURE",
            "console_format": "[{red}%(levelname)s{reset}]: %(message)s",
        },
    }

    @classmethod
    def _register_levels(cls, colors_enabled=True):
        level_formats = {}

        for method_name, config in cls.custom_levels.items():
            level_no = config["level"]
            level_name = config["name"]
            console_format = config["console_format"].format(
                **{k: (cls.escape_codes[k] if colors_enabled else "") for k in cls.escape_codes}
            )

            logging.addLevelName(level_no, level_name)
            level_formats[level_no] = {"format": console_format}

            if not hasattr(logging.Logger, method_name):
                def level_method(self, message, *args, _level_no=level_no, **kwargs):
                    if self.isEnabledFor(_level_no):
                        self._log(_level_no, message, args, **kwargs)

                setattr(logging.Logger, method_name, level_method)

        return level_formats

    @classmethod
    def configure(cls, level='INFO', logger_name="acq400_cli"):
        file_name = f"{logger_name}.log"
        level = Logger.custom_levels.get(level.lower(), {}).get('level', logging.INFO)
        colors_enabled = bool(int(os.environ.get('ACQ400_COLORS', 1)))
        level_formats = cls._register_levels(colors_enabled)

        logger = logging.getLogger(logger_name)
        logger.setLevel(cls.get_level_no('TRACE'))
        logger.propagate = False

        logger.handlers.clear()

        module_filter = ModuleFilter()

        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(ColoredLevelFormatter(level_formats=level_formats))
        console_handler.addFilter(module_filter)

        file_handler = RotatingFileHandler(
            file_name,
            maxBytes=cls.max_log_bytes,
            backupCount=cls.log_backup_count,
        )
        file_handler.setLevel(cls.get_level_no('TRACE'))
        file_handler.setFormatter(logging.Formatter(cls.file_fmt, datefmt=cls.date_fmt))
        file_handler.addFilter(module_filter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        for method_name in Logger.custom_levels:
            setattr(logging, method_name, getattr(logger, method_name))
        
        return logger

    @classmethod
    def get_level_no(cls, level):
        if isinstance(level, int): return level
        return cls.custom_levels.get(level.lower(), {}).get("level", logging.INFO)

def set_log_level(level, logger_name="acq400_cli"):
    """Update logger level."""
    level_no = Logger.get_level_no(level)
    log = logging.getLogger(logger_name)
    #log.setLevel(level_no)
    for h in log.handlers:
        if isinstance(h, RotatingFileHandler): continue
        h.setLevel(level_no)


def get_logger(level='INFO'):
    """init and return logger"""
    logger = Logger.configure(level=level.lower())
    return logger

if __name__ == '__main__':
    get_logger('TRACE')
    logging.debug("A debug message")
    logging.info("A info message")
    logging.warning("A warning message")
    logging.error("A error message")
    logging.critical("A critical message")
    logging.success("A success message")
    logging.failure("A failure message")
    logging.trace("A trace message")