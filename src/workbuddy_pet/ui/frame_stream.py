"""Bounded, cancellable RGBA decoding. No Qt objects belong to the worker."""
import queue
import threading
from ..materials import iter_animation

_SLOTS = threading.BoundedSemaphore(2)


class FrameStream:
    def __init__(self, path, loop, loop_range=None):
        self.frames = queue.Queue(6)
        self.stop = threading.Event()
        self.done = threading.Event()
        self.exit = threading.Event()
        self.tail_started = threading.Event()
        self.error = None
        self.thread = threading.Thread(target=self._run, args=(path, loop, loop_range), daemon=True)
        self.thread.start()

    def close(self):
        self.stop.set()

    def _run(self, path, loop, loop_range):
        acquired = False
        try:
            while not self.stop.is_set():
                if _SLOTS.acquire(timeout=.05):
                    acquired = True
                    break
            if not acquired:
                return
            first = True
            while not self.stop.is_set():
                for index,frame in enumerate(iter_animation(path, long=True)):
                    if loop_range:
                        if not first and index < loop_range[0]:continue
                        if index == loop_range[1]:
                            if not self.exit.is_set():break
                            self.tail_started.set()
                    if self.stop.is_set():
                        return
                    while not self.stop.is_set():
                        try:
                            self.frames.put(frame, timeout=.05)
                            break
                        except queue.Full:
                            pass
                if not loop or (self.exit.is_set() and (not loop_range or self.tail_started.is_set())):
                    return
                first = False
        except Exception as error:
            self.error = str(error)
        finally:
            if acquired:
                _SLOTS.release()
            self.done.set()
