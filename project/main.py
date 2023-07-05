import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QMenuBar, QTabWidget
from PyQt5 import uic
import pigpio

from encoder import Encoder
from relay_module import RelayModule
from tab_manual_steering import ManualSteeringTab
from tab_manual_insert import ManualInsertingTab

current_dir = os.path.dirname(os.path.abspath(__file__))
ui_templates_dir = os.path.join(current_dir, "ui_templates")

# To run this script via SSH first use command: `export DISPLAY=:0`
# Do not forget to run `sudo pigpiod`


class UI(QMainWindow):
    def __init__(self):
        super(UI, self).__init__()

        # Load main_window.ui file
        uic.loadUi(os.path.join(ui_templates_dir, "main_window.ui"), self)

        # Adding module with mnual steering
        ManualSteeringTab(self, ui_templates_dir, relay_mod, encoder)
        # Adding module wiyh manual insert
        ManualInsertingTab(self, ui_templates_dir, relay_mod, encoder)

        # Define events
        # menuBar -> menuHelp -> actionInformation
        self.actionInformation.triggered.connect(self.openInfo)

        # Show the app
        self.showFullScreen()

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


pi = pigpio.pi()
relay_mod = RelayModule(pi=pi)
encoder = Encoder(pi=pi)
app = QApplication(sys.argv)
UIWindow = UI()
app.exec_()

pi.stop()
