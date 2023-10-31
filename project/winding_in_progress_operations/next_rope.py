from PyQt5.QtCore import QRunnable, QObject, pyqtSignal
import time
from os import getenv


class Signals(QObject):
    started = pyqtSignal()
    failed = pyqtSignal()
    done = pyqtSignal()


class NextRope(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = Signals()
        self.__cancel_cutting: bool = False

    def cancel_confirmation(self):
        self.__cancel_cutting = True

    def run(self):
        start = time.time()
        while time.time() - start < int(getenv('CONFIRM_NEW_LINE_TIME')) and not self.__cancel_cutting:
            pass

        if self.__cancel_cutting:
            self.signals.failed.emit()
        else:
            self.signals.done.emit()
