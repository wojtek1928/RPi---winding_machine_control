import os
from PyQt5.QtWidgets import QDialog, QWidget, QLabel, QDialogButtonBox
from PyQt5 import uic
from PyQt5.QtCore import Qt

from orders.order import Order


class ConfirmationDONERun(QDialog):
    def __init__(self, parent: QWidget, ui_templates_dir: str, order: Order) -> None:
        super().__init__(parent)

        uic.loadUi(os.path.join(ui_templates_dir,
                   "settings_alert_dialog.ui"), self)
        # Make sure that Taskbar is hidden
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() |
                            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # Make sure that curosor is hidden
        self.setCursor(Qt.BlankCursor)

        # Set window title
        self.setWindowTitle("Potwierdzenie ponownego wykonania")
        # Set alert title
        self.label_title: QLabel
        self.label_title.setText(
            "Czy napewno chcesz ponownie wykonać zlecenie?")
        # Set alert description
        self.label_desc: QLabel
        self.label_desc.setText(order.__str__())
        # Add buttons to buttonBox
        self.buttonBox: QDialogButtonBox
        yes_btn = self.buttonBox.addButton(QDialogButtonBox.Yes)
        no_btn = self.buttonBox.addButton(QDialogButtonBox.No)
        # Set custom text for the buttons
        yes_btn.setText("Tak")
        no_btn.setText("Nie")
