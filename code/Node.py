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
        self.ledger = Ledger(node_id)
        self.blockchain = BlockChain(self.node_id, self.ledger)
        self.probability = 0.8
        self.term_duration = 20
        self.le = leaderElection(self.node_id)
        # self.elected_boolean = False
        self.sig = 'check it out this is my gd signature: ' + self.node_id

        self.messenger = Messenger(self.node_id, self)
        self.peers = [peer for peer in ['0', '1', '2', '3'] if peer != self.node_id]
        self.transaction_queue = []

        self.signatures = ['check it out this is my gd signature: ' + peer for peer in self.peers]
        self.received_blocks = collections.deque()

        self.nodes_online = []
        self.sync_nodes()
        self.genesis_time = 'not set'
        self.term = 0

        self.start_mining_thread()

    def sync_nodes(self):
        start_time = datetime.now()
        self.nodes_online.append(start_time)
        self.send_blockchain_msg(type='sync', contents={'start_time': str(start_time)})

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

        mined_probability = random.random()
        if True: # mined_probability > self.probability:
            tx_to_mine = self.transaction_queue
            new_index = self.blockchain.get_last_block().index + 1
            verify_boolean, change_or_bad_tx = self.ledger.verify_transaction(tx_to_mine, new_index )
            while not verify_boolean:
                self.transaction_queue = [tx for tx in self.transaction_queue if tx.unique_id not in change_or_bad_tx]
                verify_boolean, change_or_bad_tx = self.ledger.verify_transaction(tx_to_mine, new_index)
            new_block = Block(index=new_index, transactions=tx_to_mine)
            self.send_blockchain_msg(type='Block', contents={'block': str(new_block), 'leader_id': self.node_id, 'term': self.term})
            print(self.node_id, " has mined and sent a block")

        self.le.release_leadership()

    def handle_incoming_message(self, msg: dict):
        """
        Handles incoming messages from the Messenger class in dictionary format.

        :param msg: dict. Message attributes represented as string key value pairs.
        :return: None
        """

        if msg['type'] == 'Transaction':  # if transaction append to tx queue
            contents = msg['contents']
            print(contents, type(contents))
            # TODO: fix the sending side of this shit
            self.transaction_queue.append(Transaction(contents))

        elif msg['type'] == 'Block':  # if block process and reset mine function if valid
            msg_dict = json.loads(msg['contents'])
            block_string = copy.deepcopy(msg_dict)
            # print('received block throwing error: ', block_string)
            incoming_block = Block(msg_dict['block'])
            leader_id = msg_dict['leader_id']
            block_term = int(msg_dict['term'])
            print("\nIncoming Block received: \n", incoming_block, block_term, leader_id, '\n incoming term : ', block_term)
            self.process_incoming_block(block=incoming_block, term=block_term, leader_id=leader_id)

        elif msg['type'] == 'sync':
            msg_dict = json.loads(msg['contents'])
            start_time = date_parser.parse(msg_dict['start_time'])
            self.nodes_online.append(start_time)
            if len(self.nodes_online) > 3:
                # print("synched!")
                self.genesis_time = max(self.nodes_online)
                print('genesis time = ', self.genesis_time)
        #elif receive election_msg:
        #

    def process_incoming_block(self, block: Block, term: int, leader_id: str):
        """
        check if incoming block is sufficently staked. If so add to blockchain. Otherwise, if leader send it for more
        signatures. if follower, sign and send back to leader.
        :param block: block in question
        :param term: blockchain cycle identifier
        :param leader_id: who generated the block
        :return: None
        """
        # process block returns true if it is valid and added to blockchain and ledger
        # print('received term: ', type(term), " self term: ", type(self.term))
        if term == self.term:
            # print('self.node_id :', self.node_id, ' leader_id :', leader_id)
            if self.node_id != leader_id:
                if block.verify_proof_of_stake():
                    self.blockchain.add_block(block)
                    self.ledger.add_transactions(block.transactions, block.index)
                    print("follower ", self.node_id, "added block to blockchain")
                    # if the block is valid, then we need to remove all transactions from our own tx queue
                    delete_transactions = copy.deepcopy(block.transactions)
                    self.transaction_queue = [x for x in self.transaction_queue if x not in delete_transactions]

                else:
                    print("follower ", self.node_id, "received block to verify")
                    # if sender does not exceed block generation rate, do this:
                    valid_boolean, change_or_bad_tx = self.ledger.verify_transaction(block.transactions, block.index)
                    if valid_boolean and self.sig not in block.signatures.keys():
                        # print('sum ', sum([tx.amount for tx in block.transactions])/3 + .1)
                        block.signatures[self.sig] = sum([tx.amount for tx in block.transactions])/3 + .1
                        contents = {'block': str(block), 'leader_id': leader_id, 'term': str(term)}
                        self.send_peer_msg(type='Block', contents=contents, peer=leader_id)
            else:
                # print('leader received block from followers')
                if block.verify_proof_of_stake():
                    self.blockchain.add_block(block)
                    self.ledger.add_transactions(block.transactions, block.index)
                    print("leader ", self.node_id, "added block to blockchain")
                    # if the block is valid, then we need to remove all transactions from our own tx queue
                    delete_transactions = copy.deepcopy(block.transactions)
                    self.transaction_queue = [x for x in self.transaction_queue if x not in delete_transactions]
                    # TODO: REWARD ERRYBODY FOR ALL THEIR HARD WORK, ALSO TREAT YO'SELF TOO
                # if stake was sufficient, block will be complete, otherwise block will go get more signatures
                else:
                    print("leader ", self.node_id, "needs more signatures")
                self.send_blockchain_msg(type='Block', contents={'block': str(block), 'leader_id': leader_id, 'term': term})

    # - process block method checks received block data:
    # if leader ID == self and term == term, combine received signatures, if > tx value, do the thing
    # if not leader ID and not > tx value, verify and sign and send back to Leader ID
    # if not leader ID and > tx value, add to blockchain

    def send_blockchain_msg(self, contents: dict, type: str):
        """
        sends msgs to all peers

        :param contents: str. Newly mined blocks or new transactions in JSON string representation.
        :param type: str. indicates type of msg. 'Block' or 'Transaction'
        :return: None
        """
        # send block to all known peers
        msg_dict = {'contents': json.dumps(contents), 'type': type}
        for peer in self.peers:
            self.messenger.send(msg_dict, peer)
        #print('sending msg dictionary: ', msg_dict)

    def send_peer_msg(self, contents: dict, type: str, peer: str):
        """
        sends msgs to specific peer

        :param contents: str. ANYTHING YOU DAMN PLEASE
        :param type: str. indicates type of msg. 'Block' or 'Transaction'
        :param peer: str. destination
        :return: None
        """
        # send block to all known peers
        msg_dict = {'contents': json.dumps(contents), 'type': type}
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