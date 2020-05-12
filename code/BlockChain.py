from Block import Block
from Transaction import Transaction
from Ledger import Ledger
import datetime, os, pickle, collections, copy


class BlockChain:
    def __init__(self, node_id: str, ledger: Ledger):
        """
        Constructor initializes a BlockChain using a Genesis Block. Only used if no chain already on disk when Node.py
        starts up.

        :param node_id: str. One of '0', '1', '2', or '3', the possible nodes in network.
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
                        tx_short = Transaction(str(tx))
                        tx_short_dict = tx_short.__dict__
                        for k2, v2 in tx_short_dict.items():
                            #"2020-05-12 18:20:25.659289"
                            if k2 == 'timestamp':
                                tx_short_dict[k2] = v2[11:22]
                            elif k2 == 'unique_id':
                                tx_short_dict[k2] = v2[:5] + '...'
                        blockchain_string += '\t' + str(tx_short) + '\n'
                elif k == 'signatures':
                    v_short = copy.deepcopy(v)
                    new_sig = {}
                    for k2, v2 in v_short.items():
                        new_sig[k2[:8]+'...'] = v2
                    blockchain_string += k + ': ' + str(new_sig) + '\n'
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
                    index=0,
                    timestamp=str(datetime.datetime.now()),
                    transactions=[]
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
