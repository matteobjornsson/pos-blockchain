from Ledger import *
from Transaction import Transaction
from Ledger import Ledger
from BlockChain import BlockChain
from leaderelection import leaderElection
from Block import Block
from Messenger import Messenger
from threading import Thread, enumerate, Timer
from time import sleep, clock
from datetime import datetime
from dateutil import parser as date_parser
import  json, hashlib, copy, collections, sys, random, math


class Node:

    def __init__(self, node_id: str):
        """
        Constructor for the Node class.

        :param str node_id: one of '0', '1', '2', or '3', the possible nodes in network
        """
        self.node_id = node_id
        self.file_path = '../files/blockchain' + node_id + '.txt'
        # self.ledger = Ledger(node_id)
        # self.blockchain = BlockChain(self.node_id, self.ledger)
        self.probability = 0.8
        self.term_duration = 10
        self.le = leaderElection(self.node_id)
        # self.elected_boolean = False

        self.messenger = Messenger(self.node_id, self)
        self.peers = [peer for peer in ['0', '1', '2', '3'] if peer != self.node_id]
        self.transaction_queue = []

        self.signatures = []
        self.received_blocks = collections.deque()

        self.nodes_online = []
        self.sync_nodes()
        self.genesis_time = 'not set'
        self.term = 0

        self.start_mining_thread()

    def sync_nodes(self):
        start_time = datetime.now()
        self.nodes_online.append(start_time)
        self.send_blockchain_msg(type='sync', contents=str(start_time))





    def start_mining_thread(self) -> Thread:
        """
        Starts the thread that continually mines new blocks to add to the chain.

        :return: mining thread
        """
        t = Thread(
            target=self.mining_thread,
            name=('Mining Threads' + self.node_id)
        )
        t.start()
        print('mining thread started')
        return t

    def mining_thread(self):
        while True:
            if self.genesis_time != 'not set':
                term = self.term
                time_diff = datetime.now() - self.genesis_time
                time_diff = time_diff.seconds
                new_term = math.ceil(time_diff/self.term_duration)
                if new_term > term:
                    # reset all flags
                    self.term = new_term
                    self.mine_block(self.term)

    def mine_block(self, term: int):
        sleep(random.random()*2)
        self.le.request_leadership()
        sleep(5)
        if self.le.election_state != 'leader':
            print('no leader elected')
            return
        sleep(.5)
        print("I hope I'm leader!!! : ", self.le.election_state)
        self.le.release_leadership()





    # # TODO: rewrite s.t. mining function is based on 20 second delay, randomized approach + leader election
        # # mine a block
        # mined_probability = random.random()
        # if mined_probability > self.probability:
        #     new_block = Block() # creating block
        #     # self.send_leaderelection_msg()
        #     # # self.le.request_leadership()
        #     # if self.le.election_state == 'leader':
        #     #     self.send_blockchain_msg(new_block)


    def handle_incoming_message(self, msg: dict):
        """
        Handles incoming messages from the Messenger class in dictionary format.

        :param msg: dict. Message attributes represented as string key value pairs.
        :return: None
        """

        if msg['type'] == 'Transaction':  # if transaction append to tx queue
            self.transaction_queue.append(Transaction(msg['contents']))

        elif msg['type'] == 'Block':  # if block process and reset mine function if valid
            incoming_block = Block(msg['contents'])
            print("\nIncoming Block received: \n", "Index: ", incoming_block.index, '\n')
            self.received_blocks.append(incoming_block)
        elif msg['type'] == 'sync':
            start_time = date_parser.parse(msg['contents'])
            self.nodes_online.append(start_time)
            if len(self.nodes_online) > 3:
                print("synched!")
                self.genesis_time = max(self.nodes_online)
                print('genesis time = ', self.genesis_time)
        #elif receive election_msg:
        #

    def process_incoming_block(self):
        incoming_block = self.received_blocks.popleft()
        # process block returns true if it is valid and added to blockchain and ledger
        if self.le.check_leader_status == 'follower':
            if self.blockchain.verify_block(incoming_block):
                # if the block is valid, then we need to remove all transactions from our own tx queue
                delete_transactions = copy.deepcopy(incoming_block.transactions)
                self.transaction_queue = [x for x in self.transaction_queue if x not in delete_transactions]
                # if verified: sign block
                # TODO : sign and reply to leader that block was verified

        elif self.le.check_leader_status == 'leader':
            # verify sum of signature stakes to make sure block wass igned by enough nodes
            # if it is: cmmit to blockchain,
            # else: send renewed block to collect more signatures.
            pass

    def send_blockchain_msg(self, contents: str, type: str):
        """
        sends msgs to all peers

        :param contents: str. Newly mined blocks or new transactions in JSON string representation.
        :param type: str. indicates type of msg. 'Block' or 'Transaction'
        :return: None
        """
        # send block to all known peers
        msg_dict = {'contents': contents, 'type': type}
        for peer in self.peers:
            self.messenger.send(msg_dict, peer)

if __name__ == '__main__':
    n0 = Node('0')
    n1 = Node('1')
    n2 = Node('2')
    n3 = Node('3')

    print('constructors finished')
    synched = False
    count = 0
    while not synched:
        count = 0
        for n in [n0, n1, n2, n3]:
            synched_nodes = len(n.nodes_online)
            if synched_nodes > 3:
                count += 1
        if count == 4:
            sleep(1)
            break