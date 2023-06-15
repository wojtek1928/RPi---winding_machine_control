import sys
import os
import time
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QPushButton, QLCDNumber
from PyQt5 import uic
import pigpio
import threading

from encoder import Encoder
from relay_module import RelayModule

current_dir = os.path.dirname(os.path.abspath(__file__))
ui_templates_dir = os.path.join(current_dir, "ui_templates")


class UI(QMainWindow):
    def __init__(self):
        super(UI, self).__init__()

        # Load UI file
        uic.loadUi(os.path.join(ui_templates_dir, "UserInterface.ui"), self)

        # Define events
        # menuBar -> menuHelp -> actionInformation
        self.actionInformation.triggered.connect(self.openInfo)

        # centralWidget -> tabWidget -> manualnsert_tab -> lenghth_lineEdit
        self.length_lineEdit.setValidator(QtGui.QIntValidator(0, 1000000))
        self.length_lineEdit.installEventFilter(self)
        # centralWidget -> tabWidget -> manualnsert_tab -> quantity_lineEdit
        self.quantity_lineEdit.setValidator(QtGui.QIntValidator(0, 1000000))
        self.quantity_lineEdit.installEventFilter(self)

        # centralWidget -> tabWidget -> manualnsert_tab -> keyboard
        # Navigation btns
        self.leftArrow_pushButton.clicked.connect(
            lambda: self.moveCursorLeft())
        self.rightArrow_pushButton.clicked.connect(
            lambda: self.moveCursorRight())
        # Numbers btns
        self.zero_pushButton.clicked.connect(lambda: self.insertNumber(0))
        self.one_pushButton.clicked.connect(lambda: self.insertNumber(1))
        self.two_pushButton.clicked.connect(lambda: self.insertNumber(2))
        self.three_pushButton.clicked.connect(lambda: self.insertNumber(3))
        self.four_pushButton.clicked.connect(lambda: self.insertNumber(4))
        self.five_pushButton.clicked.connect(lambda: self.insertNumber(5))
        self.six_pushButton.clicked.connect(lambda: self.insertNumber(6))
        self.seven_pushButton.clicked.connect(lambda: self.insertNumber(7))
        self.eight_pushButton.clicked.connect(lambda: self.insertNumber(8))
        self.nine_pushButton.clicked.connect(lambda: self.insertNumber(9))
        # Backspace btn
        self.backspace_pushButton.clicked.connect(lambda: self.removeNumber())

        # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> clockwise_pushButton
        self.clockwise_pushButton.clicked.connect(
            lambda: self.winder(self.clockwise_pushButton))
        # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> #centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> clockwise_pushButton
        self.counterClockwise_pushButton.clicked.connect(
            lambda: self.winder(self.counterClockwise_pushButton))
        # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> #centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> stop_pushButton
        self.clicked_winder_btn = self.stop_pushButton  # disabled by default
        self.stop_pushButton.clicked.connect(
            lambda: self.winder(self.stop_pushButton))
        # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> options_widget -> guillotine_pushButton
        self.guillotine_pushButton.pressed.connect(relay_mod.guillotine_press)
        self.guillotine_pushButton.released.connect(relay_mod.guillotine_release)

        # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> #centralWidget -> tabWidget -> manuaSteering_tab -> lengthMeasurement_frame -> startMeasurement_pushButton
        self.startMeasurement_pushButton.clicked.connect(
            lambda: self.measurement(self.startMeasurement_pushButton))
        # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> #centralWidget -> tabWidget -> manuaSteering_tab -> lengthMeasurement_frame -> startMeasurement_pushButton
        self.reset_pushButton.clicked.connect(self.measurement_reset)

        # Show the app
        self.showFullScreen()

    # Event handler functions
    # menuBar events functions
    # Open info window
    def openInfo(self):
        infoDialog = QDialog()
        infoDialog = uic.loadUi(os.path.join(
            ui_templates_dir, "info.ui"), infoDialog)
        infoDialog.exec_()

    # manualInsert_tab events functions
    # Line selection support for numeric touch pad
    focusedLine = None

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.FocusIn:
            if obj == self.length_lineEdit:
                self.focusedLine = obj
            elif obj == self.quantity_lineEdit:
                self.focusedLine = obj

        elif event.type() == QtCore.QEvent.FocusOut:
            self.focusedLine = None

        return super().eventFilter(obj, event)

    # Numeric touchboard handler functions
    def insertNumber(self, number: int):
        if self.focusedLine == self.length_lineEdit:
            self.length_lineEdit.insert(str(number))

        elif self.focusedLine == self.quantity_lineEdit:
            self.quantity_lineEdit.insert(str(number))

    def removeNumber(self):
        if self.focusedLine == self.length_lineEdit:
            self.length_lineEdit.backspace()
        elif self.focusedLine == self.quantity_lineEdit:
            self.quantity_lineEdit.backspace()

    def moveCursorLeft(self):
        if self.focusedLine == self.length_lineEdit:
            self.length_lineEdit.cursorBackward(0, 1)
        elif self.focusedLine == self.quantity_lineEdit:
            self.quantity_lineEdit.cursorBackward(0, 1)

    def moveCursorRight(self):
        if self.focusedLine == self.length_lineEdit:
            self.length_lineEdit.cursorForward(0, 1)
        elif self.focusedLine == self.quantity_lineEdit:
            self.quantity_lineEdit.cursorForward(0, 1)

    # manualSteering_tab functions
    # Winder movement buttons
    def winder(self, button: QPushButton):
        button.setEnabled(False)  # disable currnet button
        self.clicked_winder_btn.setEnabled(True)  # Enable previous clicked
        self.clicked_winder_btn = button  # Set currnet button as clicked

        if button.objectName() == "clockwise_pushButton":
            relay_mod.winder_clockwise()
        elif button.objectName() == "counterClockwise_pushButton":
            relay_mod.winder_counter_clockwise()
        elif button.objectName() == "stop_pushButton":
            relay_mod.winder_STOP()

    def winder_zero_position(self):
        pass

    # Measurement handlers
    def display_current_value(self):
        self.is_displaying = True
        while self.is_displaying:
            self.length_lcdNumber.display(int(encoder.get_distace(1)))
            time.sleep(0.01)

    def measurement(self, QButton: QPushButton):
        if QButton.text() == "Pomiar - start":
            QButton.setText("Pomiar - stop")
            encoder.begin_measurement()
            LCD_display_thread = threading.Thread(
                target=self.display_current_value, daemon=True)
            LCD_display_thread.start()

        elif QButton.text() == "Pomiar - stop":
            QButton.setText("Pomiar - start")
            encoder.pause_measurement()
            self.is_displaying = False

    def measurement_reset(self):
        encoder.reset_measurement()
        self.length_lcdNumber.display(int(encoder.get_distace(1)))


pi = pigpio.pi()
relay_mod = RelayModule(pi=pi)
encoder = Encoder(pi=pi)
app = QApplication(sys.argv)
UIWindow = UI()
app.exec_()
pi.stop()
