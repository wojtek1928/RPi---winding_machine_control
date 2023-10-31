import os
from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets
from PyQt5 import uic
from loguru import logger

from encoder import Encoder
from buzzer import Buzzer
from machine_control import MachineControl, MachineWorker
from LOGS.error_handling import ErrorDialog
from winding_in_progres import WindingInProgressDialog


class ManualInsertingTab(QtWidgets.QWidget):
    def __init__(self, parent_class: QtWidgets.QMainWindow, ui_templates_dir: str, machine_control: MachineControl, encoder: Encoder, buzzer: Buzzer):
        super().__init__()

        try:
            uic.loadUi(os.path.join(
                ui_templates_dir, "manual_insert_tab.ui"), self)

            self.machine_control = machine_control
            self.encoder = encoder
            self.buzzer = buzzer
            self.parent_class = parent_class
            self.ui_templates_dir = ui_templates_dir

            # Assign types and events handlers to elements
            # centralWidget -> tabWidget -> manualnsert_tab -> lenghth_lineEdit
            self.length_lineEdit: QtWidgets.QLineEdit
            self.length_lineEdit.setValidator(QtGui.QIntValidator(0, 1000000))
            self.length_lineEdit.installEventFilter(self)
            self.length_lineEdit.textChanged.connect(self.check_input)

            # centralWidget -> tabWidget -> manualnsert_tab -> diameter_lineEdit
            self.diameter_lineEdit: QtWidgets.QLineEdit
            self.diameter_lineEdit.setValidator(
                QtGui.QDoubleValidator(1.0, 10.0, 1))
            self.diameter_lineEdit.installEventFilter(self)
            self.diameter_lineEdit.textChanged.connect(self.check_input)

            # centralWidget -> tabWidget -> manualnsert_tab -> quantity_lineEdit
            self.quantity_lineEdit: QtWidgets.QLineEdit
            self.quantity_lineEdit.setValidator(
                QtGui.QIntValidator(0, 99, self))
            self.quantity_lineEdit.installEventFilter(self)
            self.quantity_lineEdit.textChanged.connect(self.check_input)

            # centralWidget -> tabWidget -> manualnsert_tab -> ordrerId_lineEdit
            self.ordrerId_lineEdit: QtWidgets.QLineEdit
            order_id_regex = QtCore.QRegularExpression(
                r"^\d{6}/\d{2}/\d{4}/\d/\d$")
            self.ordrerId_lineEdit.setValidator(
                QtGui.QRegularExpressionValidator(order_id_regex))
            self.ordrerId_lineEdit.installEventFilter(self)
            self.ordrerId_lineEdit.textChanged.connect(self.check_input)

            # centralWidget -> tabWidget -> manualnsert_tab -> keyboard
            # Navigation btns
            self.leftArrow_pushButton.clicked.connect(
                lambda: self.moveCursorLeft())
            self.rightArrow_pushButton.clicked.connect(
                lambda: self.moveCursorRight())
            self.tab_pushButton.clicked.connect(
                lambda: self.form_widget.focusNextChild())
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
            # Comma btn
            self.comma_pushButton.clicked.connect(
                lambda: self.insertSymbol(','))
            # Slash btn
            self.slash_pushButton.clicked.connect(
                lambda: self.insertSymbol('/'))
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
        self.valid_inputs = (
            self.length_lineEdit,
            self.diameter_lineEdit,
            self.quantity_lineEdit,
            self.ordrerId_lineEdit
        )
        if event.type() == QtCore.QEvent.FocusIn:
            if obj in self.valid_inputs:
                self.focusedLine = obj

        elif event.type() == QtCore.QEvent.FocusOut:
            self.focusedLine = None

        return super().eventFilter(obj, event)

    # Alert handlingfunction
    def alert(self, err_title, err_desc):
        ErrorDialog(self.parent_class, err_title, err_desc, self.buzzer)

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
    def check_input(self):
        parsed_length = self.length_lineEdit.text().replace(' ', '')
        parsed_diameter = self.diameter_lineEdit.text().replace(' ', '')
        parsed_quantity = self.quantity_lineEdit.text().replace(' ', '')
        if len(parsed_length) > 0 and len(parsed_quantity) > 0 and len(parsed_diameter) > 0:
            length_valid: bool = int(parsed_length) > int(
                os.getenv('START_LENGHT')) and self.length_lineEdit.hasAcceptableInput()
            diameter_valid: bool = self.diameter_lineEdit.hasAcceptableInput()
            quantity_valid: bool = self.quantity_lineEdit.hasAcceptableInput()
            order_number_valid: bool = True   # self.ordrerId_lineEdit.hasAcceptableInput()
            if length_valid and quantity_valid and order_number_valid and diameter_valid:
                self.run_pushButton.setEnabled(True)
                return True
            else:
                self.run_pushButton.setEnabled(False)
                return False
        else:
            self.run_pushButton.setEnabled(False)
            return False

    def runProccess(self):
        # Final check input check
        if not self.check_input():
            self.alert("Błędne dane wejściowe",
                       "Wprowadzone dane nie są poprawne.")
            logger.error("Wrong input data")
            return
        if self.machine_control.is_motor_on():
            self.alert("Maszyna jest w ruchu.",
                       "Wyłącz silnik nawijarki przed rozpoczęciem.")
            logger.error("The machine was running before")
            return
        if not self.machine_control.is_in_zero_positon():
            self.alert("Bęben wyciągarki jest w złej pozycji",
                       "Przywróć bęben do pozycji zerowej.\n PAMIĘTAJ O ODCZEPIENIU LINKI OD BĘBNA PRZED PRZYWRACANIEM.")
            logger.error("Winder drum is in bad position")
            return
        length = int(self.length_lineEdit.text().replace(" ", ''))
        quantity = int(self.quantity_lineEdit.text().replace(" ", ''))
        diameter = float(self.diameter_lineEdit.text().replace(
            " ", "").replace(",", "."))
        order_id = self.ordrerId_lineEdit.text().replace(" ", "")
        logger.success(
            "Successfully run `winding_in_progress` by 'tab_manual_winding'")
        self.winding_dialog = WindingInProgressDialog(
            parent_class=self.parent_class,
            ui_templates_dir=self.ui_templates_dir,
            machine_control=self.machine_control,
            buzzer=self.buzzer,
            encoder=self.encoder,
            length_target=length,
            quantity_target=quantity,
            diameter=diameter,
            order_id=order_id
        )

        self.winding_dialog.rejected.connect(self.on_rejected)
        self.winding_dialog.accepted.connect(self.on_accepted)
        self.winding_dialog.exec_()

    def on_accepted(self):
        logger.success("Successfully done `winding_in_progres` dialog process")
        del self.winding_dialog
        self.run_pushButton.setDisabled(True)
        self.length_lineEdit.setText("")
        self.diameter_lineEdit.setText("")
        self.quantity_lineEdit.setText("")
        self.ordrerId_lineEdit.setText("")

    def on_rejected(self):
        logger.warning(
            "Done before the expected ending, `winding_in_progres` dialog process")
        del self.winding_dialog
        print("Process canceled and obj is deleted")

    