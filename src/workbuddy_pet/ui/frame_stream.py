"""Bounded, cancellable RGBA decoding. No Qt objects belong to the worker."""
import queue
import threading
from ..materials import iter_animation

_SLOTS = threading.BoundedSemaphore(2)


class FrameStream:
    def __init__(self, path, loop):
        self.frames = queue.Queue(6)
        self.stop = threading.Event()
        self.done = threading.Event()
        self.error = None
        self.thread = threading.Thread(target=self._run, args=(path, loop), daemon=True)
        self.thread.start()

    def close(self):
        self.stop.set()

    def _run(self, path, loop):
        acquired = False
        try:
            while not self.stop.is_set():
                if _SLOTS.acquire(timeout=.05):
                    acquired = True
                    break
            if not acquired:
                return
            while not self.stop.is_set():
                for frame in iter_animation(path, long=True):
                    if self.stop.is_set():
                        return
                    while not self.stop.is_set():
                        try:
                            self.frames.put(frame, timeout=.05)
                            break
                        except queue.Full:
                            pass
                if not loop:
                    return
        except Exception as error:
            self.error = str(error)
        finally:
            if acquired:
                _SLOTS.release()
            self.done.set()
