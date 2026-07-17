"""logging via rich. nothing fancy."""
import logging
from rich.logging import RichHandler
from rich.console import Console

_console = Console(stderr=True, soft_wrap=True)

def get_logger(name: str = "nettest") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    h = RichHandler(console=_console, show_path=False, show_time=False, rich_tracebacks=True)
    h.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(h)
    return logger
