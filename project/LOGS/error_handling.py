import os
from loguru import logger
from PyQt5 import QtWidgets, uic, QtGui
from buzzer import Buzzer


class ErrorDialog(QtWidgets.QDialog):

    def __init__(self, parent_class: QtWidgets.QMainWindow, error_title: str, eror_desc: str, buzzer: Buzzer):
        super().__init__()

        self.buzzer = buzzer
        self.error_title = error_title
        # Load template
        current_dir = os.getcwd()
        ui_templates_dir = os.path.join(current_dir, "project/ui_templates")
        uic.loadUi(os.path.join(
            ui_templates_dir, "error_dialog.ui"), self)
        self: QtWidgets.QDialog

        # Set window title
        self.setWindowTitle('Błąd maszyny')
        # Set window font
        self.setFont(QtGui.QFont("Tahoma", 24))

        # Configure errorTitle_label
        self.errorTitle_label: QtWidgets.QLabel
        font = QtGui.QFont(QtGui.QFont("Tahoma", 36))
        font.setBold(True)
        self.errorTitle_label.setFont(font)
        self.errorTitle_label.setText(f"!! {error_title} !!")
        self.errorTitle_label.setWordWrap(True)

        # Configure errorText_label
        self.errorText_label: QtWidgets.QLabel
        self.errorText_label.setText(eror_desc)
        self.errorText_label.setWordWrap(True)

        self.confirm_pushButton: QtWidgets.QPushButton
        self.confirm_pushButton.clicked.connect(self.__confirm_error)
        buzzer.signal('error')
        self.exec()

     # Configure confirm_pushButton
    def __confirm_error(self):
        logger.info(f"\"{self.error_title}\" - confirmed")
        self.buzzer.cancel_buzzer()
        self.accept()
