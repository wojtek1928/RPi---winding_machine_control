import os
from PyQt5 import uic
from loguru import logger
from PyQt5.QtWidgets import QDialog, QWidget, QSpinBox, QCheckBox, QPushButton

from settings.confirmation_alert import ConfirmationAlert
from settings.unsaved_alert import UnsavedChanges


class SettingsDialog(QDialog):

    def __init__(self, parent: QWidget, ui_templates_dir: str) -> None:
        super().__init__()

        self.ui_templates_dir = ui_templates_dir
        uic.loadUi(os.path.join(
            ui_templates_dir, "settings_dialog.ui"), self)

        # Assign current values from .env to fields

        #Printer
        self.checkBox_printLabels : QCheckBox
        self.checkBox_printLabels.setChecked(os.getenv("PRINT_LABELS", 'False') == 'True')

        self.checkBox_everyOtherRope : QCheckBox
        self.checkBox_everyOtherRope.setChecked(os.getenv("PRINT_LABEL_EVERY_OTHER_ROPE", 'False') == 'True')

        # Winding
        self.spinBox_startLength: QSpinBox
        self.spinBox_startLength.setValue(int(os.getenv("START_LENGHT")))
        
        self.spinBox_stopOffset: QSpinBox
        self.spinBox_stopOffset.setValue(int(os.getenv("STOP_OFFSET")))

        # Guillotine
        self.spinBox_downTime: QSpinBox
        self.spinBox_downTime.setValue(
            int(os.getenv("GUILLOTINE_DOWN_TIME")))

        self.spinBox_upTime: QSpinBox
        self.spinBox_upTime.setValue(int(os.getenv("GUILLOTINE_UP_TIME")))
        
        # Reset position 
        self.spinBox_searchTime: QSpinBox
        self.spinBox_searchTime.setValue(
            int(os.getenv("TIME_TO_SEARCH_FOR_ZERO")))
        # UI
        self.spinBox_confirmationTime: QSpinBox
        self.spinBox_confirmationTime.setValue(
            int(os.getenv("CONFIRM_NEW_LINE_TIME")))
        
        self.checkBox_buzzerSignals : QCheckBox
        self.checkBox_buzzerSignals.setChecked(os.getenv("BUZZER_SIGNALS", 'False') == 'True')

        # Assign action to pushButton_save
        self.pushButton_save: QPushButton
        self.pushButton_save.clicked.connect(self.confirmationAlert)

        # Assign action to pushButton_cancel
        self.pushButton_cancel: QPushButton
        self.pushButton_cancel.clicked.connect(self.onReject)

        # Define action on rejected settings_dialog
        self.rejected.connect(
            lambda: logger.info("Settings not saved"))

        self.showFullScreen()

    def onReject(self):
        """
        `reject` action is connet to this function in ui template
        """
        if self.get_changed_envs():
            unsaved_changes = UnsavedChanges(
                self,
                self.ui_templates_dir,
                self.get_changed_envs()
            )
            unsaved_changes.accepted.connect(self.reject)
            # Show settings_alert_dialog
            unsaved_changes.exec_()
        else:
            self.reject()

    def confirmationAlert(self):
        """
        Open `settings_alert_dialog`
        """
        if self.get_changed_envs():
            confirmation_alert = ConfirmationAlert(
                self,
                self.ui_templates_dir,
                self.get_changed_envs()
            )
            confirmation_alert.accepted.connect(
                lambda: self.save_changes(self.get_all_envs_with_changes()))
            # Show settings_alert_dialog
            confirmation_alert.exec_()

    def get_all_envs_with_changes(self):
        """
        Returns all environment variables with changes. NOT only those that changed.
        """
        # Set Current main file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Specify the name of the .env file
        self.env_file_path = os.path.join(os.path.dirname(current_dir), ".env")

        # Load the current environment variables from the .env file
        env_vars = {}
        with open(self.env_file_path, 'r') as env_file:
            for line in env_file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, value = line.split('=')
                env_vars[key] = value
        # Update values if changed
        # Update `PRINT_LABELS` value
        if (env_vars["PRINT_LABELS"] == 'True') != self.checkBox_printLabels.isChecked():
            env_vars['PRINT_LABELS'] = str(self.checkBox_printLabels.isChecked())
        # Update `PRINT_LABEL_EVERY_OTHER_ROPE` value
        if (env_vars["PRINT_LABEL_EVERY_OTHER_ROPE"] == 'True') != self.checkBox_everyOtherRope.isChecked():
            env_vars['PRINT_LABEL_EVERY_OTHER_ROPE'] = str(self.checkBox_everyOtherRope.isChecked())
        
        # Update `START_LENGHT` value
        if env_vars['START_LENGHT'] != self.spinBox_startLength.value():
            env_vars['START_LENGHT'] = str(self.spinBox_startLength.value())

        # Update `STOP_OFFSET` value
        if env_vars['STOP_OFFSET'] != self.spinBox_stopOffset.value():
            env_vars['STOP_OFFSET'] = str(self.spinBox_stopOffset.value())

        # Update `TIME_TO_SEARCH_FOR_ZERO` value
        if env_vars['TIME_TO_SEARCH_FOR_ZERO'] != self.spinBox_searchTime.value():
            env_vars['TIME_TO_SEARCH_FOR_ZERO'] = str(
                self.spinBox_searchTime.value())

        # Update `GUILLOTINE_DOWN_TIME` value
        if env_vars['GUILLOTINE_DOWN_TIME'] != self.spinBox_downTime.value():
            env_vars['GUILLOTINE_DOWN_TIME'] = str(
                self.spinBox_downTime.value())

        # Update `GUILLOTINE_UP_TIME` value
        if env_vars['GUILLOTINE_UP_TIME'] != self.spinBox_upTime.value():
            env_vars['GUILLOTINE_UP_TIME'] = str(
                self.spinBox_upTime.value())

        # Update `CONFIRM_NEW_LINE_TIME` value
        if env_vars['CONFIRM_NEW_LINE_TIME'] != self.spinBox_confirmationTime.value():
            env_vars['CONFIRM_NEW_LINE_TIME'] = str(
                self.spinBox_confirmationTime.value())

        # Update `BUZZER_SIGNALS` value
        if (env_vars["BUZZER_SIGNALS"] == 'True') != self.checkBox_buzzerSignals.isChecked():
            env_vars['BUZZER_SIGNALS'] = str(self.checkBox_buzzerSignals.isChecked())    
        
        return env_vars

    def get_changed_envs(self):
        """
        Get only changed envs
        """
        only_changed_envs = {}
        for key, value in self.get_all_envs_with_changes().items():
            if os.getenv(key) != value:
                only_changed_envs[key] = value
        return only_changed_envs

    def save_changes(self, updated_env_vars):
        """
        Write the updated environment variables back to the .env file and update currently loaded envs
        """
        with open(self.env_file_path, 'w') as env_file:
            for key, value in updated_env_vars.items():
                if os.getenv(key) != value:
                    logger.info(
                        f"{key} - changed: {os.getenv(key)} --> {value}")
                    os.environ[key] = value

                env_file.write(f'{key}={value}\n')

        self.accept()
