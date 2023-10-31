import os
import time
import threading
from functools import partial
from loguru import logger
from PyQt5.QtWidgets import QMainWindow,  QPushButton, QWidget
from PyQt5 import uic, QtCore

from encoder import Encoder
from machine_control import MachineControl, Actions, MachineWorker
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

    def winder_STOP(self):
        # Disable button for execution time
        self.stop_pushButton.setDisabled(True)
        # Thread definition
        action = Actions.winder_STOP
        pool = QtCore.QThreadPool.globalInstance()
        worker = MachineWorker(self.machine_control, action)
        # Done signal handling
        worker.signals.done.connect(self.unlockUIAfterExecution)
        # Error signal handling
        worker.signals.error_signal.connect(self.alert)
        # Set action on thread start
        worker.signals.started.connect(worker.run)
        # Start thread
        pool.start(worker)

    def winder_clockwise_ex(self):
        # Disable buttons
        self.setMainWindowEnabled(False)
        self.clockwise_pushButton.setDisabled(True)
        self.counterClockwise_pushButton.setDisabled(True)
        self.zeroPosition_pushButton.setDisabled(True)
        self.guillotine_pushButton.setDisabled(True)
        # Thread definition
        action = Actions.winder_clockwise
        pool = QtCore.QThreadPool.globalInstance()
        worker = MachineWorker(self.machine_control, action)
        # Done signal handling
        # Error signal handling
        worker.signals.error_signal.connect(self.unlockUIAfterExecution)
        # Set action on thread start
        worker.signals.started.connect(worker.run)
        # Start thread
        pool.start(worker)

    def unlockUIAfterExecution(self, err_title: str = None, err_desc: str = None):
        self.setMainWindowEnabled(True)
        self.stop_pushButton.setEnabled(True)
        self.clockwise_pushButton.setEnabled(True)
        self.counterClockwise_pushButton.setEnabled(True)
        self.zeroPosition_pushButton.setEnabled(True)
        self.guillotine_pushButton.setEnabled(True)
        if err_title is not None:
            self.alert(err_title, err_desc)

    def winder_reset_position_ex(self):
        # Disable buttons
        self.setMainWindowEnabled(False)
        self.clockwise_pushButton.setDisabled(True)
        self.counterClockwise_pushButton.setDisabled(True)
        self.zeroPosition_pushButton.setDisabled(True)
        self.guillotine_pushButton.setDisabled(True)

        # Thread definition
        action = Actions.winder_reset_position
        pool = QtCore.QThreadPool.globalInstance()
        worker = MachineWorker(self.machine_control, action)
        # Done signal handling
        worker.signals.done.connect(self.unlockUIAfterExecution)
        worker.signals.optional.connect(self.unlockUIAfterExecution)
        # Error signal handling
        worker.signals.error_signal.connect(self.unlockUIAfterExecution)
        # Set action on thread start
        worker.signals.started.connect(worker.run)
        # Start thread
        pool.start(worker)

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
