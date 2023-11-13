import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QMenuBar, QTabWidget, QMenu, QAction, QTabWidget
from PyQt5 import uic
import pigpio
from loguru import logger
from dotenv import load_dotenv

from encoder import Encoder
from machine_control import MachineControl
from buzzer import Buzzer
from tab_manual_steering import ManualSteeringTab
from tab_manual_insert import ManualInsertingTab
from orders.tab_orders import OrdersTab
from settings.settings import SettingsDialog

# Load .env variables
load_dotenv()
# Set Current mail file
current_dir = os.path.dirname(os.path.abspath(__file__))
# Set path to templates
ui_templates_dir = os.path.join(current_dir, "ui_templates")
# Set Logger
logger.add(os.path.join(current_dir, "LOGS/RopeCutter.log"), rotation='1 day')


class UI(QMainWindow):
    def __init__(self):
        super(UI, self).__init__()

        # Create pigpio instance
        self.pi: pigpio.pi = pigpio.pi()
        # Create buzzer instance
        self.buzzer = Buzzer(self.pi)
        # Create machine_control instance
        self.machine_control = MachineControl(self.pi)
        # Create encoder instance
        self.encoder = Encoder(pi=self.pi)

        # Load main_window.ui file
        uic.loadUi(os.path.join(ui_templates_dir, "main_window.ui"), self)

        self.tabWidget: QTabWidget
        self.tabWidget.removeTab(0)
        # Add module with orders
        OrdersTab(
            self,
            ui_templates_dir,
            self.machine_control,
            self.encoder,
            self.buzzer
        )

        # Add module with mnual steering
        ManualSteeringTab(
            self,
            ui_templates_dir,
            self.machine_control,
            self.encoder,
            self.pi,
            self.buzzer
        )
        # Add module with manual insert
        ManualInsertingTab(
            self,
            ui_templates_dir,
            self.machine_control,
            self.encoder,
            self.buzzer
        )

        # Define events
        # menuBar -> menuHelp -> actionInformation
        self.actionInformation: QAction
        self.actionInformation.triggered.connect(self.openInfo)
        # menuBar -> settings
        self.menuSettings: QMenu
        self.menuSettings.triggered.connect(self.openSettings)

        # Show the app
        self.showFullScreen()
        logger.success("Apllication mounted")
    # Event handler functions

    def openSettings(self):
        """
        Open `settingsDialog`
        """
        settings_dialog = SettingsDialog(self, ui_templates_dir)
        settings_dialog.exec_()

    def openInfo(self):
        """
        Open `infoDialog`
        """
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
    # Do not forget to run `sudo pigpiod` and `sudo mount /home/admin/Dokumenty/project/windows_SHARED`

    app = QApplication(sys.argv)
    UI()
    app.exec_()


main()
