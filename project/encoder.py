import pigpio
import time
import threading
from loguru import logger


class Encoder:
    """
    Encoder 
    ---

    `Encoder` class accuires and handles signals from an encoder connected to the RaspberryPi using `pigpio`. 
    The use of the `pigpio` library is important because the stadard `RPi.GPIO` library is too slow for a high resolution encoder and lose signals at even relative low speed.

    Parameters
    ---

    :pi: instance of `pigpio.pi`

    More information about `pigpio` module available on site: http://abyz.me.uk/rpi/pigpio/python.html
    """
    # Measured distance value in [mm]
    __measured_length = 0
    # Distance in mm per one puls [mm/puls]. Circumference of measuring wheel is 200 mm and encoder gives 3600 pulses per rotation.
    _step_in_mm = 200/3600

    def __init__(self, pi: pigpio.pi,):
        """
        Assign pin numbers for  each signal A and B. Sets the mode of 
        """
        self.__pi: pigpio.pi = pi
        self.A = 5     # RPi BCM GPIO pin id for signal A input
        self.B = 6     # RPi BCM GPIO pin id for signal B input
        self.__direction = None
        self.signal_thread = None

        self.__pi.set_mode(self.A, pigpio.INPUT)
        self.__pi.set_mode(self.B, pigpio.INPUT)

    def __signal(self, gpio: int, level: int, tick: int):
        """
        Counts the signals from encoder and increment/decrement depends on rotation direction the value of `__measured_length`.  
        Dedicated to using with `pigio.callback()` funtion. 

        Parameters:
        --
        :GPIO (0-31): - The GPIO which has changed state

        :level (0-2):
            - `0` = change to low (a falling edge)
            - `1` = change to high (a rising edge)
            - `2` = no level change (a watchdog timeout)

        :tick (32 bit): The number of microseconds since boot

        `WARNING:` tick wraps around from 4294967295 to 0 roughly every 72 minutes
        """
        if gpio == self.A:
            # The encoder rotates clockwise when the rising edge of signal B is ahead of the falling edge of signal A.
            if self.__direction:
                self.__measured_length += self._step_in_mm
            else:
                self.__measured_length -= self._step_in_mm
        elif gpio == self.B:
            # level is 1 for raising ege and 0 for falling
            if level:
                self.__direction = 1
            else:
                self.__direction = 0

    def __str__(self) -> str:
        """
        Returns value of `__measured_length` in `str` format
        """
        return str(int(self.__measured_length))

    def __int__(self) -> int:
        """
        Returns value of `__measured_length` in `int` format
        """
        return int(self.__measured_length)

    def __measurement(self):
        """
        Private function working inside `signal_thread` thread
        """
        # Callback activates only for signal A falling edge
        A_cb = self.__pi.callback(self.A, pigpio.FALLING_EDGE, self.__signal)
        # Callback activates whenever signal B changes state
        B_cb = self.__pi.callback(self.B, pigpio.EITHER_EDGE, self.__signal)

        while not self.stop_event.is_set():
            time.sleep(0.0000001)

        A_cb.cancel()
        B_cb.cancel()

    def begin_measurement(self):
        """
       Function begin the measuring process, only  if `signal_thread` is not already running
        """
        if not self.is_measurement_active():
            self.stop_event = threading.Event()
            self.signal_thread = threading.Thread(
                target=self.__measurement, daemon=True, name="Enocder_thread")
            self.signal_thread.start()
            logger.info("Measurement started")

    def is_measurement_active(self) -> bool:
        """
        Function returns `True` if object has a `stop_event` attribute and if flag of `stop_event` is `True` 
        """
        return hasattr(self, 'stop_event') and not self.stop_event.is_set()

    def pause_measurement(self):
        """
        Function ends the `signal_thread` thread only if thread is running 
        """
        if self.is_measurement_active():
            self.stop_event.set()
            logger.info("Measurement stopped")

    def reset_measurement(self):
        """
        Function which reset the `__measured_length` to 0 value.

        IMPORTANT:
        ---
        This function do NOT stop the `signal_thread`. If this `signal_thread` is running signals from encoder are still accuired. 
        """
        self.__measured_length = 0
        logger.info("Measurement reset")


if __name__ == "__main__":
    pi = pigpio.pi()
    encoder = Encoder(pi)
    try:
        i = 0

        while i < 100:

            time.sleep(0.1)

            if i > 10 and i < 20:
                encoder.pause_measurement()
            elif i == 50:
                encoder.reset_measurement()
            else:
                encoder.begin_measurement()

            print("A:", encoder.__str__(), "\t\t\t| i:", i,
                  " \t| Measurement proccess:", encoder.is_measurement_active(), sep=" ")
            i += 1
        i = 1
        for thread in threading.enumerate():
            print(f"Thread #{i}: {thread.is_alive()} \t|\t {thread}")
            i += 1

    except KeyboardInterrupt:
        pigpio.stop()
