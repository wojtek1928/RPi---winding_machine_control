import os
from PyQt5.QtWidgets import QDialog, QWidget, QLabel, QDialogButtonBox
from PyQt5 import uic


class UnsavedChanges(QDialog):
    def __init__(self, parent: QWidget, ui_templates_dir: str, changed_envs: dict) -> None:
        super().__init__(parent)

        uic.loadUi(os.path.join(ui_templates_dir,
                   "settings_alert_dialog.ui"), self)

        # Set window title
        self.setWindowTitle("Ostrzeżenie o nie zapisaniu ustawień")
        # Set alert title
        self.label_title: QLabel
        self.label_title.setText(
            "Poniższe ustawienia nie zostaną zapisane.\n Czy na pewno chcesz wyjść z ustawień?")
        # Set alert description
        self.label_desc: QLabel
        description = ""
        for k, v in changed_envs.items():
            description += f"{k}: {v}\n"
        self.label_desc.setText(description)
        # Add buttons to buttonBox
        self.buttonBox: QDialogButtonBox
        self.buttonBox.addButton(QDialogButtonBox.Yes)
        self.buttonBox.addButton(QDialogButtonBox.No)
