

class KnobNotFoundError(Exception):
    """Raised when a requested knob/attribute doesn't exist at a site"""

class IOCNotReadyError(Exception):
    """Raised when a UUT IOC isn't ready"""

class GPGNotAvailableError(Exception):
    """Raised when GPG is not enabled"""