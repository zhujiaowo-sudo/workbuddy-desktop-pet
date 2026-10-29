"""A single background writer for coalesced diagnostics and startup readiness."""
from copy import deepcopy
import threading
import time

from .storage import atomic_json


class RuntimeWriter:
    def __init__(self, path, *, heartbeat=15, retry_delay=1, write=atomic_json):
        self.path = path
        self.heartbeat = heartbeat
        self.retry_delay = retry_delay
        self.write = write
        self.condition = threading.Condition()
        self.latest = None
        self.closing = False
        self.thread = threading.Thread(target=self._run, name='pet-runtime', daemon=True)
        self.thread.start()

    def submit(self, value):
        with self.condition:
            if not self.closing:
                self.latest = deepcopy(value)
                self.condition.notify()

    def close(self):
        with self.condition:
            self.closing = True
            self.condition.notify()
        self.thread.join(timeout=2)

    def _run(self):
        last = None
        last_write = retry_at = 0
        while True:
            with self.condition:
                while True:
                    now = time.monotonic()
                    value = deepcopy(self.latest)
                    comparable = {k: v for k, v in value.items() if k != 'at'} if value else None
                    changed = comparable != last
                    if self.closing and not changed:
                        return
                    if value and (changed or now - last_write >= self.heartbeat):
                        if self.closing or now >= retry_at:
                            break
                        self.condition.wait(retry_at - now)
                    elif self.closing:
                        return
                    else:
                        self.condition.wait(max(.01, self.heartbeat - (now - last_write)) if value else None)
            value['at'] = time.time()
            try:
                self.write(self.path, value)
            except (OSError, ValueError):
                retry_at = time.monotonic() + self.retry_delay
                with self.condition:
                    if self.closing:
                        return
            else:
                last = comparable
                last_write = time.monotonic()
                retry_at = 0
