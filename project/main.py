import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QMenuBar, QTabWidget
from PyQt5 import uic
import pigpio
from loguru import logger

from encoder import Encoder
from machine_control import MachineControl
from buzzer import Buzzer
from tab_manual_steering import ManualSteeringTab
from tab_manual_insert import ManualInsertingTab


current_dir = os.path.dirname(os.path.abspath(__file__))
ui_templates_dir = os.path.join(current_dir, "ui_templates")
logger.add(os.path.join(current_dir, "LOGS/RopeCutter.log"), rotation='1 day')


class UI(QMainWindow):
    def __init__(self):
        super(UI, self).__init__()
        self.pi: pigpio.pi = pigpio.pi()
        self.buzzer = Buzzer(self.pi)
        self.machine_control = MachineControl(self.pi, self.buzzer)
        self.encoder = Encoder(pi=self.pi)
        # Load main_window.ui file
        uic.loadUi(os.path.join(ui_templates_dir, "main_window.ui"), self)

        # Adding module with mnual steering
        ManualSteeringTab(
            self,
            ui_templates_dir,
            self.machine_control,
            self.encoder,
            self.pi,
            self.buzzer
        )
        # Adding module wiyh manual insert
        ManualInsertingTab(self, ui_templates_dir,
                           self.machine_control, self.encoder)

        # Define events
        # menuBar -> menuHelp -> actionInformation
        self.actionInformation.triggered.connect(self.openInfo)

        # Show the app

        self.show()
        logger.success("Apllication mounted")
    # Event handler functions

    # Open info window

    def openInfo(self):
        infoDialog = QDialog()
        infoDialog = uic.loadUi(os.path.join(
            ui_templates_dir, "info.ui"), infoDialog)
        infoDialog.exec_()

    def enableMainWindow(self, currentTab: int, state: bool):
        self.tabWidget: QTabWidget
        for tab in range(self.tabWidget.count()):
            if state:
                self.tabWidget.setTabEnabled(tab, state)
            else:
                enabled = tab == currentTab
                self.tabWidget.setTabEnabled(tab, enabled)

        self.menuBar: QMenuBar
        self.menuBar.setEnabled(state)

    def __del__(self):
        self.pi.stop()


@logger.catch
def main():
    # To run this script via SSH first use command: `export DISPLAY=:0`
    # Do not forget to run `sudo pigpiod`

    app = QApplication(sys.argv)
    UI()
    app.exec_()


main()
