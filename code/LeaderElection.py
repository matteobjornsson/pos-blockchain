from ElectionMessenger import Messenger
from ElectionTimer import ElectionTimer
from Heartbeat import Heartbeat
import math, sys
from time import sleep


class LeaderElection:
    def __init__(self, _id: str):
        """
        Constructor for leader election.
        Main class to elect which node becomes leader.

        :param _id: str. Which node this object belongs to.
        """
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
        self.e = ElectionTimer(self.timer_length, self)
        self.h = Heartbeat(self.timer_length, self)

    def reset_votes_received(self):
        """
        Reset leader election so no node had any votes.
        :return:
        """
        for peer in self.peers:
            self.vote_received_from[peer] = False

    def set_follower(self, term: int):
        """
        Set election state and all attributes to follower.

        :param term: int. What term is the election in?
        :return:
        """
        self.term = term
        self.election_state = 'follower'
        self.vote_count = 0
        self.voted_for = 'null'
        self.reset_votes_received()
        self.h.stop_timer()

    def set_leader(self):
        """
        Set election state and all attributes to leader.

        :return:
        """
        self.election_state = 'leader'
        self.e.stop_timer()
        self.send_heartbeat()
        self.h.restart_timer()

    def release_leadership(self):
        """
        Force node to stop being leader.

        :return:
        """
        self.h.stop_timer()
        self.set_follower(self.term)
        self.send_to_peers('release', 'empty')

    def request_leadership(self):
        """
        Set node to candidate status, notifying followers of its intentions.

        :return:
        """
        self.term += 1
        self.election_state = 'candidate'
        self.voted_for = self._id
        self.vote_count = 1
        self.send_to_peers(type='request_votes', contents=self._id)
        # if timer elapses during request for leadership, set to follower

    def send_to_peers(self, type: str, contents: str):
        """
        Send message to all other nodes.

        :param type: str. What is the message type
        :param contents: str. What the message contains
        :return:
        """
        msg = {'type': type, 'contents': contents, 'term': str(self.term)}
        for peer in self.peers:
            self.m.send(msg, peer)

    def send_heartbeat(self, contents: str = 'empty'):
        """
        Send a heartbeat to check liveness of nodes.

        :param contents:
        :return:
        """
        if self.election_state == 'leader':
            msg = {'type': 'heartbeat', 'contents': contents, 'term': str(self.term)}
            for peer in self.peers:
                self.m.send(msg, peer)

    def handle_incoming_message(self, message: dict):
        """
        Method necessary when initializing Messenger thread to process messages from queue.

        :param message: The incoming message dictionary: type and contents
        :return:
        """
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
        """
        Upon receiving heartbeat, change timers.

        :param message:
        :return:
        """
        incoming_term = int(message['term'])
        if self.election_state == 'candidate':
            self.set_follower(incoming_term)
        elif self.election_state == 'follower':
            self.e.restart_timer()

    def receive_vote_request(self, message: dict):
        """
        Actions to undertake when a follower receives a vote request from a candidate.

        :param message:
        :return:
        """
        candidate = message['contents']
        if self.election_state != 'leader':
            vote_granted = 'False'
            if self.voted_for == 'null':
                self.voted_for = candidate
            if self.voted_for == candidate:
                vote_granted = 'True'
            self.m.send({'type': 'vote_reply', 'contents': vote_granted, 'term': str(self.term), 'sender': self._id},
                        candidate)
        else:
            self.m.send({'type': 'leader_exists', 'contents': 'none', 'term': str(self.term)}, candidate)

    def receive_vote_reply(self, message: dict):
        """
        Actions to take when you receive a vote as a candidate. If you receive majority of votes, you become leader.

        :param message:
        :return:
        """
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

    le = LeaderElection(arg)
    sleep(2)
    if le._id == '1':
        le.request_leadership()