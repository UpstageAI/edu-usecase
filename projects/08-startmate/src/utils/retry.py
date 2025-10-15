from __future__ import annotations
import time

def retry(fn, tries: int = 3, delay: float = 0.5):
    for i in range(tries):
        try:
            return fn()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(delay * (2 ** i))
