
import time

class Timer:    
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *a):
        self.end = time.time()
        self.interval = self.end - self.start
