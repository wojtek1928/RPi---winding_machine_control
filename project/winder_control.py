from PyQt5.QtCore import pyqtSignal, QThread, QObject
from time import sleep


class WinderThread(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def run1(self, text: str):
        print(f"Worker - run1: {text}")
        sleep(3)
        self.finished.emit("run1 - Done")
