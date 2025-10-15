import time

def retry(fn, tries=3, delay=0.5):
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            if i == tries - 1:
                raise
            time.sleep(delay)
    raise last

class Timer:
    def __enter__(self):
        self.t0 = time.time()
        return self
    def __exit__(self, *_):
        self.ms = int((time.time() - self.t0) * 1000)
