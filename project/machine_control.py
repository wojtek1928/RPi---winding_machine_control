from enum import Enum
from os import getenv
from dotenv import load_dotenv
from loguru import logger
from PyQt5 import QtCore
import pigpio
import time
from buzzer import Buzzer


class Signals(QtCore.QObject):
    started = QtCore.pyqtSignal()
    error_signal = QtCore.pyqtSignal(str, str)
    optional = QtCore.pyqtSignal()
    done = QtCore.pyqtSignal()


class MachineException(Exception):
    def __init__(self, title: str, description: str):
        self.title = title
        self.description = description


class OptinalException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class Actions(Enum):
    """
    `Actions` contains the actions available for execution in the `MachineControl` class. 
    Individual methods are assigned at the initialization of the `MachineConrol` class.

    Available actions:
    --
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
    cut_rope = 6
    """
    Function do not takes any arguments.
    """
    guillotine_press_circuit = 7
    """
    Function takes one argument: `state:bool`. 
    """


class MachineControl(QtCore.QRunnable):
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
    __GUILLOTINE_UP = 17  # Pin connected to hall sensor of guillotine
    __PRESSOSTAT = 27   # Pin connected to pressostat

    __ON_TIME = 0.1  # Relay activation time expressed in seconds

    __is_executed: bool = False    # Contains the status of the winder motor relay

    # Flag for cutting event, when is set to `True` then cutting is canceled
    __cancel_cutting: bool = False

    def __init__(self, pi: pigpio):
        super().__init__()
        self.__pi: pigpio.pi = pi
        self.signals = Signals()

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
            Actions.cut_rope: self.cut_rope,
            Actions.guillotine_press_circuit: self.guillotine_press_circuit
        }

    def __error_handler(self, err_title: str, err_desc: str):
        raise MachineException(err_title, err_desc)

    def execute(self, action_name: Actions, *args, **kwargs):
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
        if action_name in self.actions_handler:
            if action_name == Actions.winder_STOP:
                action = self.actions_handler[action_name]
                action(*args, **kwargs)
            elif not MachineControl.__is_executed:
                logger.info(f"Exceuting: {action_name.name} ...")
                MachineControl.__is_executed = True
                action = self.actions_handler[action_name]
                action(*args, **kwargs)
                MachineControl.__is_executed = False

    def is_motor_on(self, raise_error: bool = False, end_operation: bool = True):
        """
        Return `True` if the motor relay (24V in the bigger box) is ON. Otherwise, return `False`.
        """
        if not self.__pi.read(self.__MOTOR_STATUS_PIN):
            if raise_error:
                if end_operation:
                    MachineControl.__is_executed = False
                raise MachineException(
                    "Awaria silnika zwijacza", "Należy sprawdzić poprawność dziłania silnika, badź jego przekaźnika.")
            else:
                return False
        return True

    def is_in_zero_positon(self):
        """
        Return `True` if the winder drum is in zero position. Otherwise, return `False`.
        """
        return True if self.__pi.read(self.__HALL_SENSOR) else False

    def is_air_present(self, raise_error: bool = False, end_operation:bool = True) -> bool:
        """
        Return `True` if the air pressure is correct, or `False` if the pressure is too low.
        """
        if not self.__pi.read(self.__PRESSOSTAT):
            if raise_error:
                if end_operation:
                    MachineControl.__is_executed = False
                raise MachineException(
                    "Niskie ciśnienie powietrza", "Sprawdź zawór pneumatyczny i połączenie z centralną pneumatyką.")
            else:
                return False
        return True

    def is_guillotine_up(self, raise_error: bool = False, end_operation: bool = True) -> bool:
        """
        Return `True` if the guillotine press is in up position and ready to work. Otherwise, return `False`.
        """
        if not self.__pi.read(self.__GUILLOTINE_UP):
            if raise_error:
                if end_operation:
                    MachineControl.__is_executed = False
                MachineControl.__is_executed=False
                raise MachineException(
                    "Gilotyna opuszczona", "Gilotyna jest w nie właściwej pozycji.\n Przyczyną może być zbyt niskie ciśnienie powietrza.")
            else:
                return False
        return True

    # The function of starting the winder in a clockwise direction

    def winder_clockwise(self, after_check_status: bool = True):
        """
        Turn on winder in clockwise direction. Winder is working until `winder_STOP()` function is called.
        """
        if not self.is_motor_on() and self.is_guillotine_up(True) and self.is_air_present(True):
            self.__pi.write(self.__RELAY_MODULE['IN1'], 0)
            time.sleep(self.__ON_TIME)
            self.__pi.write(self.__RELAY_MODULE['IN1'], 1)
            if after_check_status:
                time.sleep(0.25)
                if not self.is_motor_on():
                    MachineControl.__is_executed = False
                    logger.error("Motor failure detected!")
                    self.winder_STOP(False)
                    self.__error_handler(
                        "Awaria silnika zwijacza", "Należy sprawdzić poprawność dziaaaaałania silnika, badź jego przekaźnika.")
                else:
                    logger.success("Motor is running...")
    # The function of starting the winder in a counter-clockwise direction

    def winder_counter_clockwise(self, state: bool):

        if state:
            if not self.is_motor_on() and self.is_guillotine_up() and self.is_air_present():
                self.__pi.write(self.__RELAY_MODULE['IN2'], 0)
                time.sleep(0.1)
                if not self.is_motor_on():
                    logger.error("Motor failure detected!")

                else:
                    logger.success("Motor is running...")
                    
        else:
            self.__pi.write(self.__RELAY_MODULE['IN2'], 1)
            time.sleep(0.1)
            if self.is_motor_on():
                logger.critical(
                    "THE MOTOR STILL RUNS DESPITE THE STOP PROCEDURE!\t!!!PRESS EMERGENCY STOP!!!")
            else:
                logger.success("Motor stopped")

    # The function of stopping the winder
    def winder_STOP(self, after_check_status: bool = True, direct_execution: bool = False):
        self.__pi.write(self.__RELAY_MODULE['IN3'], 0)
        time.sleep(self.__ON_TIME)
        self.__pi.write(self.__RELAY_MODULE['IN3'], 1)
        if after_check_status:
            if self.is_motor_on():
                logger.critical(
                    "THE MOTOR STILL RUNS DESPITE THE STOP PROCEDURE!\t!!!PRESS EMERGENCY STOP!!!")
                self.__error_handler(
                    "AWARIA STEROWANIA", "WCIŚNIJ WYŁĄCZNIK BEZPIECZŚTWA.\n Należy dokładnie sprawdzić sprawdzić układ sterujący przed następnym uruchomieniem. Skontaktuj się z serwisem.")
            else:
                logger.success("Motor stopped")
                MachineControl.__is_executed = False
                
        if direct_execution:
            self.signals.done.emit()

    # Function which brings hook on the wheel to zero position
    def winder_reset_position(self, activationFunction=None):
        # activationFunction is function for enable disabled winder buttons
        # Event for winding in progress dialog

        if self.__pi.read(self.__HALL_SENSOR) == 1:
            logger.info('Done - was in zero position')

        else:
            start_time = time.time()
            logger.info("Looking for zero position...")
            self.winder_clockwise(after_check_status=False)
            found: bool = True
            while self.__pi.read(self.__HALL_SENSOR) == 0:
                # If zero point is not detected in `TIME_TO_SEARCH_FOR_ZERO` seconds that means the hardware failure
                if (time.time()-start_time) > int(getenv("TIME_TO_SEARCH_FOR_ZERO")):
                    self.winder_STOP()
                    found = False
                    MachineControl.__is_executed = False
                    logger.error(
                        "Winder or Hall sensor or some relay failure")
                    self.__error_handler(
                        "Nie wykryto\n punktu zero", "Należy sprawdzić poprawność działania czujnika Halla i obecność magnesu na kole zwijacza.")

                    break
                # Handling the winder stopped event
                elif not self.is_motor_on():
                    MachineControl.__is_executed = False
                    logger.warning("The winder stopped")
                    found = False
                    raise OptinalException()

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
        if not self.is_motor_on() and self.is_air_present():
            if state:
                self.__pi.write(self.__RELAY_MODULE['IN4'], 0)
                logger.info("Guillotine pressed")
            else:
                self.__pi.write(self.__RELAY_MODULE['IN4'], 1)
                logger.info("Guillotine released")

    def __custom_delay(self, duration: float):
        """
        This method corresponds to the `time.sleep()` function, 
        but it also checks if the flag 'self.__cancel_cutting' is not set.
        If an event is set, then the function raises an `Exception` that is caught by the `MachineWorker` main function.
        """
        start = time.time()
        while time.time() - start < duration and not self.__cancel_cutting:
            pass

        if self.__cancel_cutting:
            if not self.is_guillotine_up():
                self.__pi.write(self.__RELAY_MODULE['IN4'], 1)
                if self.__pi.wait_for_edge(
                    self.__GUILLOTINE_UP,
                    pigpio.FALLING_EDGE,
                    int(getenv('GUILLOTINE_UP_TIME'))
                ):
                    logger.error("Guillotine stays down")
                    self.__cancel_cutting = False
                    self.__error_handler(
                        "Awaria gilotyny", "Gilotyna nie została podniesiona")
                else:
                    logger.success("Guillotine released")

            self.__cancel_cutting = False
            logger.info("Cutting paused")
            raise OptinalException()

    def cancel_cutting(self):
        """
        Function which breaks cutting event
        """
        self.__cancel_cutting = True
        MachineControl.__is_executed= False

    def cut_rope(self):
        if not self.is_motor_on() and self.is_air_present(True) and self.is_guillotine_up():
            self.__custom_delay(int(getenv('GUILLOTINE_UP_TIME')))
            self.__pi.write(self.__RELAY_MODULE['IN4'], 0)
            self.__custom_delay(int(getenv('GUILLOTINE_DOWN_TIME')))
            if self.is_guillotine_up():
                logger.error("Guillotine stays up")
                MachineControl.__is_executed = False
                self.__error_handler(
                    "Awaria gilotyny", "Gilotyna nie została opuszczona")
            else:
                logger.success("Guillotine pressed")
            self.__pi.write(self.__RELAY_MODULE['IN4'], 1)
            self.__custom_delay(int(getenv('GUILLOTINE_UP_TIME')))

            if not self.is_guillotine_up():
                logger.error("Guillotine stays down")
                MachineControl.__is_executed = False
                self.__error_handler(
                    "Awaria gilotyny", "Gilotyna nie została podniesiona")
            else:
                logger.success("Guillotine released")

    def guillotine_press_circuit(self, state):
        """
        Function that enable the possibility of manual use of the guillotine or crimper
        """
        if state:
            self.__pi.write(self.__RELAY_MODULE['IN5'], 1)
            logger.info("Guillotine nad press circuit activated")
            MachineControl.__is_executed = False
        else:
            self.__pi.write(self.__RELAY_MODULE['IN5'], 0)
            logger.info("Guillotine nad press circuit deactivated")
            MachineControl.__is_executed = False

    def is_guillotine_press_circuit_active(self) -> bool:
        return bool(self.__pi.read(self.__RELAY_MODULE['IN5']))

    def get_winder_status(self) -> bool:
        return self.is_motor_on()


class MachineWorker(QtCore.QRunnable):

    def __init__(self, machine: MachineControl, action_name: Actions, *args, **kwargs):
        super().__init__()
        self.machine = machine
        self.action_name = action_name
        self.args = args
        self.kwargs = kwargs
        self.signals = Signals()

    def cancel_cutting_run(self):
        self.machine.cancel_cutting()

    def run(self):
        try:
            self.machine.execute(self.action_name, *self.args, **self.kwargs)
            self.signals.done.emit()
        except MachineException as e:
            e_title = e.title
            e_desc = e.description
            self.signals.error_signal.emit(e_title, e_desc)
        except OptinalException as e:
            self.signals.optional.emit()


if __name__ == '__main__':
    pi = pigpio.pi()
    mc = MachineControl(pi, Buzzer(pi))
    mc.is_air_present()
