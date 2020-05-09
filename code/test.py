from leaderelection import leaderElection
from time import sleep, clock
from threading import Timer, Thread
import random, sys

class Node:

    def __init__(self, _id: str):
        self._id = _id
        self.le = leaderElection(_id)
        self.timer_duration = 10
        self.timeout = self.new_timeout()
        print(self.timeout)

        self.run = True
        self.m_thread = self.start_thread()

    def start_thread(self):
        t = Thread(
            target=self.mining_thread,
            daemon=True,
            name=self._id+' Mining thread'
        )
        t.start()
        return t

    def new_timeout(self):
        return self.timer_duration + self.timer_duration*random.random()*2

    def mining_thread(self):
        start = clock()
        count = 0
        while self.run:
            count += 1
            if count > 500000:
                print(self.timeout - elapsed_time)
                count = 0
            elapsed_time = clock() - start
            if elapsed_time > self.timeout:
                print(elapsed_time, self.timeout)
                self.le.request_leadership()
                count2 = 0
                while elapsed_time < self.timer_duration + 6:
                    count2 += 1
                    if count2 >10000:
                        print('requesting leadership')
                        count2 = 0
                    elapsed_time = clock() - start
                    if self.le.election_state == 'leader':
                        print('\n***********************************\n', self._id, ' leadership acquired', '\n***********************************\n')
                        # sleep(3)
                        self.le.release_leadership()
                        print("LEADERSHIP RELEASED")
                        break
                print('\n***********************************\n', self._id, ' leadership request timer elapsed, restarting',
                     '\n***********************************\n')
                print('')
                start = clock()
                self.timeout = self.new_timeout()

if __name__ == '__main__':
    arg = sys.argv[1]
    n = Node(arg)

