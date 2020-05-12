from time import sleep, clock
from threading import Thread, Timer
import random


class ElectionTimer:

    def __init__(self, duration: float, target):
        """
        Creates a timer to reset elections every time a 'term' has elapsed.

        :param duration:
        :param target:
        """
        self.target = target
        self.duration = duration
        self.running = False
        self.restart = False
        self.stop = False

        t = Thread(
            target=self.run,
            name='Election Timer Thread'
        )
        t.start()

    def kill_thread(self):
        self.running = False

    def stop_timer(self):
        self.stop = True

    def restart_timer(self):
        self.restart = True
        self.stop = False

    def new_timeout(self) -> float:
        return self.duration + 2 * self.duration * random.random()

    def run(self):
        # randomize timeouts to avoid conflicting elections
        timeout = self.new_timeout()
        # start the timer
        start = clock()
        count = 0
        while self.running:
            while not self.stop:
                count += 1
                if self.restart:
                    timeout = self.new_timeout()
                    start = clock()
                    self.restart = False

                elapsed_time = clock() - start
                if elapsed_time > timeout:
                    print('\nCountodwn elapsed ', timeout, ',', self.target._id, ' Starting Election       \n')
                    self.target.request_leadership()
                    self.restart_timer()
                    break
                else:
                    if count > 200000:
                        print('Election Timer: ', timeout - elapsed_time)
                        count = 0
