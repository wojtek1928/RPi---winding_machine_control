from PyQt5.QtCore import QRunnable, QObject, pyqtSignal, QThreadPool
import time

from machine_control import MachineControl, Actions, MachineWorker
from stopwatch import Stopwatch
from encoder import Encoder


class Signals(QObject):
    started = pyqtSignal()
    length_reading = pyqtSignal(str)
    time_reading = pyqtSignal(str)
    error_signal = pyqtSignal(str, str)


class MonitorProcess(QRunnable):
    def __init__(self, machine_control: MachineControl, encoder: Encoder, stopwatch: Stopwatch):
        super().__init__()
        self.machine_control = machine_control
        self.encoder = encoder
        self.stopwatch = stopwatch
        self.signals = Signals()
        self.work_not_done = True
        self.should_emit_lenght: bool = True
        self.should_emit_time: bool = True

    def set_work_done(self):
        """
        Ends monitor thread loop
        """
        self.work_not_done: bool = False

    def run(self):
        while self.work_not_done:
            if self.should_emit_lenght:
                self.signals.length_reading.emit(self.encoder.__str__())
            if self.should_emit_time:
                self.signals.time_reading.emit(self.stopwatch.__str__())
            time.sleep(0.0001)
