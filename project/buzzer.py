import pigpio
import time


class Buzzer:
    def __init__(self, pi: pigpio):
        self.__pi = pi
        self.__BUZZER_PIN = 19

        self.__pi.set_mode(self.__BUZZER_PIN, pigpio.OUTPUT)

    def beep_once(self):
        self.__pi.set_PWM_frequency(self.__BUZZER_PIN, 5000)
        self.__pi.set_PWM_dutycycle(self.__BUZZER_PIN, 150)
        for i in range(4):
            time.sleep(0.5)
            self.__pi.set_PWM_frequency(self.__BUZZER_PIN, 2000)
            time.sleep(0.75)
            self.__pi.set_PWM_frequency(self.__BUZZER_PIN, 1500)

        self.__pi.set_PWM_dutycycle(self.__BUZZER_PIN, 0)


if __name__ == "__main__":
    pi = pigpio.pi()
    buzzer = Buzzer(pi=pi)
    buzzer.beep_once()
