from Ledger import *
from Transaction import Transaction
from Ledger import Ledger
from BlockChain import BlockChain
from leaderelection import leaderElection
from Block import Block
from Messenger import Messenger
from threading import Thread
from time import sleep, clock
from datetime import datetime
from dateutil import parser as date_parser
import json, copy, collections, random, math, shutil
import cryptography
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes



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
        self.probability = 0.1
        self.term_duration = 25
        self.le = leaderElection(self.node_id)
        self.leader_counts = {'0': 0, '1': 0, '2': 0, '3': 0}
        # self.elected_boolean = False

        self.messenger = Messenger(self.node_id, self)
        self.peers = [peer for peer in ['0', '1', '2', '3'] if peer != self.node_id]
        self.transaction_queue = []


        self.received_blocks = collections.deque()
        self.secret_message =  b'SECRET TUNNEL!'
        self.nodes_online = []
        self.all_public_keys = {}
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.sig = self.private_key.sign(
            self.secret_message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        ).hex()
        self.peer_signatures = {}
        self.all_public_keys[self.node_id] = self.private_key.public_key()
        self.sync_nodes()
        self.genesis_time = 'not set'
        self.term = 0


    def sync_nodes(self):
        start_time = datetime.now()
        self.nodes_online.append(start_time)
        self.send_blockchain_msg(type='sync', contents={'start_time': str(start_time)})

        public_key_string = self.all_public_keys[self.node_id].public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")
        self.send_blockchain_msg(type='key', contents={'key': public_key_string, 'sender': self.node_id, 'signature': self.sig})


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
            print('no leader elected \n')
            return
        sleep(.5)
        print("I hope I'm leader!!! : ", self.le.election_state, "\n")

        mined_probability = random.random()
        if len(self.transaction_queue) != 0: #mined_probability > self.probability and
            tx_to_mine = self.transaction_queue
            new_index = self.blockchain.get_last_block().index + 1
            verify_boolean, change_or_bad_tx = self.ledger.verify_transaction(tx_to_mine, new_index )
            while not verify_boolean:
                print('BAD TRANSACTIONS DETECTED. PANIC!')
                self.transaction_queue = [tx for tx in self.transaction_queue if tx.unique_id not in change_or_bad_tx]
                verify_boolean, change_or_bad_tx = self.ledger.verify_transaction(tx_to_mine, new_index)
            new_block = Block(index=new_index, transactions=tx_to_mine)
            to_node = self.peers[random.randrange(len(self.peers))]
            self.send_peer_msg(type='Block', contents={'block': str(new_block), 'leader_id': self.node_id, 'term': self.term, 'history': json.dumps([self.node_id])}, peer=to_node)
            print(self.node_id, " has mined and sent a block to ", to_node)

        self.le.release_leadership()

    def handle_incoming_message(self, msg: dict):
        """
        Handles incoming messages from the Messenger class in dictionary format.

        :param msg: dict. Message attributes represented as string key value pairs.
        :return: None
        """

        if msg['type'] == 'Transaction':  # if transaction append to tx queue
            contents = msg['contents']
            self.transaction_queue.append(Transaction(contents))

        elif msg['type'] == 'Block':  # if block process and reset mine function if valid
            msg_dict = json.loads(msg['contents'])
            incoming_block = Block(msg_dict['block'])
            leader_id = msg_dict['leader_id']
            block_term = int(msg_dict['term'])
            block_history = json.loads(msg_dict['history'])
            # print("\nIncoming Block received: \n", incoming_block, block_term, leader_id, '\n incoming term : ', block_term)
            self.process_incoming_block(block=incoming_block, term=block_term, leader_id=leader_id, block_history=block_history)

        elif msg['type'] == 'sync':
            msg_dict = json.loads(msg['contents'])
            start_time = date_parser.parse(msg_dict['start_time'])
            self.nodes_online.append(start_time)
            if len(self.nodes_online) > 3:
                # print("synched!")
                self.genesis_time = max(self.nodes_online)
                print('genesis time = ', self.genesis_time)

        elif msg['type'] == 'key':
            msg_dict = json.loads(msg['contents'])
            sender = msg_dict['sender']
            sig = msg_dict['signature']
            key_string = msg_dict['key'].encode("utf-8")

            incoming_public_key = serialization.load_pem_public_key(
                key_string,
                backend=default_backend()
            )
            self.all_public_keys[sender] = incoming_public_key
            self.peer_signatures[sig] = sender


    def add_to_blockchain(self, block, leader_id):
        self.blockchain.add_block(block)
        self.ledger.add_transactions(block.transactions, block.index)
        if self.node_id == leader_id:
            print("leader ", self.node_id, "added block to blockchain")
        else:
            print("follower ", self.node_id, "added block to blockchain")
        self.leader_counts[leader_id] += 1
        # if the block is valid, then we need to remove all transactions from our own tx queue
        delete_transactions = copy.deepcopy(block.transactions)
        self.transaction_queue = [x for x in self.transaction_queue if x not in delete_transactions]

    def verify_all_signatures(self, block: Block) -> bool:
        signatures = block.signatures
        valid_sig_count = 0
        for sig in signatures.keys():
            for public_key in self.all_public_keys.values():
                print('what is this key: ', type(public_key), public_key)
                try:
                    public_key.verify(
                        bytes.fromhex(sig),
                        self.secret_message,
                        padding.PSS(
                            mgf=padding.MGF1(hashes.SHA256()),
                            salt_length=padding.PSS.MAX_LENGTH
                        ),
                        hashes.SHA256()
                    )
                    valid_sig_count += 1
                    print("signature validated!")
                except cryptography.exceptions.InvalidSignature:
                    pass
        if len(signatures) == valid_sig_count:
            return True
        else:
            return False

    def process_incoming_block(self, block: Block, term: int, leader_id: str, block_history: list):
        """
        check if incoming block is sufficently staked. If so add to blockchain. Otherwise, if leader send it for more
        signatures. if follower, sign and send back to leader.
        :param block: block in question
        :param term: blockchain cycle identifier
        :param leader_id: who generated the block
        :return: None
        """
        # process block returns true if it is valid and added to blockchain and ledger
        print('==================================received term: ', term, " self term: ", self.term, 'self.node_id: ', self.node_id, '\n+++++++++++++++++++++++++++++++++++++++++++++++++++')
        if term == self.term and block.index == self.blockchain.get_last_block().index+1:# and self.verify_all_signatures(block):
            # print('self.node_id :', self.node_id, ' leader_id :', leader_id)
            if self.node_id != leader_id: # if node is a follower
                print('incoming block index: ', block.index, ' last block index: ', self.blockchain.get_last_block().index)
                if block.verify_proof_of_stake():
                    self.add_to_blockchain(block, leader_id)

                else:
                    #print("follower ", self.node_id, "received block to verify")
                    # if sender does not exceed block generation rate, do this:
                    valid_boolean, change_or_bad_tx = self.ledger.verify_transaction(block.transactions, block.index)
                    #print('generation rate: ', self.leader_counts[leader_id]/self.term)
                    if (self.leader_counts[leader_id]/self.term) < self.probability:
                        if valid_boolean and self.sig not in block.signatures.keys():
                            print('stake to be sent ', sum([tx.amount for tx in block.transactions])/2 + .1)
                            block.signatures[self.sig] = sum([tx.amount for tx in block.transactions])/2 + .1
                            block_history.append(self.node_id)
                            contents = {'block': str(block), 'leader_id': leader_id, 'term': str(term), 'history': json.dumps(block_history)}
                            if block.verify_proof_of_stake():
                                self.send_peer_msg(type='Block', contents=contents, peer=leader_id)
                            else:
                                options = [peer for peer in self.peers if peer not in block_history]
                                print ('block history at ', self.node_id, ': ', block_history, '. Options: ', options)
                                to_node = options[random.randrange(len(options))]
                                self.send_peer_msg(type='Block', contents=contents, peer=to_node)

            else:
                # print('leader received block from followers')
                if block.verify_proof_of_stake():
                    self.add_to_blockchain(block, leader_id)

                    # TODO: REWARD ERRYBODY FOR ALL THEIR HARD WORK, ALSO TREAT YO'SELF TOO
                    rewardees = [self.peer_signatures[sig] for sig in block.signatures.keys()]
                    rewardees.append(self.node_id)
                    print('Reward these hard working folx: ', rewardees)
                    for peer in rewardees:
                        reward_tx = str(Transaction(_to=peer, _from='reward', amount=1))
                        for destination in ['0', '1', '2', '3']:
                            self.messenger.send({'type': 'Transaction', 'contents': reward_tx}, destination)

                # if stake was sufficient, block will be complete, otherwise block will go get more signatures
                else:
                    print("leader ", self.node_id, "needs more signatures")
                self.send_blockchain_msg(type='Block', contents={'block': str(block), 'leader_id': leader_id, 'term': term, 'history': json.dumps(block_history)})


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
    try:
        shutil.rmtree('../files')
    except OSError:
        print('no files to delete? ')
    n0 = Node('0')
    n1 = Node('1')
    n2 = Node('2')
    n3 = Node('3')

    print('constructors finished')
    synched = False
    count = 0
    while not synched or len(n3.all_public_keys) < 4:
        count = 0
        for n in [n0, n1, n2, n3]:
            synched_nodes = len(n.nodes_online)
            if synched_nodes > 3:
                count += 1
        if count == 4:
            sleep(1)
            break
    for n in [n0, n1, n2, n3]:
        n.start_mining_thread()