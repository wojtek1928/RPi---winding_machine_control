import pigpio
import time


class RelayModule:
    # Dictionary of physical pins `'name of pin on relay module': RPi_BCM_GPIO_pin_number`
    __RELAY_MODULE = {
        'IN1': 21,  # Winder clockwise rotation START
        'IN2': 20, 	# Winder counterclockwise rotation START
        'IN3': 16,  # Winder rotation STOP
        'IN4': 12,  # Guillotine cut
        'IN5': 25,  # Guillotine/press circuit
        'IN6': 24,  # NOT USED
        'IN7': 23,  # NOT USED
        'IN8': 18   # NOT USED
    }

    __ON_TIME = 0.1  # Relay activation time expressed in seconds

    def __init__(self, pi: pigpio):
        self.__pi = pi
        # Setting pins for realy in OUT mode with HIGH values (disabled)
        for pin in self.__RELAY_MODULE.values():
            self.__pi.set_mode(pin, pigpio.OUTPUT)
            self.__pi.write(pin, 1)

    def winder_clockwise(self):
        self.__pi.write(self.__RELAY_MODULE['IN1'], 0)
        time.sleep(self.__ON_TIME)
        self.__pi.write(self.__RELAY_MODULE['IN1'], 1)

    def winder_counter_clockwise(self):
        self.__pi.write(self.__RELAY_MODULE['IN2'], 0)
        time.sleep(self.__ON_TIME)
        self.__pi.write(self.__RELAY_MODULE['IN2'], 1)

    def winder_STOP(self):
        self.__pi.write(self.__RELAY_MODULE['IN3'], 0)
        time.sleep(self.__ON_TIME)
        self.__pi.write(self.__RELAY_MODULE['IN3'], 1)

    def guillotine_press(self):
        self.__pi.write(self.__RELAY_MODULE['IN4'], 0)

    def guillotine_release(self):
        self.__pi.write(self.__RELAY_MODULE['IN4'], 1)

    def guillotine_press_circuit_activate(self):
        self.__pi.write(self.__RELAY_MODULE['IN5'], 0)

    def guillotine_press_circuit_deactivate(self):
        self.__pi.write(self.__RELAY_MODULE['IN5'], 1)
