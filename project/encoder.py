import pigpio
import time
import threading


class Encoder:
    __measured_length = 0   # Measured distance value in [mm]
    # Distance in mm per one puls [mm/puls]. Circumference of measuring wheel is 200 mm and encoder gives 3600 pulses per rotation.
    _step_in_mm = 200/3600
    __measurement_proccess = False

    def __init__(self, pi:pigpio):
        self.__pi = pi
        self.A = 17     # RPi BCM GPIO pin id for signal A input
        self.B = 27     # RPi BCM GPIO pin id for signal B input
        self.__direction = None

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

    def get_distace(self, digits) -> float:
        return round(self.__measured_length, digits)

    def begin_measurement(self):
        signal_thread = threading.Thread(target=self.__measurement, daemon=True)
        signal_thread.start()

    def __measurement(self):
        # Callback is active only for signal A falling edge
        A_cb = self.__pi.callback(self.A, pigpio.FALLING_EDGE, self.__signal)
        # Callback activates whenever signal B changes state
        B_cb = self.__pi.callback(self.B, pigpio.EITHER_EDGE, self.__signal)

        self.__measurement_proccess = True
        while self.__measurement_proccess:
            time.sleep(0.0000001)
        A_cb.cancel()
        B_cb.cancel()

    def pause_measurement(self):
        self.__measurement_proccess = False

    def reset_measurement(self):
        self.__measured_length = 0

    def is_measurement_active(self) -> bool:
        return self.__measurement_proccess


if __name__ == "__main__":
    pi = pigpio.pi()
    encoder = Encoder(pi)
    try:
        i = 0
        while i < 100:
            print("A:", encoder.get_distace(2), "\t\t\t| i:", i,
                  " \t| Measurement proccess:", encoder._Encoder__measurement_proccess, sep=" ")
            time.sleep(0.1)

            if i > 10 and i < 20:
                encoder.pause_measurement()
            elif i == 50:
                encoder.reset_measurement()
            else:
                encoder.begin_measurement()

            i += 1

    except KeyboardInterrupt:
        pigpio.stop()
