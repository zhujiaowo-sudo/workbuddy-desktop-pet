"""Short background tasks with queued Qt delivery; no GUI work on worker threads."""
import threading
from PySide6.QtCore import QObject, Signal


class Task(QObject):
    done = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, function, parent=None):
        super().__init__(parent)
        self.function = function
        self.cancel = threading.Event()
        self.thread = None

    def start(self):
        def run():
            try:
                result = self.function()
                if not self.cancel.is_set():
                    self.done.emit(result)
            except Exception as error:
                if not self.cancel.is_set():
                    self.failed.emit(str(error)[:220])
            finally:
                self.finished.emit()
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
