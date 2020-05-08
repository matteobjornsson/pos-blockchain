from Block import Block
from Transaction import Transaction
from Ledger import Ledger
import datetime, hashlib, json, os, pickle, collections


class BlockChain:
    """
    A class used to hold and manipulate a blockchain. Initialized with an associated ledger. BlockChain contents are
    stored to disk for node failure recovery.

    Attributes
    ----------
    ledger : Ledger
        a reference to the blockchain's associated ledger, created by Node.py
    blockchain: List
        list of Block objects constituting the blockchain


    Methods
    -------
    verify_block(block: Block)
        This method verifies the proof of work and transactions of a block and adds the block to the chain if valid.
    add_block(block: Block)
        Adds a block to the blockchain a its appropriate index
    get_last_block()
        Return last block in the chain.

    """

    def __init__(self, node_id: str, ledger: Ledger):
        """
        Constructor initializes a BlockChain using a Genesis Block. Only used if no chain already on disk when Node.py
        starts up.

        :param ledger: Ledger. Reference to ledger passed to constructor for reference.
        """
        self.ledger = ledger
        self.node_id = node_id
        filename = '../files/blockchain' + node_id
        self.file_path = filename + '.txt'
        self.pickle_path = filename + '.pickle'
        self.blockchain = []
        self.saved_blocks = []
        self.create_or_read_file()

        #  TODO: pickledump and jsondump the chain to disk

    def verify_block(self, block) -> bool:
        """
        Method takes a block and verifies the PoW and transaction validity (which updates ledger if valid).
        If valid add block to chain.

        :param block: Block. Represents block object to be processed.
        :return: bool. Return True if valid block and added to ledger and chain, return False otherwise.
        """
        if block.index < len(self.blockchain):
            self.saved_blocks.append(block)
            print("incoming block index less than last +1, added to saved blocks")
            return False
        # print('incoming block index: ', block.index, '\n index of last block in chain: ', self.get_last_block().index)
        # print('incoming block prevHash: ', block.prevHash, '\nhash of last block in chain: ', self.get_last_block().hash)
        elif block.index == len(self.blockchain) and block.prevHash == self.get_last_block().hash:
            #print('Incoming block matches index and hash requirements')
            if block.verify_proof_of_work():
                #print('proof of work check passed')
                # if transactions are valid verify_and_add will update the ledger and return true
                verified_bool, change = self.ledger.verify_transaction(block.transactions, block.index)
                if verified_bool:
                    self.ledger.add_balance_state(change[0], block.index)  # apply that state if none are negative
                    #print('verify tx check passed')
                    #  add the block to the chain since PoW and tx are valid
                    self.add_block(block)
                    print("\nReceived Block added to Blockchain: \n", "Index: ", block.index, '\n', "Previous Hash: ",
                          block.prevHash, '\n', "Hash: ", block.hash, '\n')
                    return True
                else:
                    print('verify tx not passed\nIndex = ', block.index, '\nHash = ', block.hash, '\n')
            else:
                print('proof of work check not passed\nIndex = ', block.index, '\nHash = ', block.hash, '\n')
            return False
        elif block.index == len(self.blockchain) and block.prevHash != self.get_last_block().hash:
            self.saved_blocks.append(block)
            print("incoming block has appropriate index but not correct prev hash, added to saved blocks")
            return False
        elif block.index > len(self.blockchain):
            self.rebuild_longest_chain(block)
            print('********************************\n**************************\n\n NEW LONGEST CHAIN \n\n')
            print('********************************\n**************************\n\n')
            return False
        return False

    def rebuild_longest_chain(self, block):
        current_block = block
        build_new_chain = True
        new_chain_stack = collections.deque()
        new_chain_stack.append(current_block)

        while build_new_chain:
            prev_block = self.find_block_from_hash(current_block.prevHash, self.saved_blocks)
            if prev_block:
                print('found previous block: ', prev_block[0].index, prev_block[0].hash)
                new_chain_stack.append(prev_block[0])
                current_block = prev_block[0]
            else:
                print('no more previous blocks found')
                build_new_chain = False

        while len(new_chain_stack) > 0:
            next_block = new_chain_stack.pop()
            print('block being replaced: ', next_block.index, next_block.hash)
            self.add_block(next_block)
            self.ledger.add_transactions(next_block.transactions, next_block.index)
            # NEW LONGEST CHAIN!

    # if index already exists:
    #     save block in ''saved blocks''
    #     keep existing chain
    # else if index >> than current index:
    #     loop through ''saved blocks'' until there is no more block with prevHash and add to saved chain stack (to replace)
    #     -> block(prevHash) -> last block current node needs to keep in own chain
    #     Replace current chain from block(prevHash) on with saved chain by popping from stack (add replaced blocks to ""saved blocks"")
    #     #and verifying as saved chain is processed
    #     # if verification fails, revert to old chain

    def find_block_from_hash(self, _hash, list_of_blocks):
        return [block for block in list_of_blocks if block.hash == _hash]

    def add_block(self, block):
        """
        This method adds blocks to the chain and writes new chain to disk.

        :param block: Block. Block to be added to chain. Block is assumed to have been verified already
        :return: None
        """
        if block.index >= len(self.blockchain):
            self.blockchain.append(block)
        else:
            self.blockchain[block.index] = block
        self.write_to_disk()

    def get_last_block(self) -> Block:
        """
        Returns last block in the chain.

        :return: Block.
        """
        return self.blockchain[-1]

    def __str__(self) -> str:
        """
        Overrides native string representation of a BlockChain Object.

        :return: str. String representation of the BlockChain
        """
        blockchain_string = 'Node ' + self.node_id + ' Blockchain: \n'
        stack = collections.deque()
        for block in self.blockchain:
            stack.append(block)
        for i in range(0, len(stack)):
            block = stack.pop()
            blockchain_string += '-'*75 + '\n'
            for k, v in block.__dict__.items():
                if k == 'transactions':
                    blockchain_string += k + ':\n'
                    for tx in v:
                        blockchain_string += '\t' + str(tx) + '\n'
                else:
                    blockchain_string += k + ': ' + str(v) + '\n'
            blockchain_string += '-' * 75 + '\n'
        return blockchain_string

    def create_or_read_file(self):
        """
        Check for existing Blockchain on disk, else create blockchain
        :return: None
        """
        # make sure the 'files' directory exists
        if not os.path.isdir('../files'):
            os.mkdir('../files')
        try:
            # try to read in files from disk if they exist
            read_file = open(self.pickle_path, 'rb')
            self.blockchain = pickle.load(read_file)
            read_file.close()
            # print('blockchain loaded from file')
        except FileNotFoundError:
            # if no blockchain exists, initialize one with the genesis block
            self.blockchain = [  # Genesis block! as the first block in the chain the hashes are predetermined.
                Block(
                    prevHash='0000000000000000000000000000000000000000000000000000000000000000',
                    timestamp=str(datetime.datetime.now()),
                    nonce=0,
                    transactions=[],
                    index=0,
                    hash='000000000000000000000000000000000000000000000000000000000000000f'
                )
            ]
            self.write_to_disk()

    def write_to_disk(self):
        """
        Write self to a human readable text file and dump contents of blockchain to a pickle
        :return: None
        """
        text_file = open(self.file_path, "w")
        text_file.write(str(self))
        text_file.close()
        # dump to pickle
        pickle.dump(self.blockchain, open(self.pickle_path, "wb"))


if __name__ == '__main__':
    bc = BlockChain('0', Ledger('0'))
    print("Initial blockchain: \n", bc)
    new_block = {
        'index': 1,
        'prevHash':'00000000000000000000000000000000000000000000000000000000000fffff',
        'timestamp' : str(datetime.datetime.now()),
        'nonce': 5,
        'transactions': [Transaction(_to='node1', _from='node2', amount=3.4),
                         Transaction(_to='node3', _from='node2', amount=2.1)]

    }
    new_block['transactions'] = [str(tx) for tx in new_block['transactions']]
    _hash = hashlib.sha256(json.dumps(new_block).encode()).hexdigest()
    new_block['hash'] = _hash
    new_block_json = json.dumps(new_block)
    b = Block(json_string = new_block_json)

    if bc.verify_block(b):
        print("\n blockchain: \n", bc)
        print("ledger: \n", bc.ledger.blockchain_balances)



