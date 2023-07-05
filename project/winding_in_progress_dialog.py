import os
import time
import threading
import typing

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5 import uic
from PyQt5.QtWidgets import QWidget

from encoder import Encoder
from relay_module import RelayModule
from stopwatch import Stopwatch


class WindingInProgressDialog(QtWidgets.QDialog):

    __STATES = ("working", "paused", "cancelling", "done", "end")
    __current_state: str

    def __init__(self, parent_class: QtWidgets.QMainWindow, ui_templates_dir: str, relay_mod: RelayModule, encoder: Encoder, length_taget: int, quantity_target: int):
        super().__init__()

        try:
            self.__relay_mod = relay_mod
            self.__encoder = encoder
            self.__length_target = length_taget
            self.__quantity_target = quantity_target

            uic.loadUi(os.path.join(
                ui_templates_dir, "winding_in_progress_dialog.ui"), self)

            # Overwrite default fontsize for dialog
            self.setFont(QtGui.QFont("Tahoma", 24))
            # Display dialog in full screen mode
            self.showFullScreen()

            # Assign types and events handlers to elements
            # Alert label - handles the displaying messages to user
            self.alert_label: QtWidgets.QLabel

            # Cancel pushButton suppports the canceling of the winding process
            self.cancel_pushButton: QtWidgets.QPushButton
            self.cancel_pushButton.setFont(QtGui.QFont("Tahoma", 30))
            self.cancel_pushButton.clicked.connect(
                lambda: self.cancel_pushButton_event())

            # action pushbutonn handling thediffrent actions depeds on situation
            self.action_pushButton: QtWidgets.QPushButton
            self.action_pushButton.setFont(QtGui.QFont("Tahoma", 30))
            self.action_pushButton.clicked.connect(
                lambda: self.action_pushButton_event())

            # timeVal_label displays time since begin of the winding process
            self.timeVal_label: QtWidgets.QLabel
            self.timeVal_label.setFont(QtGui.QFont("Tahoma", 24))

            # progressVal_label displays the currently wound rope
            self.progressVal_label: QtWidgets.QLabel
            self.progressVal_label.setFont(QtGui.QFont("Tahoma", 24))

            # lengthVal_label displays the current length of the wound rope
            self.lengthVal_label: QtWidgets.QLabel
            self.lengthVal_label.setFont(QtGui.QFont("Tahoma", 24))

            # Set stopwatch object
            self.__runtime = Stopwatch()
            self.__wound_ropes = 0
            self.__wound_lenght = 0

            self.__current_state = self.__STATES[0]

            # Run the monitoring thread
            self.display_thread = threading.Thread(
                target=self.__monitoring_fcn, daemon=True)
            self.display_thread.start()

            # Run proccess
            self.run()

        except Exception as e:
            print("Module WindingInProgressDialog initialization failed.", e, sep='\n')

    def run(self):
        self.__current_state = self.__STATES[0]
        # Run time measurement
        self.__runtime.run()
        # Run encoder measurement
        self.__encoder.begin_measurement()
        # Run winder motor
        self.__relay_mod.winder_clockwise()

    def pause(self):
        self.__current_state = self.__STATES[1]
        self.__relay_mod.winder_STOP()
        self.__runtime.pause()

    def next_rope(self):
        self.__current_state = self.__STATES[3]
        # Stop winder
        self.__relay_mod.winder_STOP()
        #Stop and reset encoder
        self.__encoder.pause_measurement()
        self.__encoder.reset_measurement()
        # Cut the rope
        self.alert_label.setText("Ucinanie linki...")
        self.__relay_mod.guillotine_press(True)
        time.sleep(1)
        self.__relay_mod.guillotine_press(False)
        # Reset winder to zero position
        self.alert_label.setText("Bęben wraca do punktu zero...")
        self.__relay_mod.winder_reset_position()
        # Wait for winder
        self.__relay_mod.reset_event.wait()
        # Display progress
        self.progressVal_label.setText(
                f"{self.__wound_ropes}/{self.__quantity_target}")

        self.__wound_ropes += 1
        
        if self.__wound_ropes == self.__quantity_target:
                self.end()
        else:
            self.action_pushButton.setText("Następna linka")
            self.alert_label.setText("Sterowanie zaciskarką zostało odblokowane,\n przygoytuj następną linkę.\n\nGdy będziesz gotowy/a przytrzymaj przycisk \nwznowienia.")

    def end(self):
        self.__current_state = self.__STATES[4]
        self.cancel_pushButton.setDisabled(True)
        self.alert_label.setText("Zlecenie zostało ukończone.")
        self.action_pushButton.setStyleSheet(
                "background-color: #00aa00; color: white;")
        self.action_pushButton.setText("Zakończ")

    def __monitoring_fcn(self):
        while True:

            # Display current time on screen
            self.timeVal_label.setText(self.__runtime.__str__())
            # Display number of wound ropes
            self.progressVal_label.setText(
                f"{self.__wound_ropes}/{self.__quantity_target}")
            # Display lenght of wound rope
            self.lengthVal_label.setText(self.__encoder.__str__())
             
            # Check condition
            if self.__wound_ropes == self.__quantity_target:
                self.end()

            elif self.__encoder.__int__() >= self.__length_target:
                self.next_rope()
                

            time.sleep(0.01)

    # Function which handling clicked event of cancel_pushButton
    def cancel_pushButton_event(self):
        if self.__current_state == "working" or self.__current_state == "paused" or self.__current_state == "done":
            self.pause()
            # Switch state to cancelling
            self.__current_state = self.__STATES[2]
            # Display message to user
            self.alert_label.setText(
                "Czy na pewno chcesz anulować obecne zadanie?")
            # Change action button text and color
            self.action_pushButton.setText("Tak")
            self.action_pushButton.style
            self.action_pushButton.setStyleSheet(
                "background-color: #aa0000; color: white;")
            # Change cancel button text and color
            self.cancel_pushButton.setText("Nie")
            self.cancel_pushButton.setStyleSheet(
                "background-color: #00aa00; color: white;")

        elif self.__current_state == "cancelling":
            self.__current_state = self.__STATES[1]
            # Remove message to user
            self.alert_label.setText("")
            # Change action button text and color
            self.action_pushButton.setText("Wznów")
            self.action_pushButton.setStyleSheet(
                "background-color: #ffaa00; color: white;")
            # Change cancel button text and color
            self.cancel_pushButton.setText("Anuluj")
            self.cancel_pushButton.setStyleSheet(
                "background-color: #aa0000; color: white;")

    # Function which handling clicked event of action_pushButton
    def action_pushButton_event(self):
        if self.__current_state == "working":
            self.pause()
            self.action_pushButton.setText("Wznów")

        elif self.__current_state == "paused":
            self.run()
            self.action_pushButton.setText("Zatrzymaj")

        elif self.__current_state == "cancelling":
            self.reject()
        elif self.__current_state == "done":
            self.alert_label.setText("")
            self.action_pushButton.setText("Zatrzymaj")
            self.run()
        elif self.__current_state == 'end':
            self.accept()
            
