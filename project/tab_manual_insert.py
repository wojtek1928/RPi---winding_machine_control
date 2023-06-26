import os
import time
import threading
from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets
from PyQt5 import uic

from encoder import Encoder
from relay_module import RelayModule


class ManualInsertingTab(QtWidgets.QWidget):
    def __init__(self, parent_class: QtWidgets.QMainWindow, ui_templates_dir: str, relay_mod: RelayModule, encoder: Encoder):
        super().__init__()

        try:
            uic.loadUi(os.path.join(
                ui_templates_dir, "manual_insert_tab.ui"), self)

            self.relay_mod = relay_mod
            self.encoder = encoder
            self.parent_class = parent_class
            self.min_len = 100

            # Assign types and events handlers to elements
            # centralWidget -> tabWidget -> manualnsert_tab -> lenghth_lineEdit
            self.length_lineEdit: QtWidgets.QLineEdit
            self.length_lineEdit.setValidator(QtGui.QIntValidator(0, 1000000))
            self.length_lineEdit.installEventFilter(self)
            self.length_lineEdit.textChanged.connect(self.checkInput)
            # centralWidget -> tabWidget -> manualnsert_tab -> quantity_lineEdit
            self.quantity_lineEdit: QtWidgets.QLineEdit()
            self.quantity_lineEdit.setValidator(
                QtGui.QIntValidator(0, 10))
            self.quantity_lineEdit.installEventFilter(self)
            self.quantity_lineEdit.textChanged.connect(self.checkInput)

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
            self.backspace_pushButton.clicked.connect(
                lambda: self.removeNumber())

            # centralWidget -> tabWidget -> manualnsert_tab -> run_pushButton
            self.run_pushButton: QtWidgets.QPushButton
            self.run_pushButton.clicked.connect(lambda: self.runProccess())
            self.run_pushButton.setEnabled(False)

            # Add tab to main window
            parent_class.tabWidget.addTab(self, "Wprowadzanie ręczne")

        except Exception as e:
            print("Module ManualInsertingTab initialization failed.", e, sep='\n')

        # manualInsert_tab events functions
    # Line selection support for numeric touch pad
    focusedLine: QtWidgets.QLineEdit
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
    # Process

    # A function that dynamically validates length and quantity values. If values are correct then run_pushButton button is enabled.
    def checkInput(self):
        # The try-except statement is an additional safeguard in addition to QIntValidator against non-int input
        try:
            if (int(self.length_lineEdit.text()) > self.min_len) and (int(self.quantity_lineEdit.text()) > 0):
                self.run_pushButton.setEnabled(True)
            else:
                self.run_pushButton.setEnabled(False)
        except:
            pass

    def runProccess(self):

        if (int(self.length_lineEdit.text()) > self.min_len) and (int(self.quantity_lineEdit.text()) > 0):
            self.parent_class.enableMainWindow(
                self.parent_class.tabWidget.currentIndex(), False)
            self.encoder.begin_measurement()
            self.relay_mod.winder_clockwise()
            while self.encoder.get_distace(0) < int(self.length_lineEdit.text()):
                time.sleep(0.01)
                print("Current lenght: ", self.encoder.get_distace(0))

            self.relay_mod.winder_STOP()
            self.encoder.reset_measurement()
            self.parent_class.enableMainWindow(
                self.parent_class.tabWidget.currentIndex(), True)
            print("Done")
