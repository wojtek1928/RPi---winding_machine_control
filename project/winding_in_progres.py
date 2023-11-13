from enum import Enum
import os
import time
from datetime import datetime
from functools import partial
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5 import uic
from loguru import logger

from encoder import Encoder
from LOGS.error_handling import ErrorDialog
from machine_control import MachineControl, Actions, MachineWorker
from stopwatch import Stopwatch
from buzzer import Buzzer
from winding_in_progress_operations.next_rope import NextRope
from winding_in_progress_operations.monitor import MonitorProcess
from winding_in_progress_operations.states import STATES
from label_printing.print import ZebraPrinter


class BTN(Enum):
    first = 1
    second = 2


class WindingInProgressDialog(QtWidgets.QDialog):
    __current_state: STATES = None
    __previous_state: STATES
    # Flag for blocking buttons in case of unexpected rope pulling
    __block__buttons: bool = False
    # Stores STATE which was paused or canceled as target to which should be set after continuing or canceling termination.
    __paused_state: STATES = None
    # Flag that prevents length condition multiple activation
    __rope_lenght_accepted: bool = False

    def __init__(
            self, parent_class: QtWidgets.QMainWindow,
            ui_templates_dir: str,
            machine_control: MachineControl,
            encoder: Encoder,
            buzzer: Buzzer,
            length_target: int,
            quantity_target: int,
            diameter: float,
            order_id: str,
            customer_name: str = ""
    ):
        super().__init__()

        try:
            self.__machine_control: MachineControl = machine_control
            self.__encoder: Encoder = encoder
            self.__buzzer = buzzer
            self.__parent_class = parent_class
            self.__length_target = length_target
            self.__quantity_target = quantity_target
            self.__diameter = diameter
            self.order_id = order_id
            self.__customer_name = customer_name

            uic.loadUi(os.path.join(
                ui_templates_dir, "winding_in_progress_dialog.ui"), self)

            # Assign types and events handlers to elements
            # Info label - handles the displaying messages to user
            self.info_label: QtWidgets.QLabel

            # First pushbutonn handling the diffrent actions depeds on situation
            self.first_pushButton: QtWidgets.QPushButton
            self.first_pushButton.setFont(QtGui.QFont("Tahoma", 30))
            self.first_pushButton.clicked.connect(
                partial(self.__first_btn_fcn, "clicked"))
            # Only for confirmation function which checks holding button
            self.first_pushButton.pressed.connect(
                partial(self.__first_btn_fcn, "pressed"))
            self.__next_rope_confirmed = False
            self.__confirmation_started = False

            # Second pushbutonn handling the diffrent actions depeds on situation
            self.second_pushButton: QtWidgets.QPushButton
            self.second_pushButton.setFont(QtGui.QFont("Tahoma", 30))
            self.second_pushButton.clicked.connect(self.__second_btn_fcn)

            # `pushButton_resetAgain` handling the `__set_resetPosition_state` actions only on `wait_for_next_state`
            self.pushButton_resetAgain: QtWidgets.QPushButton
            self.pushButton_resetAgain.setHidden(True)
            self.pushButton_resetAgain.setFont(QtGui.QFont("Tahoma", 30))
            self.pushButton_resetAgain.clicked.connect(
                partial(self.__set_resetPosition_state, False))

            # orderIdVal_label displays time since begin of the winding process
            self.orderIdVal_label: QtWidgets.QLabel
            self.orderIdVal_label.setFont(QtGui.QFont("Tahoma", 24))
            self.orderIdVal_label.setText(self.order_id)

            # timeVal_label displays time since begin of the winding process
            self.timeVal_label: QtWidgets.QLabel
            self.timeVal_label.setFont(QtGui.QFont("Tahoma", 24))

            # progressVal_label displays the currently wound rope
            self.progressVal_label: QtWidgets.QLabel
            self.progressVal_label.setFont(QtGui.QFont("Tahoma", 24))
            self.progressVal_label.setText(f"0 / {self.__quantity_target}")

            # lengthVal_label displays the current length of the wound rope
            self.lengthVal_label: QtWidgets.QLabel
            self.lengthVal_label.setFont(QtGui.QFont("Tahoma", 24))

            # Overwrite default fontsize for dialog
            self.setFont(QtGui.QFont("Tahoma", 24))
            # Display dialog in full screen mode
            self.showFullScreen()

            # Set stopwatch object
            self.__runtime = Stopwatch()
            self.__quantity_current = 0
            self.initial_run()
        except Exception as e:
            print("Module WindingInProgressDialog initialization failed.", e, sep='\n')

    # Alert handlingfunction
    def alert(self, err_title, err_desc):
        self.__buzzer.cancel_buzzer()
        logger.error(err_title)
        alert = ErrorDialog(self.__parent_class, err_title,
                            err_desc, self.__buzzer)
        alert.exec()

    def set_states(self, new_state: STATES):
        if new_state != self.__current_state:
            self.__previous_state = self.__current_state
            self.__current_state = new_state
            logger.info(
                f"STATE change: {self.__previous_state} ---> {self.__current_state}")

    def set_info_label(self, message: str, text_color: str):
        self.info_label.setText(message)
        self.info_label.setStyleSheet(f"color: {text_color};")

    def set_button(self, btn: BTN, text: str, bg_color: str, text_color: str = "white"):
        if btn == BTN.first:
            self.first_pushButton.setText(text)
            self.first_pushButton.setStyleSheet(
                f"background-color: {bg_color}; color: {text_color};")
        elif BTN.second:
            self.second_pushButton.setText(text)
            self.second_pushButton.setStyleSheet(
                f"background-color: {bg_color}; color: {text_color};")

    def __length_monitor(self, encoder_val: str):
        self.lengthVal_label.setText(f"{encoder_val} / {self.__length_target}")
        if int(encoder_val) > (self.__length_target - int(os.getenv("STOP_OFFSET")))\
            and not self.__rope_lenght_accepted\
                and not self.__block__buttons:
            self.monitor_worker.checks_during_winding = False
            self.__machine_control.winder_STOP()
            if self.__current_state == STATES.winding:
                self.__rope_lenght_accepted = True
                self.__set_cutRope_state()
            else:
                self.__block__buttons = True
                self.first_pushButton.setDisabled(True)
                self.second_pushButton.setDisabled(True)
                self.alert("Lina przeciągnięta bez udziału silnika",
                           "Cofnij linę na poniżej docelowej długości z zapasem")
        elif int(encoder_val) < self.__length_target - 500:
            self.__block__buttons = False
            self.first_pushButton.setEnabled(True)
            self.second_pushButton.setEnabled(True)

    def __update_time_reading(self, stopwatch_val: str):
        self.timeVal_label.setText(stopwatch_val)

    def __update_quantity_progress(self, new_val: int):
        self.__quantity_current = new_val
        self.progressVal_label.setText(f"{new_val} / {self.__quantity_target}")

    def __monitor_error(self, err_title, err_desc):
        self.__set_pause_state()
        self.alert(err_title, err_desc)

    def initial_run(self):
        self.__runtime.run()
        self.__encoder.begin_measurement(int(os.getenv('START_LENGHT')))
        # Monitor thread definition
        self.monitor_pool = QtCore.QThreadPool.globalInstance()
        self.monitor_worker = MonitorProcess(self.__machine_control,
                                             self.__encoder, self.__runtime)
        # Pause till confirmation
        self.__encoder.pause_measurement()
        # Length signal handling
        self.monitor_worker.signals.length_reading.connect(
            self.__length_monitor)
        # Time signal handling
        self.monitor_worker.signals.time_reading.connect(
            self.__update_time_reading)
        # Error signal handling
        self.monitor_worker.signals.error_signal.connect(self.__monitor_error)
        # Set action on thread start
        self.monitor_worker.signals.started.connect(self.monitor_worker.run)
        # Start thread
        self.monitor_pool.start(self.monitor_worker)
        # Set working state
        self.__set_waitForNext_state()

    def winder_STOP(self):
        # Thread definition
        action = Actions.winder_STOP
        pool = QtCore.QThreadPool.globalInstance()
        worker = MachineWorker(self.__machine_control, action)
        # Error signal handling
        worker.signals.error_signal.connect(self.alert)
        # Set action on thread start
        worker.signals.started.connect(worker.run)
        # Start thread
        pool.start(worker)

    def __print_label(self):
        try:
            printer = ZebraPrinter(
                self.order_id,
                self.__customer_name,
                self.__length_target,
                self.__diameter
            )
            printer.print_label()
            logger.info("Label was added to printing queue")

            if self.__current_state == STATES.reset_position:
                self.__set_waitForNext_state()

        except Exception as e:
            self.__buzzer.cancel_buzzer()
            logger.error("Label printing failed")
            error = ErrorDialog(
                self.__parent_class,
                "Błąd drukowania etykiety",
                "Sprawdź czy drukarka jest poprawnie podłączona i czy jest włączona.",
                self.__buzzer,
                printer_error=True
            )
            error.rejected.connect(self.__print_label)

            if self.__current_state == STATES.reset_position:
                error.accepted.connect(self.__set_waitForNext_state)

            error.exec()

    def __first_btn_fcn(self, type_of_event: str):
        """
        A function that performs appropriate actions after user interaction with the `first_pushButton` (upper) button, depending on the value of `current_state`.
        """
        if type_of_event == "clicked" and not self.__block__buttons:
            if self.__current_state in [STATES.winding, STATES.reset_position, STATES.cut_rope]:
                self.__set_pause_state()
            elif self.__current_state == STATES.paused:
                self.__continue_work()
            elif self.__current_state == STATES.winding_fail:
                self.__set_winding_state()
            elif self.__current_state == STATES.cut_rope_fail:
                self.__set_cutRope_state()
            elif self.__current_state == STATES.reset_position_fail:
                self.__set_resetPosition_state()
            elif self.__current_state == STATES.cancel:
                self.__set_cancel_state(perform_cancel=True)
            elif self.__current_state == STATES.next_run_confirmation:
                self.__set_nextRunConfirmation_state(type_of_event)

        if type_of_event == "pressed" and not self.__block__buttons:
            if self.__current_state == STATES.next_run_confirmation:
                self.__set_nextRunConfirmation_state(type_of_event)

    def __second_btn_fcn(self):
        """
        A function that performs appropriate actions after user interaction with the `second_pushButton` (lower) button, depending on the value of `current_state`.
        """
        if not self.__block__buttons:
            if self.__current_state in [
                    STATES.paused,
                    STATES.winding,
                    STATES.winding_fail,
                    STATES.cut_rope,
                    STATES.cut_rope_fail,
                    STATES.reset_position,
                    STATES.reset_position_fail,
                    STATES.next_run_confirmation
            ]:
                self.__set_cancel_state()
            elif self.__current_state == STATES.cancel:
                self.__set_cancel_state(perform_cancel=False)
            elif self.__current_state == STATES.summary and self.__previous_state == STATES.cancel:
                self.reject()
            elif self.__current_state == STATES.summary and self.__previous_state == STATES.reset_position:
                self.accept()

    #######################################################
    # paused STATE actions
    #######################################################

    def __set_pause_state(self):
        """
        Stops machine and runtime 
        """
        # Hide  `pushButton_resetAgain`
        self.pushButton_resetAgain.setHidden(True)
        if self.__paused_state is None:
            self.__paused_state = self.__current_state
        self.set_states(STATES.paused)
        self.monitor_worker.checks_during_winding = False
        # UI ACTIONS
        self.set_info_label("Zadanie wstrzymane", "yellow")
        self.set_button(BTN.first, "Wznów", "#00aa00")
        self.set_button(BTN.second, "Anuluj", "#aa0000")

        # MACHINE ACTIONS
        if self.__previous_state in [STATES.winding, STATES.reset_position]:
            self.__runtime.pause()
            self.winder_STOP()
        elif self.__previous_state == STATES.cut_rope:
            self.__runtime.pause()
            self.set_button(
                BTN.first, "Przywracanie gilotyny...", "#888888")
            self.set_button(BTN.second, "Anuluj", "#888888")
            self.first_pushButton.setDisabled(True)
            self.second_pushButton.setDisabled(True)
            self.cut_worker.cancel_cutting_run()

    def __continue_work(self):
        logger.info(f"Continue back to state: {self.__paused_state}")
        # start detecting erros after pause
        self.monitor_worker.should_emit_errors = True
        self.__runtime.run()
        if self.__paused_state == STATES.winding:
            self.__set_winding_state()
        if self.__paused_state == STATES.winding_fail:
            self.__set_windingFail_state()
        if self.__paused_state == STATES.cut_rope:
            self.__set_cutRope_state()
        if self.__paused_state == STATES.cut_rope_fail:
            self.__set_cutFail_state()
        elif self.__paused_state == STATES.reset_position:
            self.__set_resetPosition_state()
        elif self.__paused_state == STATES.reset_position_fail:
            self.__set_resetPositionFail_state()
        elif self.__paused_state == STATES.next_run_confirmation:
            self.__set_waitForNext_state()
        elif self.__paused_state == STATES.winding_fail:
            self.__set_windingFail_state()

        self.__paused_state = None

    #######################################################
    # cancel STATE actions
    #######################################################

    def __set_cancel_state(self, perform_cancel: bool = None):
        """
        Stop winder and runtime. Ask for end process.
        """
        # Hide  `pushButton_resetAgain`
        self.pushButton_resetAgain.setHidden(True)
        if perform_cancel == False:
            self.__set_pause_state()

        elif perform_cancel == True:
            self.__paused_state = None
            self.__set_summary_state()

        else:
            # UI ACTIONS
            self.set_info_label(
                "Czy na pewno chcesz przerwać zadanie?", "yellow")
            self.set_button(BTN.first, "Tak", "#aa0000")
            self.set_button(BTN.second, "Nie", "#00aa00")
            if self.__paused_state is None:
                self.__paused_state = self.__current_state
            self.set_states(STATES.cancel)

            # MACHINE ACTIONS
            if self.__previous_state in [STATES.winding, STATES.reset_position]:
                self.monitor_worker.checks_during_winding = False
                self.__runtime.pause()
                self.winder_STOP()
            if self.__previous_state in [STATES.reset_position_fail, STATES.next_run_confirmation]:
                self.__runtime.pause()
            elif self.__previous_state == STATES.cut_rope:
                self.__runtime.pause()
                self.set_button(
                    BTN.first, "Przywracanie gilotyny...", "#888888")
                self.set_button(BTN.second, "Nie", "#888888")
                self.first_pushButton.setDisabled(True)
                self.second_pushButton.setDisabled(True)
                self.cut_worker.cancel_cutting_run()

    #######################################################
    # winding and winding_fail STATES actions
    #######################################################

    def __set_winding_state(self):
        """
        Run winder and runtime
        """
        self.set_states(STATES.winding)

        # UI ACTIONS
        self.set_info_label("Nawijanie...", "white")
        self.set_button(BTN.first, "Zatrzymaj", "#ffaa00")
        self.set_button(BTN.second, "Anuluj", "#aa0000")
        # MACHINE ACTIONS

        def after():
            # Monitor machine state
            self.monitor_worker.checks_during_winding = True
            if self.__machine_control.is_guillotine_press_circuit_active():
                self.activate_guillotine_press_circuit(False)

        def fail(err_title, err_desc):
            self.alert(err_title, err_desc)
            self.__set_windingFail_state()

        # Thread definition
        pool = QtCore.QThreadPool.globalInstance()
        worker = MachineWorker(self.__machine_control,
                               Actions.winder_clockwise)
        # Error signal handling
        worker.signals.error_signal.connect(fail)
        # Done signal handling
        worker.signals.done.connect(after)
        # Set action on thread start
        worker.signals.started.connect(worker.run)
        # Start thread
        pool.start(worker)

    def __set_windingFail_state(self):
        # UI actions
        self.set_states(STATES.winding_fail)
        self.set_button(BTN.first, "Powtórz próbę", "#00aa00")
        self.set_button(BTN.second, "Anuluj", "#aa0000")
        self.set_info_label(
            "Nieudana próba uruchomienia nawijania", "red")

    #######################################################
    # cut_rope and cut_rope_fail STATES actions
    #######################################################

    def __set_cutRope_state(self):
        # UI Actions
        self.set_states(STATES.cut_rope)
        self.set_info_label("Ucinanie linki...", "yellow")
        self.set_button(BTN.first, "Zatrzymaj", "#ffaa00")
        self.set_button(BTN.second, "Anuluj", "#aa0000")

        # Machine Actions
        # Signal stop
        self.__buzzer.signal("stop")
        # Define after action

        def after():
            self.__encoder.pause_measurement()
            self.__encoder.reset_measurement()
            self.monitor_worker.should_emit_lenght = False
            self.__set_resetPosition_state()

        def fail(err_title, err_desc):
            self.first_pushButton.setEnabled(True)
            self.second_pushButton.setEnabled(True)
            if self.__current_state == STATES.paused:
                self.set_button(BTN.first, "Wznów", "#00aa00")
                self.set_button(BTN.second, "Anuluj", "#aa0000")
            elif self.__current_state == STATES.cancel:
                self.set_button(BTN.first, "Tak", "#aa0000")
                self.set_button(BTN.second, "Nie", "#00aa00")
            self.alert(err_title, err_desc)
            self.__set_cutFail_state()

        def paused():
            self.first_pushButton.setEnabled(True)
            self.second_pushButton.setEnabled(True)
            if self.__current_state == STATES.paused:
                self.set_button(BTN.first, "Wznów", "#00aa00")
                self.set_button(BTN.second, "Anuluj", "#aa0000")
            elif self.__current_state == STATES.cancel:
                self.set_button(BTN.first, "Tak", "#aa0000")
                self.set_button(BTN.second, "Nie", "#00aa00")

        # Thread definition
        action = Actions.cut_rope
        pool = QtCore.QThreadPool.globalInstance()
        self.cut_worker = MachineWorker(self.__machine_control, action)
        # Error signal handling
        self.cut_worker.signals.error_signal.connect(fail)
        # Oprional signal handling
        self.cut_worker.signals.optional.connect(paused)
        # Done signal handling
        self.cut_worker.signals.done.connect(after)
        # Set action on thread start
        self.cut_worker.signals.started.connect(self.cut_worker.run)
        # Start thread
        pool.start(self.cut_worker)

    def __set_cutFail_state(self):
        self.set_states(STATES.cut_rope_fail)
        # UI Actions
        self.set_info_label("Nie udane ucinanie linki", "red")
        self.set_button(BTN.first, "Ponów ucinanie", "#00aa00")
        self.set_button(BTN.second, "Anuluj", "#aa0000")

    #######################################################
    # reset_position and reset_position_fail STATES actions
    #######################################################

    def __set_resetPosition_state(self, first_run: bool = True):
        self.set_states(STATES.reset_position)
        logger.info("STATE - reset_position")
        # UI Actions
        self.set_info_label(
            "Przywracnie bębna do pozycji zerowej...", "yellow")
        self.set_button(BTN.first, "Zatrzymaj", "#ffaa00")
        self.set_button(BTN.second, "Anuluj", "#aa0000")
        # Machine Actions
        # Define after action

        def after():
            # Signal end
            if first_run:
                self.__buzzer.signal("end")
                self.__update_quantity_progress(self.__quantity_current+1)
                if self.__quantity_current >= self.__quantity_target:
                    self.__set_summary_state()
                elif (os.getenv("PRINT_LABELS", 'False') == 'True') and (os.getenv("PRINT_LABEL_EVERY_OTHER_ROPE", 'False') == 'True') and self.__quantity_current % 2 == 0:
                    self.__print_label()
                else:
                    self.__set_waitForNext_state()
            else:
                self.__set_waitForNext_state()

        def fail(err_title, err_desc):
            self.alert(err_title, err_desc)
            self.__set_resetPositionFail_state()

        # Thread definition
        action = Actions.winder_reset_position
        self.reset_pool = QtCore.QThreadPool.globalInstance()
        self.reset_worker = MachineWorker(self.__machine_control, action)
        # Error signal handling
        self.reset_worker.signals.error_signal.connect(fail)
        # Done signal handling
        self.reset_worker.signals.done.connect(after)
        # Set action on thread start
        self.reset_worker.signals.started.connect(self.reset_worker.run)
        # Start thread
        self.reset_pool.start(self.reset_worker)

    def __set_resetPositionFail_state(self):
        self.set_states(STATES.reset_position_fail)
        # UI actions
        self.set_button(BTN.first, "Powtórz przywracanie", "#00aa00")
        self.set_button(BTN.second, "Anuluj", "#aa0000")
        self.set_info_label(
            "Nieudane przywracanie do pozycji zerowej", "red")

    #######################################################
    # next_run_confirmation STATE actions
    #######################################################

    def __set_waitForNext_state(self):
        self.set_states(STATES.next_run_confirmation)
        # Show `pushButton_resetAgain`
        self.pushButton_resetAgain.setHidden(False)
        self.set_info_label(
            "Układ gilotyny i prasy został odblokowany.\nPotwierdź przygotowanie linki", "lime")
        self.set_button(BTN.first, "Potwierdź", "#00aa00")

        # Machine Actions
        self.activate_guillotine_press_circuit(True)

    def activate_guillotine_press_circuit(self, active: bool):
        # Machine Actions
        # Thread definition
        action = Actions.guillotine_press_circuit
        pool = QtCore.QThreadPool.globalInstance()
        worker = MachineWorker(self.__machine_control, action, active)
        # Error signal handling
        worker.signals.error_signal.connect(self.alert)
        # Set action on thread start
        worker.signals.started.connect(worker.run)
        # Start thread
        pool.start(worker)

    #######################################################
    # next_rope STATE actions
    #######################################################

    def __set_nextRunConfirmation_state(self, call_type: str):
        """
        Handle the next_rope confirmation. This function is first executed by a `pressed` signal.
        If the button is still down after 'CONFIRM_NEW_LINE_TIME', then if the user presses the button, the next line winding is starting.
        """
        if self.__next_rope_confirmed and call_type == "clicked":
            # Hide  `pushButton_resetAgain`
            self.pushButton_resetAgain.setHidden(True)
            self.__encoder.begin_measurement(int(os.getenv('START_LENGHT')))
            self.monitor_worker.should_emit_lenght = True
            self.__rope_lenght_accepted = False
            self.__next_rope_confirmed = False
            self.__confirmation_started = False
            logger.success("Run next rope winding process")
            # Signal start
            self.__buzzer.signal("start")
            self.__set_winding_state()

        elif self.__confirmation_started and call_type == "clicked":
            self.confirmation_worker.cancel_confirmation()

        elif not self.__confirmation_started and call_type == "pressed":
            def after():
                logger.success("Confirmation - success")
                self.set_info_label(
                    "Puść przycisk aby rozpocząć nawijanie", "yellow")
                self.__next_rope_confirmed = True

            def confirmation_failed():
                logger.warning("Confirmation - failed")
                self.__confirmation_started = False

            # Thread definition
            self.confirmation_pool = QtCore.QThreadPool.globalInstance()
            self.confirmation_worker = NextRope()
            # Done signal handling
            self.confirmation_worker.signals.done.connect(after)
            # Failed signal handling
            self.confirmation_worker.signals.failed.connect(
                confirmation_failed)
            # Set action on thread start
            self.confirmation_worker.signals.started.connect(
                self.confirmation_worker.run)
            # Start thread
            self.__confirmation_started = True
            self.confirmation_pool.start(self.confirmation_worker)
            logger.info("Confirmation - started")

    #######################################################
    # summary STATE actions
    #######################################################

    def __set_summary_state(self):
        """
        Stop all running threads and show end button
        """

        self.set_states(STATES.summary)
        # Machine Actions
        self.monitor_worker.set_work_done()
        self.__encoder.pause_measurement()
        self.__encoder.reset_measurement()
        self.final_execution_time = self.__runtime.get_time()
        self.__runtime.reset()
        self.activate_guillotine_press_circuit(True)
        # UI Actions
        if self.__previous_state == STATES.reset_position:
            if (os.getenv("PRINT_LABELS", 'False') == 'True') and self.__quantity_current > 0:
                self.__print_label()
            self.set_info_label(
                "Zadanie zostało zakończone pomyślnie.\n\nWciśnij „Zakończ”, aby powrócić do\n ekranu wprowadzania.",
                "lime"
            )

        elif self.__previous_state == STATES.cancel:
            if (os.getenv("PRINT_LABELS", 'False') == 'True') and self.__quantity_current > 0 and not self.__quantity_current % 2 == 0:
                self.__print_label()

            self.set_info_label(
                "Przerwano wykonywanie obecnego zadania.\n\nWciśnij „Zakończ”, aby powrócić do\n ekranu wprowadzania.",
                "yellow"
            )
        self.first_pushButton.setHidden(True)
        self.set_button(BTN.second, "Zakończ", "#00aa00")
