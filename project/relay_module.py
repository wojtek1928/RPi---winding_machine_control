import pigpio
import time
import threading

from PyQt5.QtWidgets import QPushButton


class RelayModule:
    # Dictionary of physical pins `'name of pin on relay module': RPi_BCM_GPIO_pin_number`
    __RELAY_MODULE = {
        # Winder clockwise rotation START (running unntill STOP is executed)
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

    __HALL_SENSOR = 22  # Pin connected to Hall sensor
    __MOTOR_STATUS_PIN = None   # Pin connected to winder motor relay

    __ON_TIME = 0.1  # Relay activation time expressed in seconds

    __is_running = False    # Contains the status of the winder motor relay

    def __init__(self, pi: pigpio):
        self.__pi: pigpio
        self.__pi = pi
        # Set the pins of the relay module in OUT mode to HIGH (relays off)
        for pin in self.__RELAY_MODULE.values():
            self.__pi.set_mode(pin, pigpio.OUTPUT)
            self.__pi.write(pin, 1)
        # Set the pin of Hall sensor in INPUT mode
        self.__pi.set_mode(self.__HALL_SENSOR, pigpio.INPUT)
        # Set and start the thread for checking the winder motor status
        self.check_motor_status_thread = threading.Thread(
            target=self.check_motor_status, daemon=True)
        # self.check_motor_status_thread.start()

    # Winder motor relay status check function
    def check_motor_status(self):
        pass

    # The function of starting the winder in a clockwise direction
    def winder_clockwise(self):
        if not self.__is_running:
            self.__is_running = True
            self.__pi.write(self.__RELAY_MODULE['IN1'], 0)
            time.sleep(self.__ON_TIME)
            self.__pi.write(self.__RELAY_MODULE['IN1'], 1)

    # The function of starting the winder in a counter-clockwise direction
    def winder_counter_clockwise(self, state: bool):
        if state:
            if not self.__is_running:
                self.__is_running = True
                self.__pi.write(self.__RELAY_MODULE['IN2'], 0)
        else:
            self.__pi.write(self.__RELAY_MODULE['IN2'], 1)
            self.__is_running = False

    # The function of stopping the winder
    def winder_STOP(self):
        self.__pi.write(self.__RELAY_MODULE['IN3'], 0)
        time.sleep(self.__ON_TIME)
        self.__pi.write(self.__RELAY_MODULE['IN3'], 1)
        self.__is_running = False

    # Function which brings hook on the wheel to zero position
    def winder_reset_position(self, activationFunction=None):
        # activationFunction is function for enable disabled winder buttons
        if self.__pi.read(self.__HALL_SENSOR) == 1:
            if callable(activationFunction):
                activationFunction(True)

        else:
            if not self.__is_running:
                def finding_zero():
                    start_time = time.time()
                    searching_time = 10
                    # Start winder
                    self.winder_clockwise()

                    while self.__pi.read(self.__HALL_SENSOR) == 0:
                        # If zero point is not detected in 10 seconds that means the hardware failure
                        if (time.time()-start_time) > searching_time:
                            print(
                                "Error: Winder or Hall sensor or some relay failure")
                            break
                        # Handling the winder stopped event
                        elif self.__is_running == False:
                            print("The winder stopped")
                            break
                        time.sleep(0.001)

                    print("Done")
                    self.winder_STOP()
                    if callable(activationFunction):
                        activationFunction(True)

                finding_zero_thread = threading.Thread(
                    target=finding_zero, daemon=True)

                finding_zero_thread.start()

    # The guillotine press function
    def guillotine_press(self, state: bool):
        if self.__is_running == False:
            if state:
                self.__pi.write(self.__RELAY_MODULE['IN4'], 0)
            else:
                self.__pi.write(self.__RELAY_MODULE['IN4'], 1)

    # Function that enable the possibility of manual use of the guillotine or crimper
    def guillotine_press_circuit_activate(self):
        self.__pi.write(self.__RELAY_MODULE['IN5'], 0)

    # Function that enable the possibility of manual use of the guillotine or crimper
    def guillotine_press_circuit_deactivate(self):
        self.__pi.write(self.__RELAY_MODULE['IN5'], 1)

    def get_winder_status(self) -> bool:
        return self.__is_running


if __name__ == '__main__':
    pi = pigpio.pi()
    rm = RelayModule(pi)
