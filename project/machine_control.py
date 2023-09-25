from enum import Enum
from loguru import logger
from PyQt5 import QtWidgets, QtCore
import pigpio
import time
import threading
from LOGS.error_handling import ErrorDialog
from buzzer import Buzzer



class Actions(Enum):
    """
    `Actions` contains the actions available for execution in the `MachineControl` class. 
    Individual methods are assigned at the initialization of the `MachineConrol` class.

    Available actions:
    --
    - check_motor_on_and_air_status
    - winder_clockwise
    - winder_counter_clockwise
    - winder_STOP
    - winder_reset_position
    - guillotine_press
    - guillotine_press_circuit

    IMPORTANT
    --
    To execute wanted action with arguments witch `execute` method in `MachineControl` class, provide args after comma.

    Example of usage:
    --
    - function without args: `mc.execute(Actions.winder_STOP)`  
    - function with args: `mc.execute(Actions.winder_counter_clockwise, True)`  
    """
    winder_clockwise = 1
    """
    Function do not takes any arguments.
    """
    winder_counter_clockwise = 2
    """
    Function takes one argument: `state:bool`. 
    """
    winder_STOP = 3
    """
    Function do not takes any arguments.
    """
    winder_reset_position = 4
    """
    Function takes one OPTIONAL argument: `activationFunction:ManualInsertingTab`.
    """
    guillotine_press = 5
    """
    Function takes one argument: `state:bool`. 
    """
    guillotine_press_circuit = 6
    """
    Function takes one argument: `state:bool`. 
    """


class MachineControl(QtCore.QObject):
    """
    MachineControl
    ---

    `MachineControl` handles communication and control of winder and guillotine.

    Parameters
    ---

    :pi: instance of `pigpio.pi`

    More information about `pigpio` module available on site: http://abyz.me.uk/rpi/pigpio/python.html
    """
    # Dictionary of physical pins `'name of pin on relay module': RPi_BCM_GPIO_pin_number`
    __RELAY_MODULE = {
        # Winder clockwise rotation START (running untill STOP is executed)
        'IN1': 21,
        # Winder counterclockwise rotation START (runs only on holded high state)
        'IN2': 16,
        'IN3': 20,  # Winder rotation STOP
        'IN4': 12,  # Guillotine cut
        'IN5': 25,  # Guillotine/press circuit
        'IN6': 24,  # NOT USED
        'IN7': 23,  # NOT USED
        'IN8': 18   # NOT USED
    }

    __HALL_SENSOR = 4  # Pin connected to Hall sensor
    __MOTOR_STATUS_PIN = 22   # Pin connected to winder motor relay
    __GUILLOTINE_READY = 17  # Pin connected to hall sensor of guillotine
    __PRESSOSTAT = 27   # Pin connected to pressostat

    __ON_TIME = 0.1  # Relay activation time expressed in seconds

    __is_executed = False    # Contains the status of the winder motor relay

    __is_running = False  # ONLY FOR TESTS - DELETE BEFORE PRODUCTION

    error_signal = QtCore.pyqtSignal(str, str)
    done = QtCore.pyqtSignal()

    def __init__(self, pi: pigpio, buzzer: Buzzer):
        super().__init__()
        self.__pi: pigpio.pi = pi
        self.__buzzer = buzzer

        # Set the pins of the relay module in OUT mode to HIGH state (relays off)
        for pin in self.__RELAY_MODULE.values():
            self.__pi.set_mode(pin, pigpio.OUTPUT)
            self.__pi.write(pin, 1)

        # Set the pin for the Hall sensor of wheel zero position signal in INPUT mode.
        # If the wheel is in zeroposition, the reading should be True.
        self.__pi.set_mode(self.__HALL_SENSOR, pigpio.INPUT)
        self.__pi.set_pull_up_down(self.__HALL_SENSOR, pigpio.PUD_DOWN)

        # Set the pin for the pressure switch signal in INPUT mode.
        # If the air pressure is too low, the reading should be false.
        self.__pi.set_mode(self.__PRESSOSTAT, pigpio.INPUT)
        self.__pi.set_pull_up_down(self.__PRESSOSTAT, pigpio.PUD_DOWN)

        # Set the pin for the motor-on signal in INPUT mode.
        # If the motor is NOT running, the reading should be false.
        self.__pi.set_mode(self.__MOTOR_STATUS_PIN, pigpio.INPUT)
        self.__pi.set_pull_up_down(self.__MOTOR_STATUS_PIN, pigpio.PUD_DOWN)

        # Set the pin for the motor-on signal in INPUT mode.
        # If the motor is NOT running, the reading should be false.
        self.__pi.set_mode(self.__PRESSOSTAT, pigpio.INPUT)
        self.__pi.set_pull_up_down(self.__PRESSOSTAT, pigpio.PUD_DOWN)

        # Define actions object
        self.actions_handler = {
            Actions.winder_clockwise: self.winder_clockwise,
            Actions.winder_counter_clockwise: self.winder_counter_clockwise,
            Actions.winder_STOP: self.winder_STOP,
            Actions.winder_reset_position: self.winder_reset_position,
            Actions.guillotine_press: self.guillotine_press,
            Actions.guillotine_press_circuit: self.guillotine_press_circuit,
        }

    def __error_handler(self, err_title: str, err_desc: str):
        self.error_signal.emit(err_title, err_desc)

    def execute(self, action_name: Actions, *args):
        """
        Execute actions in a separate thread available in the `Actions` class.


        Parametres:
        --
        - `name of action` - goes first
        - `*args` - optional or required depends on the function's execution.

        IMPORTANT
        --
        The order of parameters is important; the name of the action always goes first.
        """
        if action_name in self.actions_handler and not MachineControl.__is_executed:
            MachineControl.__is_executed = True
            action = self.actions_handler[action_name]
            action(*args)

        self.done.emit()
        MachineControl.__is_executed = False

    def is_motor_on(self):
        """
        Return `True` if the motor relay (24V in the bigger box) is ON. Otherwise, return `False`.
        """
        return True if self.__pi.read(self.__MOTOR_STATUS_PIN) else False

    def check_air_presence(self) -> bool:
        """
        Return `True` if the air pressure is correct, or `False` if the pressure is too low.
        """
        return True if self.__pi.read(self.__PRESSOSTAT) else False

    def check_guillotine_press(self) -> bool:
        """
        Return `True` if the guillotine press is in up position and ready to work. Otherwise, return `False`.
        """
        return True if self.__pi.read(self.__GUILLOTINE_READY) else False

    # The function of starting the winder in a clockwise direction

    def winder_clockwise(self, after_check_status: bool = True):
        """
        Turn on winder in clockwise direction. Winder is working until `winder_STOP()` function is called.
        """
        #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! DELETE TRUE, remove __is_running
        if True or not self.check_motor_on() and self.check_guillotine_press() and self.check_air_presence():
            self.__pi.write(self.__RELAY_MODULE['IN1'], 0)
            time.sleep(self.__ON_TIME)
            self.__pi.write(self.__RELAY_MODULE['IN1'], 1)
            # ONLY FOR TESTS - DELETE BEFORE PRODUCTION
            MachineControl.__is_running = True
            if after_check_status:
                if not self.is_motor_on():
                    logger.error("Motor failure detected!")
                    self.winder_STOP(False)
                    self.__error_handler(
                        "Awaria silnika zwijacza", "Należy sprawdzić poprawność dziłania silnika, badź jego przekaźnika")
                else:
                    logger.success("Motor is running...")
                    # self.__buzzer.signal('start')

    # The function of starting the winder in a counter-clockwise direction

    def winder_counter_clockwise(self, state: bool):

        if state:
            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! DELETE TRUE, remove __is_running
            if True or not self.check_motor_on() and self.check_guillotine_press() and self.check_air_presence():
                self.__pi.write(self.__RELAY_MODULE['IN2'], 0)
                time.sleep(0.2)
                if not self.is_motor_on():
                    self.__pi.write(self.__RELAY_MODULE['IN2'], 1)
                    logger.error("Motor failure detected!")

                else:
                    logger.success("Motor is running...")
                    # self.__buzzer.signal('start')
        else:
            self.__pi.write(self.__RELAY_MODULE['IN2'], 1)
            time.sleep(0.2)
            if self.is_motor_on():
                logger.critical(
                    "THE MOTOR STILL RUNS DESPITE THE STOP PROCEDURE!\t!!!PRESS EMERGENCY STOP!!!")
            else:
                logger.success("Motor stopped")
                # self.__buzzer.signal('stop')

    # The function of stopping the winder
     #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! remove __is_running
    def winder_STOP(self, after_check_status: bool = True, direct_execution: bool = False):
        self.__pi.write(self.__RELAY_MODULE['IN3'], 0)
        time.sleep(self.__ON_TIME)
        self.__pi.write(self.__RELAY_MODULE['IN3'], 1)
        # ONLY FOR TESTS - DELETE BEFORE PRODUCTION
        self.__is_running = False
        if after_check_status:
            if self.is_motor_on():
                logger.critical(
                    "THE MOTOR STILL RUNS DESPITE THE STOP PROCEDURE!\t!!!PRESS EMERGENCY STOP!!!")
                self.__error_handler(
                    "AWARIA STEROWANIA", "WCIŚNIJ WYŁĄCZNIK BEZPIECZŚTWA.\n Należy dokładnie sprawdzić sprawdzić układ sterujący przed następnym uruchomieniem. Skontaktuj się z serwisem.")
            else:
                logger.success("Motor stopped")
                # self.__buzzer.signal('stop')
        if direct_execution:
            self.done.emit()

    # Function which brings hook on the wheel to zero position
    def winder_reset_position(self, activationFunction=None, searching_time=10):
        # activationFunction is function for enable disabled winder buttons
        # Event for winding in progress dialog

        if self.__pi.read(self.__HALL_SENSOR) == 1:
            logger.info('Done - was in zero position')

        else:
            print("Start")
            start_time = time.time()
            logger.info("Looking for zero position...")
            self.winder_clockwise(after_check_status=False)
            found: bool = True
            while self.__pi.read(self.__HALL_SENSOR) == 0:
                # If zero point is not detected in 10 seconds that means the hardware failure
                if (time.time()-start_time) > searching_time:
                    self.winder_STOP()
                    found = False
                    logger.error(
                        "Winder or Hall sensor or some relay failure")
                    self.__error_handler(
                        "Nie wykryto\n punktu zero", "Należy sprawdzić poprawność działania czujnika Halla i obecność magnesu na kole zwijacza.")
                    break
                # Handling the winder stopped event
                #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! DELETE __is_runnning place not befor check_motor_on
                elif self.is_motor_on() or not MachineControl.__is_running:
                    logger.warning("The winder stopped")
                    found = False
                    break
                time.sleep(0.001)

            if not found:
                if callable(activationFunction):
                    activationFunction(True)
            else:
                self.winder_STOP()
                logger.success("Done - zero position found")
                if callable(activationFunction):
                    activationFunction(True)

    # The guillotine press function

    def guillotine_press(self, state: bool):
        #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! DELETE TRUE
        if True or self.check_motor_on() and self.check_air_presence() and self.check_guillotine_press():
            if state:
                self.__pi.write(self.__RELAY_MODULE['IN4'], 0)
                logger.info("Guillotine pressed")
            else:
                self.__pi.write(self.__RELAY_MODULE['IN4'], 1)
                logger.info("Guillotine released")

    # Function that enable the possibility of manual use of the guillotine or crimper

    def guillotine_press_circuit(self, state):
        if not self.is_motor_on() and self.check_air_presence() and self.check_guillotine_press():
            if state:
                self.__pi.write(self.__RELAY_MODULE['IN5'], 0)
                logger.info("Guillotine nad press circuit activated")
            else:
                self.__pi.write(self.__RELAY_MODULE['IN5'], 1)
                logger.info("Guillotine nad press circuit deactivated")

    def get_winder_status(self) -> bool:
        return self.is_motor_on()


if __name__ == '__main__':
    pi = pigpio.pi()
    mc = MachineControl(pi)

    print(f"Is motor running: {mc.is_motor_on()}")
    mc.execute(Actions.winder_clockwise)
