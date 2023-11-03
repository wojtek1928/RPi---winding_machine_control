import time
import threading
from loguru import logger


class Stopwatch:
    """
    `Stopwatch` measure the time as seperate thread.
    """
    __measuerd_time = 0
    __time_before_paused = 0
    __is_running = False

    def __init__(self):
        self.__logs: logger = logger

    def run(self):
        """
        Run `stopwatch`
        """
        if not self.__is_running:
            self.__is_running = True
            self.start_time = time.time()
            time_thread = threading.Thread(
                target=self.__measurement, daemon=True, name="Stopwatch_thread")
            time_thread.start()
            self.__logs.info("Stopwatch started")

    def pause(self):
        """
        Pause the `stopwatch`
        """
        self.__is_running = False
        self.__time_before_paused = self.__measuerd_time
        self.__logs.info("Stopwatch stopped")

    def reset(self):
        """
        Reset the `stopwatch`
        """
        self.__measuerd_time = 0
        self.__time_before_paused = 0
        self.__is_running = False
        self.__logs.info("Stopwatch reset")

    def __measurement(self):
        while self.__is_running:
            self.__measuerd_time = time.time() - self.start_time + \
                self.__time_before_paused
            time.sleep(0.001)
            # os.system("cls")
            # print(self)

    def __str__(self) -> str:
        """
        Return measured time in format `hh:mm:ss` as `str`
        """
        # Convert the current_time to hours, minutes and seconds
        hours = int(self.__measuerd_time // 3600)
        minutes = int((self.__measuerd_time % 3600) // 60)
        seconds = int(self.__measuerd_time % 60)
        # Return measured time in format hh:mm:ss
        return (f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def get_time(self):
        return self.__measuerd_time


if __name__ == "__main__":
    # IMPORTANT uncomment line 32 and 33 before testing
    stopwatch_test = Stopwatch()
    stopwatch_test.run()
    time.sleep(5)
    stopwatch_test.run()
    time.sleep(3)
    stopwatch_test.pause()
    time.sleep(2)
    stopwatch_test.run()
    time.sleep(3)
    stopwatch_test.pause()
    print(stopwatch_test)
    stopwatch_test.reset()
    print(stopwatch_test)
