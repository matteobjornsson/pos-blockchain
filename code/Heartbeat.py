from time import sleep, clock
from threading import Thread, Timer
import random

class Heartbeat:

    def __init__(self, duration: float, target):
        self.target = target
        self.duration = duration/8
        self.running = True
        self.restart = False
        self.stop = True

        t = Thread(
            target=self.run,
            name='Heartbeat Thread'
        )
        t.start()

    def kill_thread(self):
        self.running = False

    def stop_timer(self):
        self.stop = True

    def restart_timer(self):
        self.restart = True
        self.stop = False

    #def new_timeout(self) -> float:
    #   return (self.duration + self.duration * random.random())

    def run(self):
        #start the timer
        start = clock()
        count = 0
        while self.running:
            while not self.stop:
                count+=1
                if self.restart:
                    start = clock()
                    self.restart = False

                elapsed_time = clock() - start
                if elapsed_time > self.duration:
                    if self.target.election_state == 'leader':
                        print('\nSending Heartbeat ........       \n')
                        self.target.send_heartbeat()
                        self.restart = True
                    break
                else:
                    if count > 10000:  
                        print('Heartbeat Timer: ', self.duration-elapsed_time)  
                        count = 0
