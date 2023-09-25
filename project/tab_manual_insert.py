import os
from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets
from PyQt5 import uic

from encoder import Encoder
from machine_control import MachineControl
from winding_in_progress_dialog import WindingInProgressDialog


class ManualInsertingTab(QtWidgets.QWidget):
    def __init__(self, parent_class: QtWidgets.QMainWindow, ui_templates_dir: str, relay_mod: MachineControl, encoder: Encoder):
        super().__init__()

        try:
            uic.loadUi(os.path.join(
                ui_templates_dir, "manual_insert_tab.ui"), self)

            self.relay_mod = relay_mod
            self.encoder = encoder
            self.parent_class = parent_class
            self.ui_templates_dir = ui_templates_dir

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

            # centralWidget -> tabWidget -> manualnsert_tab -> ordrerId_lineEdit
            self.ordrerId_lineEdit: QtWidgets.QLineEdit()
            self.ordrerId_lineEdit.installEventFilter(self)

            # centralWidget -> tabWidget -> manualnsert_tab -> keyboard
            # Navigation btns
            self.leftArrow_pushButton.clicked.connect(
                lambda: self.moveCursorLeft())
            self.rightArrow_pushButton.clicked.connect(
                lambda: self.moveCursorRight())
            # Numbers btns
            self.zero_pushButton.clicked.connect(
                lambda: self.insertSymbol('0'))
            self.one_pushButton.clicked.connect(lambda: self.insertSymbol('1'))
            self.two_pushButton.clicked.connect(lambda: self.insertSymbol('2'))
            self.three_pushButton.clicked.connect(
                lambda: self.insertSymbol('3'))
            self.four_pushButton.clicked.connect(
                lambda: self.insertSymbol('4'))
            self.five_pushButton.clicked.connect(
                lambda: self.insertSymbol('5'))
            self.six_pushButton.clicked.connect(lambda: self.insertSymbol('6'))
            self.seven_pushButton.clicked.connect(
                lambda: self.insertSymbol('7'))
            self.eight_pushButton.clicked.connect(
                lambda: self.insertSymbol('8'))
            self.nine_pushButton.clicked.connect(
                lambda: self.insertSymbol('9'))
            # Space btn
            self.space_pushButton.clicked.connect(
                lambda: self.insertSymbol(' '))
            # Slash btn
            self.slash_pushButton.clicked.connect(
                lambda: self.insertSymbol('/'))
            # Dash btn
            self.dash_pushButton.clicked.connect(
                lambda: self.insertSymbol('-'))
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
    focusedLine: QtWidgets.QLineEdit = None

    def eventFilter(self, obj, event):
        self.valid_inputs = (self.length_lineEdit,
                             self.quantity_lineEdit, self.ordrerId_lineEdit)
        if event.type() == QtCore.QEvent.FocusIn:
            if obj in self.valid_inputs:
                self.focusedLine = obj

        elif event.type() == QtCore.QEvent.FocusOut:
            self.focusedLine = None

        return super().eventFilter(obj, event)

    # Touchboard handler functions
    def insertSymbol(self, symbol: str):
        if self.focusedLine in self.valid_inputs:
            self.focusedLine.insert(symbol)

    def removeNumber(self):
        if self.focusedLine in self.valid_inputs:
            self.focusedLine.backspace()

    def moveCursorLeft(self):
        if self.focusedLine in self.valid_inputs:
            self.focusedLine.cursorBackward(0, 1)

    def moveCursorRight(self):
        if self.focusedLine in self.valid_inputs:
            self.focusedLine.cursorForward(0, 1)
    # Process

    # A function that dynamically validates length and quantity values. If values are correct then run_pushButton button is enabled.
    def checkInput(self):
        # The try-except statement is an additional safeguard in addition to QIntValidator against non-int input
        if self.length_lineEdit.text() != '':
            current_length = int(
                self.length_lineEdit.text().replace(' ', ''))
        else:
            current_length = 0

        if self.quantity_lineEdit.text() != '':
            current_quantity = int(
                self.quantity_lineEdit.text().replace(' ', ''))
        else:
            current_quantity = 0

        if current_length > self.min_len and current_quantity > 0:
            self.run_pushButton.setEnabled(True)
        else:
            self.run_pushButton.setEnabled(False)

    def runProccess(self):
        # Final check of length input
        if self.length_lineEdit.text() != '':
            length = int(
                self.length_lineEdit.text().replace(' ', ''))
        else:
            length = 0
        # Final check of quantity input
        if self.quantity_lineEdit.text() != '':
            quantity = int(
                self.quantity_lineEdit.text().replace(' ', ''))
        else:
            quantity = 0
        if (length > self.min_len) and (quantity > 0):

            self.winding_dialog = WindingInProgressDialog(
                parent_class=self.parent_class,
                ui_templates_dir=self.ui_templates_dir,
                machine_control=self.relay_mod, encoder=self.encoder,
                length_target=length, quantity_target=quantity
            )

            self.winding_dialog.rejected.connect(self.on_rejected)
            self.winding_dialog.accepted.connect(self.on_accepted)
            self.winding_dialog.exec_()
        else:
            self.run_pushButton.setDisabled(True)

    def on_accepted(self):
        del self.winding_dialog
        self.run_pushButton.setDisabled(True)
        self.length_lineEdit.setText("")
        self.quantity_lineEdit.setText("")

    def on_rejected(self):
        del self.winding_dialog
        print(self.winding_dialog)
        print("Process canceled and obj is deleted")
