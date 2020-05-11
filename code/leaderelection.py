from ElectionMessenger import Messenger
from ElectionTimer import Election_Timer
from Heartbeat import Heartbeat
import math, sys
from time import sleep


class leaderElection:

    def __init__(self, _id: str):
        self._id = _id
        self.nodes = ['0', '1', '2', '3']
        self.peers = [node for node in self.nodes if node != self._id]

        self.term = 0
        self.election_state = 'follower'
        self.current_leader = ''
        self.timer_length = 3
        self.vote_count = 0
        self.voted_for = 'null'
        self.vote_received_from = {}
        self.reset_votes_received()

        self.m = Messenger(self._id, self)
        self.e = Election_Timer(self.timer_length, self)
        self.h = Heartbeat(self.timer_length, self)

    def reset_votes_received(self):
        for peer in self.peers:
            self.vote_received_from[peer] = False

    def set_follower(self, term: int):
        self.term = term
        # print(self._id, " set state to follower")
        self.election_state = 'follower'
        self.vote_count = 0
        self.voted_for = 'null'
        self.reset_votes_received()
        self.h.stop_timer()

    def set_leader(self):
        # print(self._id, ' set state to leader')
        self.election_state = 'leader'
        self.e.stop_timer()
        self.send_heartbeat()
        self.h.restart_timer()

    def release_leadership(self):
        #print(self._id, " leadership released!")
        self.h.stop_timer()
        self.set_follower(self.term)
        self.send_to_peers('release', 'empty')

    def request_leadership(self):
        #print(self._id, ' start election')
        self.term += 1
        self.election_state = 'candidate'
        self.voted_for = self._id
        self.vote_count = 1
        self.send_to_peers(type='request_votes', contents=self._id)
        # if timer elapses during request for leadership, set to follower

    def send_to_peers(self, type: str, contents: str):
        msg = {'type': type, 'contents': contents, 'term': str(self.term)}
        for peer in self.peers:
            self.m.send(msg, peer)

    def send_heartbeat(self, contents: str = 'empty'):
        if self.election_state == 'leader':
            msg = {'type': 'heartbeat', 'contents': contents, 'term': str(self.term)}
            for peer in self.peers:
                self.m.send(msg, peer)

    def handle_incoming_message(self, message: dict):
        #print(self._id, ' Message received: ', message)
        incoming_term = int(message['term'])
        if incoming_term > self.term and self.election_state != 'leader':
            self.set_follower(incoming_term)
        message_type = message['type']
        if message_type == 'heartbeat':
            self.receive_heartbeat(message)
        elif message_type == 'request_votes':
            self.receive_vote_request(message)
        elif message_type == 'vote_reply':
            self.receive_vote_reply(message)
        elif message_type == 'release':
            # sent by leader to release all "voted for" and reset state to followers
            self.set_follower(incoming_term)
        elif message_type == 'leader_exists' and self.election_state == 'candidate':
            self.set_follower(incoming_term)

    def receive_heartbeat(self, message: dict):
        # print('heartbeat received')
        incoming_term = int(message['term'])
        if self.election_state == 'candidate':
            self.set_follower(incoming_term)
        elif self.election_state == 'follower':
            self.e.restart_timer()

    def receive_vote_request(self, message: dict):
        candidate = message['contents']
        if self.election_state != 'leader':
            vote_granted = 'False'
            # print(self._id, ' initial voted for: ', self.voted_for)
            if self.voted_for == 'null':
                self.voted_for = candidate
            if self.voted_for == candidate:
                #print(self._id, ' voted for ', candidate)
                vote_granted = 'True'
            self.m.send({'type': 'vote_reply', 'contents': vote_granted, 'term': str(self.term), 'sender': self._id},
                        candidate)
        else:
            self.m.send({'type': 'leader_exists', 'contents': 'none', 'term': str(self.term)}, candidate)

    def receive_vote_reply(self, message: dict):
        vote_granted = message['contents']
        incoming_term = int(message['term'])
        sender = message['sender']
        if self.election_state == 'candidate' and incoming_term == self.term:
            self.vote_received_from[sender] = True
            response_from_all = True
            if vote_granted == 'True':
                self.vote_count += 1
            for k, v in self.vote_received_from.items():
                if not v:
                    response_from_all = False
            if self.vote_count > math.floor(len(self.peers)/2) and response_from_all:
                self.set_leader()



if __name__ == '__main__':
    arg = sys.argv[1]

    le = leaderElection(arg)
    sleep(2)
    if le._id == '1':
        le.request_leadership()