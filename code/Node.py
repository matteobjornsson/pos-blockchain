from Ledger import *
from Transaction import Transaction
from Ledger import Ledger
from BlockChain import BlockChain
from Block import Block
from Messenger import Messenger
from threading import Thread, enumerate, Timer
from time import sleep
import datetime, json, hashlib, copy, collections, sys, random


class Node:

    def __init__(self, node_id: str):
        """
        Constructor for the Node class.

        :param str node_id: one of '0', '1', '2', or '3', the possible nodes in network
        """
        self.node_id = node_id
        self.file_path = '../files/blockchain' + node_id + '.txt'
        self.ledger = Ledger(node_id)
        self.blockchain = BlockChain(self.node_id, self.ledger)
        self.probability = 0.8

        self.messenger = Messenger(self.node_id, self)
        self.peers = [peer for peer in ['0', '1', '2', '3'] if peer != self.node_id]
        self.transaction_queue = []
        self.timer = None
        self.mining_blocked = False

        self.signatures = []
        self.received_blocks = collections.deque()

    # def start_mining_thread(self) -> Thread:
    #     #     """
    #     #     Starts the thread that continually mines new blocks to add to the chain.
    #     #
    #     #     :return: mining thread
    #     #     """
    #     #     t = Thread(
    #     #         target=self.mining_thread,
    #     #         name=('Mining Threads' + self.node_id)
    #     #     )
    #     #     t.start()
    #     #     return t

    def timer_action(self):
        """
        Action to perform when timer finishes.
        Sets blocked to False, so robot can punch again.
        Resets timer variable.
        :return:
        """
        self.mining_blocked = False
        self.timer = None

    def start_timer_secs(self, seconds):
        """
        Set timer for n seconds.
        Starts a thread that sleeps until time is over.
        Once it wakes up, it calls the function to perform.
        :param seconds: Number of seconds timer should run.
        :return:
        """
        new_timer = Timer(seconds, self.timer_action)
        new_timer.start()
        self.timer = new_timer

    def mining(self):
        # TODO: rewrite s.t. mining function is based on 20 second delay, randomized approach + leader election
        mined_probability = random.random()
        if mined_probability > self.probability:
            new_block = Block(self.node_id)
            self.send_msg()
        self.mining_blocked = True
        self.start_timer_secs(20)

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

    def process_incoming_block(self):
        incoming_block = self.received_blocks.popleft()
        # process block returns true if it is valid and added to blockchain and ledger
        if self.blockchain.verify_block(incoming_block):
            # if the block is valid, then we need to remove all transactions from our own tx queue
            delete_transactions = copy.deepcopy(incoming_block.transactions)
            self.transaction_queue = [x for x in self.transaction_queue if x not in delete_transactions]
            # TODO : sign and reply to leader that block was verified

    def send_msg(self, contents: str, type: str):
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