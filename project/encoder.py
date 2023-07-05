import pigpio
import time
import threading


class Encoder:
    # Measured distance value in [mm]
    __measured_length = 0
    # Distance in mm per one puls [mm/puls]. Circumference of measuring wheel is 200 mm and encoder gives 3600 pulses per rotation.
    _step_in_mm = 200/3600

    def __init__(self, pi: pigpio):
        self.__pi = pi
        self.A = 17     # RPi BCM GPIO pin id for signal A input
        self.B = 27     # RPi BCM GPIO pin id for signal B input
        self.__direction = None
        self.signal_thread = None

        self.__pi.set_mode(self.A, pigpio.INPUT)
        self.__pi.set_mode(self.B, pigpio.INPUT)

    def __signal(self, gpio, level, tick):
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
        return str(int(self.__measured_length))

    def __int__(self) -> int:
        return int(self.__measured_length)

    def __measurement(self):
        # Callback is active only for signal A falling edge
        A_cb = self.__pi.callback(self.A, pigpio.FALLING_EDGE, self.__signal)
        # Callback activates whenever signal B changes state
        B_cb = self.__pi.callback(self.B, pigpio.EITHER_EDGE, self.__signal)

        while not self.stop_event.is_set():
            time.sleep(0.0000001)

        A_cb.cancel()
        B_cb.cancel()

    def begin_measurement(self):
        if not self.is_measurement_active():
            self.stop_event = threading.Event()
            self.signal_thread = threading.Thread(
                target=self.__measurement, daemon=True, name="Enocder_thread")
            self.signal_thread.start()

    def is_measurement_active(self) -> bool:
        return hasattr(self, 'stop_event') and not self.stop_event.is_set()

    def pause_measurement(self):
        if self.is_measurement_active():
            self.stop_event.set()

    def reset_measurement(self):
        self.__measured_length = 0


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
