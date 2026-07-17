"""random helpers."""
import time, hashlib
from functools import wraps
from typing import Callable

def timed(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*a, **kw):
        t0 = time.perf_counter()
        return fn(*a, **kw), (time.perf_counter() - t0) * 1000
    return wrapper

def md5(s: str) -> str:
    return hashlib.md5(s.encode(), usedforsecurity=False).hexdigest()[:12]
