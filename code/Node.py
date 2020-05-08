from Ledger import *
from Transaction import Transaction
from Ledger import Ledger
from BlockChain import BlockChain
from Block import Block
from Messenger import Messenger
from threading import Thread, enumerate
from time import sleep
import datetime, json, hashlib, copy, collections, sys, random


class Node:
    """
    A class used to represent a Miner node in a BlockChain network. Initialized with node ID string. This class
    sets up a thread that continually mines new blocks from a transaction queue, meeting a predefined hash
    difficulty. Node uses Messenger (SQS) to send and receive messages from other nodes.

    Attributes
    ----------
    difficulty : int
        indicates hash difficulty for mining blocks, integer represents number of leading 0s required
    hash_difficulty : str
        reference for hash difficulty as represented by a 64 char hexadecimal hash
    node_id : str
        name of node (in this case '0', '1', '2', or '3'
    ledger : Ledger
        ledger associated with the blockchain for checking validity of transactions and peer balances
    blockchain : BlockChain
        this is the node's copy of the blockchain for reference and updating
    messenger : Messenger
        a messaging layer used by the node to send and receive blocks and transactions from other miners
    peers : list
        a list of peer nodes, members of the BlockChain network
    transaction_queue : list
        a list of incoming transactions to be mined into a block
    reset_mine_function : bool
        flag for when a new block is discovered, when true node resets flag and begins mining on new block instead
    stop_mine_function : bool
        flag for stopping the mining thread
    mine_thread : thread
        a stored reference to the mining thread for accessing the thread if necessary

    Methods
    -------
    start_mining_thread()
        Starts the thread that continually mines new blocks to add to the chain.
    handle_incoming_message()
        interface required for the Messenger class, handles incoming messages from the Messenger class.
    mining_thread()
        continually mines new blocks on current blockchain, resets function when new block received
    hash_block()
        the actual function that generates a hash for a new block to add to the blockchain
    send_block(block: str)
        sends newly mined blocks to all peers

    """

    def __init__(self, node_id: str):
        """
        Constructor for the Node class.

        :param str node_id: one of '0', '1', '2', or '3', the possible nodes in network
        """
        self.difficulty = 4
        _max = 'f' * 64
        self.hash_difficulty = _max.replace('f', '0', self.difficulty)

        self.node_id = node_id
        self.file_path = '../files/blockchain' + node_id + '.txt'
        #  TODO: check disk for existing ledger and blockchain. Only make new instance if not found.
        self.ledger = Ledger(node_id)
        self.blockchain = BlockChain(self.node_id, self.ledger)

        self.messenger = Messenger(self.node_id, self)
        self.peers = [peer for peer in ['0', '1', '2', '3'] if peer != self.node_id]
        self.transaction_queue = []
        self.reset_mine_function = False
        self.stop_mine_function = False
        self.received_blocks = collections.deque()  # d.append() to add, d.popleft() to remove as queue
        self.mine_thread = self.start_mining_thread()

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
        return t

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
            print("\nIncoming Block received: \n", "Index: ", incoming_block.index, '\n', "Previous Hash: ",
                  incoming_block.prevHash, '\n', "Hash: ", incoming_block.hash, '\n')
            # Nodes must always mine on the longest chain, so any mining in progress needs to be reset
            self.received_blocks.append(incoming_block)
            # print('length of received blocks list: ', len(self.received_blocks))
            self.reset_mine_function = True
            print('reset mining true')

    def process_incoming_block(self):
        incoming_block = self.received_blocks.popleft()
        # process block returns true if it is valid and added to blockchain and ledger
        if self.blockchain.verify_block(incoming_block):
            # if the block is valid, then we need to remove all transactions from our own tx queue
            delete_transactions = copy.deepcopy(incoming_block.transactions)
            self.transaction_queue = [x for x in self.transaction_queue if x not in delete_transactions]
            # print('transactions after deletion ', self.transaction_queue)

    def mining_thread(self):
        """
        Function to be threaded. Continually mines new blocks on current blockchain, watches for new blocks to mine on

        :return: None
        """
        count = 0
        while not self.stop_mine_function:  # always run unless stop flag is true
            if len(self.received_blocks) > 0:
                self.process_incoming_block()

            elif self.transaction_queue:  # check if tx queue is empty
                tx_to_mine = copy.deepcopy(self.transaction_queue)
                next_index = self.blockchain.get_last_block().index + 1

                verified_bool, return_value = self.ledger.verify_transaction(tx_to_mine, next_index)
                # print('verified transaction , returned ', str(verified_bool))
                if verified_bool:
                    # verified_bool returns True with new balance
                    # print('verification successful change of ', return_value)
                    new_block_json = self.hash_block(tx_to_mine, next_index)
                    # print("lenght of mined block(should be 0 if reset mine == True", len(new_block_json))
                    # hash_block() returns empty ('false') string if mining was interrupted by discovery of new block
                    if new_block_json:  # mining was not interrupted
                        new_block = Block(new_block_json)
                        # last check before adding to blockchain that mined block is indeed the longest:
                        # print("length of received blocks list pre add mined block: ",
                        #       len(self.received_blocks))
                        #
                        # if len(self.received_blocks) > 0:
                        #     print('\nIndex of first block in received blocks pre add mined block: ',
                        #           self.received_blocks[0].index)
                        if len(self.received_blocks) > 0 and self.received_blocks[0].index >= new_block.index:
                            print('block already exists at that index! discarding mined block')
                        else:
                            self.ledger.add_balance_state(return_value[0], new_block.index)
                            self.blockchain.add_block(new_block)
                            self.send_msg(new_block_json, 'Block')
                            print("\nmined a new block and added to blockchain!: \n", "Index: ", new_block.index, '\n',
                                  "Previous Hash: ",
                                  new_block.prevHash, '\n', "Hash: ", new_block.hash, '\n')
                    else:
                        # this will only occur if mining had been interrupted, so we need to reset flag and start again
                        self.reset_mine_function = False
                        continue
                else:
                    #  if not valid, verified_bool returns False with list of bad transaction IDs. Delete bad tx
                    # print('verification unsuccessful, returned following transactions ', return_value)
                    # print('txs after receiving block, before adjustment', self.transaction_queue)
                    self.transaction_queue = [tx for tx in self.transaction_queue if tx.unique_id not in return_value]
                    # print('txs after receiving block', self.transaction_queue)
            else:
                pass
            count += 1
            if count > 500000:
                text_file = open(self.file_path, "a")
                text_file.write(str(self.transaction_queue))
                text_file.close()
                count = 0

    def hash_block(self, transactions, index) -> str:
        """
        the actual function that generates a hash for a new block to add to the blockchain

        :return: str. Returns empty string if interrupted, otherwise JSON string representation of a newly mined block
        """
        last_block = self.blockchain.get_last_block()
        #  make a new block with everything but the hash
        new_block = {
            'index': index,
            'prevHash': last_block.hash,
            'timestamp': str(datetime.datetime.now()),
            'nonce': 0,
            'transactions': transactions
        }
        # change the transaction objects into strings so it can be dumped into JSON format
        new_block['transactions'] = [str(tx) for tx in new_block['transactions']]

        # Hash the JSON representation of the new block
        _hash = hashlib.sha256(json.dumps(new_block).encode()).hexdigest()

        # keep hashing the block until the hash meets the required difficulty
        count = 0
        while _hash > self.hash_difficulty:
            count +=1
            if not self.reset_mine_function:  # keep hashing unless a new block was received
                if count > 50000:
                    # print('still mining')
                    count = 0
                new_block['nonce'] += 1
                _hash = hashlib.sha256(json.dumps(new_block).encode()).hexdigest()
                # print(_hash)
            else:  # if a new block was received, break and exit the function, returning an empty string (falsy)
                # print('mining shouldve been reset, entered break of while loop')
                _hash = ''
                break

        if _hash:  # finished mine function uninterrupted, successfully mined new block
            # print('found correct hash')
            new_block['hash'] = _hash
            new_block_json = json.dumps(new_block)
            # clear mined transactions from queue
            # print('txs ater mining before adjustment', self.transaction_queue)
            self.transaction_queue = [x for x in self.transaction_queue if x not in transactions]
            # print('txs ater mining', self.transaction_queue)
            if self.reset_mine_function:
                return ''
            else:
                return new_block_json  # this string will be sent to other nodes
        else:  # mine function interrupted, returning empty string.
            return _hash

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


if __name__ == '__main__':
    arg = sys.argv[1]

    n = Node(arg)
    # n.handle_incoming_message(
    #     {'type': 'Transaction', 'contents': str(Transaction(_to='node1', _from='node3', amount=1))})
    # print('-----------------------------------------------------\n' * 3)
    # n.handle_incoming_message(
    #     {'type': 'Transaction', 'contents': str(Transaction(_to='node3', _from='node1', amount=.22))})
    #
    # print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&\n' * 3)


    # n.stop_mine_function = True
    # n.messenger.run = False
    #
    # n.mine_thread.join()


