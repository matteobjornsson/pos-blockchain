import json, hashlib, datetime, copy
from Transaction import Transaction


class Block:
    """
    This class holds all the attributes that define a blockchain Block.

    Attributes
    -----------
    index : int
        number of block in the blockchain
    prevHash : str
        hash of the block previous in the blockchain (block at position index - 1)
    timestamp : str
        timestamp of block
    nonce : int
        nonce of block. Used to compute a hash of appropriate difficulty.
    transactions : list of Transaction objects
        Transactions that were mined into the block.
    hash : str
        Hash of the block contents in JSON format without the hash attribute included.

    Methods
    -----------
    verify_proof_of_work()
        blocks are often constructed from incoming unverified JSON. This method verifies the hash matches the contents

    """

    def __init__(self, json_string: str = '', prevHash: str = '', timestamp: str = '', nonce: int = 0,
                 transactions: list = [], hash: str = '', index: int = 0):
        """
        Constructor for a Block.

        :param json_string: str. Constructor can take in just a JSON string and build a block object from that.
        :param prevHash: str. Used if JSON string parameter not used.
        :param timestamp: str. Used if JSON string parameter not used.
        :param nonce: int. Used if JSON string parameter not used.
        :param transactions: list of Transaction objects. Used if JSON string parameter not used.
        :param hash: str. Used if JSON string parameter not used.
        :param index: int. Used if JSON string parameter not used.
        """
        # if JSON string is provided, assign parameters from that.
        if json_string != '':
            json_obj = json.loads(json_string)
            self.index = int(json_obj['index'])
            self.prevHash = json_obj['prevHash']
            self.timestamp = json_obj['timestamp']
            self.nonce = int(json_obj['nonce'])
            self.transactions = [Transaction(x) for x in json_obj['transactions']]
            self.hash = json_obj['hash']
        # otherwise construct Block from assigned variables.
        else:
            self.index = index
            self.prevHash = prevHash
            self.timestamp = timestamp
            self.nonce = nonce
            self.transactions = transactions
            self.hash = hash

    def __str__(self):
        """
        override for the string representation of a Block

        :return: str.
        """
        blockDict = copy.deepcopy(self.__dict__)
        blockDict['transactions'] = [str(tx) for tx in blockDict['transactions']]
        return json.dumps(blockDict)

    def __eq__(self, _in) -> bool:
        """
        Override of the equality attribute. Blocks are the same if their hashes are equivalent.

        :param _in: str. Transaction to compare with self.
        :return: bool.
        """
        return _in.hash == self.hash

    def verify_proof_of_work(self) -> bool:
        """
        This method verifies the hash matches the JSON equivalent of the block contents (sans hash)

        :return:
        """
        block_dict = copy.deepcopy(self.__dict__)
        block_dict['transactions'] = [str(tx) for tx in block_dict['transactions']]
        # print("\nblock_dict in json format:\n", json.dumps(block_dict), '\n')
        incoming_hash = block_dict.pop('hash')  # remove hash from object to verify the rest of the contents
        # print('print json block to verify, sans hash, followed by hash\n', json.dumps(block_dict), incoming_hash)
        verify_hash = hashlib.sha256(json.dumps(block_dict).encode()).hexdigest()  # recompute hash value of contents
        # print('verify_hash', verify_hash)
        # print(type(verify_hash), type(incoming_hash))
        return verify_hash == incoming_hash


if __name__ == '__main__':
    new_block = {
        'prevHash':'e4d0ab7c39bbb38c2df7ee2689ae98f52a6099a5932b58c7339f8763dbaea2ec',
        'timestamp' : str(datetime.datetime.now()),
        'nonce': 5,
        'transactions': [Transaction(_to='node1', _from='node2', amount=12.5),
                         Transaction(_to='node3', _from='node2', amount=200.1)],
        'index': 4
    }
    new_block['transactions'] = [str(tx) for tx in new_block['transactions']]
    print('\n this is the exact string we are hashing for block b:\n', json.dumps(new_block),'\n')
    _hash = hashlib.sha256(json.dumps(new_block).encode()).hexdigest()
    new_block['hash'] = _hash

    new_block_json = json.dumps(new_block)
    b = Block(json_string=new_block_json)
    print('\njson representation of block b: \n', str(b), '\n')
    b2 = Block(str(b))
    print(b2.verify_proof_of_work())
