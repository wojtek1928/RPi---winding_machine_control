import os
from loguru import logger
from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtCore import Qt
from buzzer import Buzzer


class ErrorDialog(QtWidgets.QDialog):

    def __init__(self, parent_class: QtWidgets.QMainWindow, error_title: str, eror_desc: str, buzzer: Buzzer, printer_error: bool = False):
        super().__init__()

        self.buzzer = buzzer
        self.error_title = error_title
        # Load template
        current_dir = os.getcwd()
        ui_templates_dir = os.path.join(current_dir, "project/ui_templates")
        uic.loadUi(os.path.join(
            ui_templates_dir, "error_dialog.ui"), self)
        self: QtWidgets.QDialog
        
        # Make sure that Taskbar is hidden
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # Make sure that curosor is hidden
        self.setCursor(Qt.BlankCursor)

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

        # Configure confirm_pushButton
        self.confirm_pushButton: QtWidgets.QPushButton
        self.confirm_pushButton.clicked.connect(self.__confirm_error)

        # Configure retry_pushButton
        self.retry_pushButton: QtWidgets.QPushButton
        if not printer_error:
            self.retry_pushButton.hide()
        else:
            self.confirm_pushButton.setText("Kontynuuj bez etykiety")
            self.retry_pushButton.clicked.connect(self.__retry)

        # Activate buzzer signal
        buzzer.signal('error')

    # Handle clicked event for confirm_pushButton
    def __confirm_error(self):
        logger.info(f"\"{self.error_title}\" - confirmed")
        self.buzzer.cancel_buzzer()
        self.accept()

     # Handle clicked event for retry_pushButton
    def __retry(self):
        logger.info(f"\"{self.error_title}\" - printing retry")
        self.buzzer.cancel_buzzer()
        self.reject()
