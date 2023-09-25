import os
import time
import threading
from functools import partial
from loguru import logger
from PyQt5.QtWidgets import QMainWindow,  QPushButton, QWidget
from PyQt5 import uic, QtCore

from encoder import Encoder
from machine_control import MachineControl, Actions
from winder_control import WinderThread
from LOGS.error_handling import ErrorDialog


class ManualSteeringTab(QWidget):
    def __init__(self, parent_class: QMainWindow, ui_templates_dir: str, machine_control: MachineControl, encoder: Encoder, pi, buzzer):
        super().__init__()
        try:
            uic.loadUi(os.path.join(
                ui_templates_dir, "manual_steering_tab.ui"), self)

            self.machine_control = machine_control
            self.encoder = encoder
            self.parent_class = parent_class
            self.pi = pi
            self.buzzer = buzzer

            # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> clockwise_pushButton
            self.clockwise_pushButton: QPushButton
            self.clockwise_pushButton.clicked.connect(self.winder_clockwise_ex)
            # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> #centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> clockwise_pushButton
            self.counterClockwise_pushButton: QPushButton
            self.counterClockwise_pushButton.pressed.connect(
                partial(self.machine_control.execute, Actions.winder_counter_clockwise, True))
            self.counterClockwise_pushButton.released.connect(
                partial(self.machine_control.execute, Actions.winder_counter_clockwise, False))

            # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> #centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> stop_pushButton
            self.stop_pushButton: QPushButton
            self.clicked_winder_btn = self.stop_pushButton  # disabled by default
            self.stop_pushButton.clicked.connect(self.winder_STOP)
            # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> options_widget -> zeroPosition_pushButton
            self.zeroPosition_pushButton: QPushButton
            self.zeroPosition_pushButton.clicked.connect(
                self.winder_reset_position_ex)

            # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> options_widget -> guillotine_pushButton
            self.guillotine_pushButton: QPushButton
            self.guillotine_pushButton.pressed.connect(
                partial(machine_control.execute, Actions.guillotine_press, True))
            self.guillotine_pushButton.released.connect(
                partial(machine_control.execute, Actions.guillotine_press, False))

            # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> #centralWidget -> tabWidget -> manuaSteering_tab -> lengthMeasurement_frame -> startMeasurement_pushButton
            self.startMeasurement_pushButton.clicked.connect(
                lambda: self.measurement(self.startMeasurement_pushButton))
            # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> #centralWidget -> tabWidget -> manuaSteering_tab -> lengthMeasurement_frame -> startMeasurement_pushButton
            self.reset_pushButton.clicked.connect(self.measurement_reset)

            # Add element to parent class
            parent_class.tabWidget.addTab(self, "Sterowanie ręczne")

        except Exception as e:
            print("Module ManualSteeringTab initialization failed.", e, sep='\n')

    def alert(self, err_title, err_desc):
        ErrorDialog(self.parent_class, err_title, err_desc, self.buzzer)

    def winder_reset_position_ex(self):
        # Disable buttons
        self.setMainWindowEnabled(False)
        self.clockwise_pushButton.setDisabled(True)
        self.counterClockwise_pushButton.setDisabled(True)
        self.zeroPosition_pushButton.setDisabled(True)
        self.guillotine_pushButton.setDisabled(True)
        # Execute action
        self.__executor(Actions.winder_reset_position)

    def winder_clockwise_ex(self):
        # Disable buttons
        self.setMainWindowEnabled(False)
        self.clockwise_pushButton.setDisabled(True)
        self.counterClockwise_pushButton.setDisabled(True)
        self.zeroPosition_pushButton.setDisabled(True)
        self.guillotine_pushButton.setDisabled(True)
        # Execute action
        self.__executor(Actions.winder_clockwise)

    def afterExecution(self, action: Actions):
        self.winder_ex_thread.deleteLater()
        del self.winder_ex_thread
        del self.MC_worker

        # Enable buttons automatic if motor is stopped
        if not self.machine_control.is_motor_on():
            self.setMainWindowEnabled(True)
            self.clockwise_pushButton.setEnabled(True)
            self.counterClockwise_pushButton.setEnabled(True)
            self.zeroPosition_pushButton.setEnabled(True)
            self.guillotine_pushButton.setEnabled(True)

    def __executor(self, action: Actions, *args):
        # Check if self.winder_thread is already running before creating a new thread
        if not hasattr(self, 'winder_ex_thread'):
            # Thread definition
            self.winder_ex_thread = QtCore.QThread()
            self.MC_worker = MachineControl(self.pi, self.buzzer)
            self.MC_worker.moveToThread(self.winder_ex_thread)
            # Done signal handling
            self.MC_worker.done.connect(self.winder_ex_thread.quit)
            self.MC_worker.done.connect(self.MC_worker.deleteLater)
            # Error signal handling
            self.MC_worker.error_signal.connect(self.alert)
            # Thread finished handling
            self.winder_ex_thread.finished.connect(
                partial(self.afterExecution, action))
            # Set action on thread start
            self.winder_ex_thread.started.connect(
                partial(self.MC_worker.execute, action, *args)
            )
            # Start thread
            self.winder_ex_thread.start()

    def afterSTOPExecution(self):
        self.winder_STOP_thread.deleteLater()
        self.winder_STOP_thread.wait(100)
        del self.winder_STOP_thread
        del self.STOP_worker
        # Enable previous disabled buttons
        self.setMainWindowEnabled(True)
        self.stop_pushButton.setEnabled(True)
        self.clockwise_pushButton.setEnabled(True)
        self.counterClockwise_pushButton.setEnabled(True)
        self.zeroPosition_pushButton.setEnabled(True)
        self.guillotine_pushButton.setEnabled(True)

    def winder_STOP(self):
        # Check if self.winder_thread is already running before creating a new thread
        if not hasattr(self, 'winder_STOP_thread'):
            # Thread definition
            self.winder_STOP_thread = QtCore.QThread()
            self.STOP_worker = MachineControl(self.pi, self.buzzer)
            self.STOP_worker.moveToThread(self.winder_STOP_thread)
            # Done signal handling
            self.STOP_worker.done.connect(self.winder_STOP_thread.quit)
            self.STOP_worker.done.connect(self.STOP_worker.deleteLater)
            # Error signal handling
            self.STOP_worker.error_signal.connect(self.alert)
            # Thread finished handling
            self.winder_STOP_thread.finished.connect(self.afterSTOPExecution)
            # Set action on thread start
            self.winder_STOP_thread.started.connect(
                partial(self.STOP_worker.winder_STOP, direct_execution=True))
            # Start thread
            self.stop_pushButton.setDisabled(True)
            self.winder_STOP_thread.start()

    def setMainWindowEnabled(self, should_be_active: bool):
        # Making sure that encoder measurement is inactive and measured distance is equal to 0
        if (
            should_be_active
            and not self.machine_control.is_motor_on()
            and not self.encoder.is_measurement_active()
            and self.encoder.__int__() == 0
        ):
            self.parent_class.enableMainWindow(
                self.parent_class.tabWidget.currentIndex(), True)
        else:
            self.parent_class.enableMainWindow(
                self.parent_class.tabWidget.currentIndex(), False)

    # Measurement handlers

    def display_current_value(self):
        self.is_displaying = True
        while self.is_displaying:
            self.length_lcdNumber.display(self.encoder.__int__())
            time.sleep(0.01)

    def measurement(self, QButton: QPushButton):
        if QButton.text() == "Pomiar - start":
            self.parent_class.enableMainWindow(
                self.parent_class.tabWidget.currentIndex(), False)
            QButton.setText("Pomiar - stop")
            self.encoder.begin_measurement()
            LCD_display_thread = threading.Thread(
                target=self.display_current_value, daemon=True)
            LCD_display_thread.start()

        elif QButton.text() == "Pomiar - stop":
            QButton.setText("Pomiar - start")
            self.encoder.pause_measurement()
            self.is_displaying = False

    def measurement_reset(self):
        self.encoder.reset_measurement()
        # Making sure that measurement is not active and winder is not running bfere unnlocing the menu and other tabs
        if not self.encoder.is_measurement_active() and not self.machine_control.get_winder_status():
            self.parent_class.enableMainWindow(
                self.parent_class.tabWidget.currentIndex(), True)
        # Display new value
        self.length_lcdNumber.display(self.encoder.__int__())
