from os import getenv
import threading
import pigpio
import time
from enum import Enum
from functools import partial


class Buzzer:
    __is_executed = False
    __cancel_buzzer_event = None

    def __init__(self, pi: pigpio):
        self.__pi: pigpio.pi = pi
        # Set RPi GPIO pin number
        self.__BUZZER_PIN = 13
        self.__pi.set_mode(self.__BUZZER_PIN, pigpio.OUTPUT)

    # Define available signals
    class Signals(str, Enum):
        start_signal = "start"
        stop_signal = "stop"
        end_signal = "end"
        error_signal = "error"

    def __custom_delay(self, duration: float):
        """
        This method corresponds to the `time.sleep()` function, 
        but it also checks if the event 'self.__cancel_buzzer_event' is not set.
        If an event is set, then the function raises an `Exception` that is caught by the `Buzzer_thread` main function.
        """
        start = time.time()
        while time.time() - start < duration and not self.__cancel_buzzer_event.is_set():
            pass

        if self.__cancel_buzzer_event.is_set():
            raise Exception()

    def __start_signal(self):
        """
        `Low tone` for 0.15 sec and `high tone` for 0.25 sec
        """
        self.__pi.set_PWM_frequency(self.__BUZZER_PIN, 1)
        self.__pi.set_PWM_dutycycle(self.__BUZZER_PIN, 255)
        self.__custom_delay(0.15)
        self.__pi.set_PWM_dutycycle(self.__BUZZER_PIN, 128)
        self.__pi.set_PWM_frequency(self.__BUZZER_PIN, 5000)
        self.__custom_delay(0.25)
        self.__pi.set_PWM_dutycycle(self.__BUZZER_PIN, 0)

    def __stop_signal(self):
        """
        `High tone` for 0.15 sec and `low tone` for 0.25 sec
        """
        self.__pi.set_PWM_dutycycle(self.__BUZZER_PIN, 128)
        self.__pi.set_PWM_frequency(self.__BUZZER_PIN, 5000)
        self.__custom_delay(0.15)
        self.__pi.set_PWM_frequency(self.__BUZZER_PIN, 1)
        self.__pi.set_PWM_dutycycle(self.__BUZZER_PIN, 255)
        self.__custom_delay(0.25)
        self.__pi.set_PWM_dutycycle(self.__BUZZER_PIN, 0)

    def __end_signal(self):
        """
        Beeps 3 times for 15 seconds with 1 second breaks
        """
        for cycle in range(3):
            self.__pi.set_PWM_frequency(self.__BUZZER_PIN, 2000)
            self.__pi.set_PWM_dutycycle(self.__BUZZER_PIN, 128)
            self.__custom_delay(3)
            self.__pi.set_PWM_dutycycle(self.__BUZZER_PIN, 0)
            self.__custom_delay(1)

    def __error_signal(self):
        """
        Beeps 20 times for 20 seconds with 0.5 second breaks
        """
        self.__pi.set_PWM_frequency(self.__BUZZER_PIN, 1)
        self.__pi.set_PWM_dutycycle(self.__BUZZER_PIN, 128)
        self.__custom_delay(30)
        self.__pi.set_PWM_dutycycle(self.__BUZZER_PIN, 0)

    def cancel_buzzer(self):
        if self.__cancel_buzzer_event:
            self.__cancel_buzzer_event.set()

    def __run_signal(self, signal_name: Signals, event: threading.Event):
        """
        Runs selected signal inside thread. At the end free the object
        """
        try:
            if signal_name == self.Signals.start_signal:
                self.__start_signal()
            elif signal_name == self.Signals.stop_signal:
                self.__stop_signal()
            elif signal_name == self.Signals.end_signal:
                self.__end_signal()
            elif signal_name == self.Signals.error_signal:
                self.__error_signal()

        # Catch exception and cancel `Buzzer_thread`
        except:
            # Disable pwm on `__BUZZER_PIN`
            self.__pi.set_PWM_dutycycle(self.__BUZZER_PIN, 0)

        delattr(self, 'signal_thread')
        self.__cancel_buzzer_event = None
        # Set static `__is_executed` flag to `false`
        Buzzer.__is_executed = False

    def signal(self, signal_name: Signals):
        """
        Available signals:
        - start - `0.15 sec `LOW beep - `0.25 sec` HIGH beep = `0.4sec`
        - stop - `0.15 sec `HIGH beep - `0.25 sec` LOW beep = `0.4sec`
        - end - 3 X (`4 sec` beep - `1 sec` silent) = `15sec`
        - error - 20 X (`0.5 `sec beep - `0.5 sec` silent) = `20sec`
        """
        if signal_name == "error" or (getenv("BUZZER_SIGNALS", 'False') == 'True'):
            if not hasattr(self, 'signal_thread') and Buzzer.__is_executed == False:

                # Create cancel event
                self.__cancel_buzzer_event = threading.Event()

                self.signal_thread = threading.Thread(
                    target=partial(self.__run_signal, signal_name,
                                self.__cancel_buzzer_event),
                    name="Buzzer_thread")

                Buzzer.__is_executed = True
                self.signal_thread.start()


if __name__ == "__main__":
    pi = pigpio.pi()
    buzzer = Buzzer(pi=pi)
    buzzer.signal('error')
    # time.sleep(2)
    # print("2s")
    # buzzer.signal('end')
    # time.sleep(2)
    # print("4s")
    buzzer.cancel_buzzer()
