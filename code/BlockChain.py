from Block import Block
from Transaction import Transaction
from Ledger import Ledger
import datetime, hashlib, json, os, pickle, collections


class BlockChain:
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

    def verify_block(self, block) -> bool:
        pass

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