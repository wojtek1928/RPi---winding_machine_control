import os
import time
import threading

from PyQt5.QtWidgets import QMainWindow,  QPushButton, QWidget
from PyQt5 import uic

from encoder import Encoder
from relay_module import RelayModule


class ManualSteeringTab(QWidget):
    def __init__(self, parent_class: QMainWindow, ui_templates_dir: str, relay_mod: RelayModule, encoder: Encoder):
        super().__init__()

        try:
            uic.loadUi(os.path.join(
                ui_templates_dir, "manual_steering_tab.ui"), self)

            self.relay_mod = relay_mod
            self.encoder = encoder
            self.parent_class = parent_class

            # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> clockwise_pushButton
            self.clockwise_pushButton: QPushButton
            self.clockwise_pushButton.clicked.connect(
                lambda: self.winder(self.clockwise_pushButton))
            # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> #centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> clockwise_pushButton
            self.counterClockwise_pushButton: QPushButton
            self.counterClockwise_pushButton.pressed.connect(
                lambda: relay_mod.winder_counter_clockwise(True))
            self.counterClockwise_pushButton.released.connect(
                lambda: relay_mod.winder_counter_clockwise(False))

            # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> #centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> stop_pushButton
            self.stop_pushButton: QPushButton
            self.clicked_winder_btn = self.stop_pushButton  # disabled by default
            self.stop_pushButton.clicked.connect(
                lambda: self.winder(self.stop_pushButton))
            # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> options_widget -> zeroPosition_pushButton
            self.zeroPosition_pushButton: QPushButton
            self.zeroPosition_pushButton.clicked.connect(
                self.winder_zero_position)

            # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> options_widget -> guillotine_pushButton
            self.guillotine_pushButton: QPushButton
            self.guillotine_pushButton.pressed.connect(
                lambda: relay_mod.guillotine_press(True))
            self.guillotine_pushButton.released.connect(
                lambda: relay_mod.guillotine_press(False))

            # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> #centralWidget -> tabWidget -> manuaSteering_tab -> lengthMeasurement_frame -> startMeasurement_pushButton
            self.startMeasurement_pushButton.clicked.connect(
                lambda: self.measurement(self.startMeasurement_pushButton))
            # centralWidget -> tabWidget -> manuaSteering_tab -> winder_frame -> #centralWidget -> tabWidget -> manuaSteering_tab -> lengthMeasurement_frame -> startMeasurement_pushButton
            self.reset_pushButton.clicked.connect(self.measurement_reset)

            # Add element to parent class
            parent_class.tabWidget.addTab(self, "Sterowanie ręczne")

        except Exception as e:
            print("Module ManualSteeringTab initialization failed.", e, sep='\n')

    def winder(self, button: QPushButton):
        if button.objectName() == "clockwise_pushButton":
            # Diasable buttons for safety reasons
            self.activate_winder_buttons(False)
            # Start winding
            self.relay_mod.winder_clockwise()
            self.stop_pushButton.setEnabled(True)
        elif button.objectName() == "stop_pushButton":
            # Enalbe buttons previous disabled buttons
            self.activate_winder_buttons(True)
            self.relay_mod.winder_STOP()
            self.clockwise_pushButton.setEnabled(True)
            self.counterClockwise_pushButton.setEnabled(True)

    def winder_zero_position(self):
        self.activate_winder_buttons(False)
        self.relay_mod.winder_reset_position(self.activate_winder_buttons)

    def activate_winder_buttons(self, state: bool):
        # Making sure that encoder measurement is inactive and measured distance is equa to 0
        if state and not self.encoder.is_measurement_active() and self.encoder.__int__() == 0:
            self.parent_class.enableMainWindow(
                self.parent_class.tabWidget.currentIndex(), state)
        else:
            self.parent_class.enableMainWindow(
                self.parent_class.tabWidget.currentIndex(), False)
        self.clockwise_pushButton.setEnabled(state)
        self.counterClockwise_pushButton.setEnabled(state)
        self.zeroPosition_pushButton.setEnabled(state)
        self.guillotine_pushButton.setEnabled(state)

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
        if not self.encoder.is_measurement_active() and not self.relay_mod.get_winder_status():
            self.parent_class.enableMainWindow(
                self.parent_class.tabWidget.currentIndex(), True)
        # Display new value
        self.length_lcdNumber.display(self.encoder.__int__())
