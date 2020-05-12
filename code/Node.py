from Transaction import Transaction
from Ledger import Ledger
from BlockChain import BlockChain
from LeaderElection import LeaderElection
from Block import Block
from Messenger import Messenger
from threading import Thread
from time import sleep
from datetime import datetime
from dateutil import parser as date_parser
import json, copy, collections, random, math, sys, cryptography
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes


class Node:

    def __init__(self, node_id: str):
        """
        Constructor for the Node class.
        Synchronizes nodes.
        Starts messaging and mining threads.
        Creates files to store data.

        :param str node_id: one of '0', '1', '2', or '3', the possible nodes in network
        """
        self.node_id = node_id
        self.file_path = '../files/blockchain' + node_id + '.txt'
        self.ledger = Ledger(node_id)
        self.blockchain = BlockChain(self.node_id, self.ledger)
        self.probability = 0.1
        self.term_duration = 25
        self.le = LeaderElection(self.node_id)
        self.leader_counts = {'0': 0, '1': 0, '2': 0, '3': 0}
        # self.elected_boolean = False

        self.peers = [peer for peer in ['0', '1', '2', '3'] if peer != self.node_id]
        self.transaction_queue = []

        self.received_blocks = collections.deque()
        self.secret_message = b'SECRET TUNNEL!'
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
        self.messenger = Messenger(self.node_id, self)
        self.sync_nodes()
        self.genesis_time = 'not set'
        self.term = 0

    def sync_nodes(self):
        """
        Method to synchronize all nodes for receiving and sending messages over the queue.
        Blockchain cannot start until all nodes are live and have generated their private/public key pairs.
        """
        start_time = datetime.now()
        self.nodes_online.append(start_time)
        self.send_blockchain_msg(type='sync', contents={'start_time': str(start_time)})

        public_key_string = self.all_public_keys[self.node_id].public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")
        self.send_blockchain_msg(type='key',
                                 contents={'key': public_key_string, 'sender': self.node_id, 'signature': self.sig})

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
        print('Mining thread started.')
        return t

    def mining_thread(self):
        """
        Waits to start mining until all nodes are initialized.
        Calculates current term based on genesis time and timestamp.
        Starts mining a block every time a new term begins (e.g. every 20 or 25 seconds)
        :return:
        """
        while True:
            if self.genesis_time != 'not set':
                term = self.term
                time_diff = datetime.now() - self.genesis_time
                time_diff = time_diff.seconds
                new_term = math.ceil(time_diff / self.term_duration)
                if new_term > term:
                    # reset all flags
                    self.term = new_term
                    self.mine_block()

    def mine_block(self):
        """
        The actual mining of a block.

        Generates a block with a certain probability, if a block was generated, the node requests leadership.
        Leadership is granted through the RAFT algorithm, which has been slightly adjusted to suit this purpose.
        Whichever node was elected sends generated block to all other nodes for verification and signing.
        """
        sleep(random.random() * 2)
        mined_probability = random.random()
        if mined_probability > self.probability and len(self.transaction_queue) != 0:
            tx_to_mine = self.transaction_queue
            new_index = self.blockchain.get_last_block().index + 1
            verify_boolean, change_or_bad_tx = self.ledger.verify_transaction(tx_to_mine, new_index)
            while not verify_boolean:
                self.transaction_queue = [tx for tx in self.transaction_queue if tx.unique_id not in change_or_bad_tx]
                verify_boolean, change_or_bad_tx = self.ledger.verify_transaction(tx_to_mine, new_index)
            new_block = Block(index=new_index, transactions=tx_to_mine)
            to_node = self.peers[random.randrange(len(self.peers))]

            self.le.request_leadership()
            sleep(5)
            if self.le.election_state != 'leader':
                return
            sleep(.5)
            print('I have been elected as leader.')
            self.send_peer_msg(type='Block',
                               contents={'block': str(new_block), 'leader_id': self.node_id, 'term': self.term,
                                         'history': json.dumps([self.node_id])}, peer=to_node)
            print(self.node_id, " has mined and sent a block to ", to_node)

            self.le.release_leadership()

    def handle_incoming_message(self, msg: dict):
        """
        Handles incoming messages from the Messenger class in dictionary format.
        Four types of messages exist: Transactions, Blocks, Sync, and Key messages.

        :param msg: dict. Message attributes represented as string key value pairs.
        :return: None
        """

        if msg['type'] == 'Transaction':  # if transaction append to tx queue
            contents = msg['contents']
            self.transaction_queue.append(Transaction(contents))

        elif msg['type'] == 'Block' and self.genesis_time != 'not set':  # if block process and reset mine function if valid
            msg_dict = json.loads(msg['contents'])
            incoming_block = Block(msg_dict['block'])
            leader_id = msg_dict['leader_id']
            block_term = int(msg_dict['term'])
            block_history = json.loads(msg_dict['history'])
            # print("\nIncoming Block received: \n", incoming_block, block_term, leader_id, '\n incoming term : ', block_term)
            self.process_incoming_block(block=incoming_block, term=block_term, leader_id=leader_id,
                                        block_history=block_history)

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
        """
        Method to add a block to the blockchain after it has been verified.
        Deletes block transactions from transaction queue to avoid double transactions.
        Keeps track of whichever node generated a block to determine whether generation rate exceeds probability.

        :param block: The block to be added, contains transactions to be removed
        :param leader_id: Who generated the block
        :return:
        """
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
        """
        Verifies encoded signatures by using a secret message.
        This ensures the message came from one of the known, i.e., trustworthy nodes, by decoding using saved public keys.

        :param block:
        :return:
        """
        signatures = block.signatures
        valid_sig_count = 0
        for sig in signatures.keys():
            for public_key in self.all_public_keys.values():
                # print('what is this key: ', type(public_key), public_key)
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
        :param block_history: List of nodes that have signed the block
        :return: None
        """
        # process block returns true if it is valid and added to blockchain and ledger
        #print('==================================received term: ', term, " self term: ", self.term, 'self.node_id: ',
              self.node_id, '\n+++++++++++++++++++++++++++++++++++++++++++++++++++')
        if term == self.term and block.index == self.blockchain.get_last_block().index + 1:  # and self.verify_all_signatures(block):
            # if node is a follower
            if self.node_id != leader_id:
                # Check if there is enough stake
                if block.verify_proof_of_stake():
                    self.add_to_blockchain(block, leader_id)

                else:
                    # verify transactions through ledger
                    valid_boolean, change_or_bad_tx = self.ledger.verify_transaction(block.transactions, block.index)
                    # Check node that sent the block does not exceed generation rate. Otherwise, no block is added.
                    # This prevents a node from sending too many blocks (i.e., taking control of the chain).
                    if (self.leader_counts[leader_id] / self.term) < self.probability:
                        if valid_boolean and self.sig not in block.signatures.keys():
                            print('Signing block with stake: ', sum([tx.amount for tx in block.transactions]) / 2 + .1)
                            block.signatures[self.sig] = sum([tx.amount for tx in block.transactions]) / 2 + .1
                            block_history.append(self.node_id)
                            contents = {'block': str(block), 'leader_id': leader_id, 'term': str(term),
                                        'history': json.dumps(block_history)}
                            if block.verify_proof_of_stake():
                                self.send_peer_msg(type='Block', contents=contents, peer=leader_id)
                            else:
                                options = [peer for peer in self.peers if peer not in block_history]
                                to_node = options[random.randrange(len(options))]
                                self.send_peer_msg(type='Block', contents=contents, peer=to_node)
            # Node is leader
            else:
                # Check if there is enough stake
                if block.verify_proof_of_stake():
                    self.add_to_blockchain(block, leader_id)
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
                self.send_blockchain_msg(type='Block',
                                         contents={'block': str(block), 'leader_id': leader_id, 'term': term,
                                                   'history': json.dumps(block_history)})

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

    def send_peer_msg(self, contents: dict, type: str, peer: str):
        """
        sends msgs to specific peer

        :param contents: str. ANYTHING YOU DAMN PLEASE
        :param type: str. indicates type of msg. 'Block' or 'Transaction'
        :param peer: str. destination
        :return: None
        """
        msg_dict = {'contents': json.dumps(contents), 'type': type}
        self.messenger.send(msg_dict, peer)


if __name__ == '__main__':
    arg = sys.argv[1]
    n = Node(arg)

    print('constructors finished')

    while len(n.all_public_keys) < 4:
        continue
    sleep(1)
    n.start_mining_thread()
