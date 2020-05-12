import json, hashlib, datetime, copy
from Transaction import Transaction

class Block:

    def __init__(self, json_string: str = '',  timestamp: str = '',
                 transactions: list = [], index: int = 0):
        """
        Constructor for a Block.

        :param json_string: str. Constructor can take in just a JSON string and build a block object from that.
        :param timestamp: str. Used if JSON string parameter not used.
        :param transactions: list of Transaction objects. Used if JSON string parameter not used.
        :param index: int. Used if JSON string parameter not used.
        """
        # if JSON string is provided, assign parameters from that.
        if json_string != '':
            json_obj = json.loads(json_string)
            self.index = int(json_obj['index'])
            self.timestamp = json_obj['timestamp']
            self.transactions = [Transaction(x) for x in json_obj['transactions']]
            self.signatures = json_obj['signatures']
        # otherwise construct Block from assigned variables.
        else:
            self.index = index
            self.timestamp = str(datetime.datetime.now())
            self.transactions = transactions
            self.signatures = {} #'key':value -> 'unique node signature':stake

    def __str__(self):
        """
        override for the string representation of a Block

        :return: str.
        """
        blockDict = copy.deepcopy(self.__dict__)
        blockDict['transactions'] = [str(tx) for tx in blockDict['transactions']]
        return json.dumps(blockDict)

    def verify_proof_of_stake(self):
        sum_stake = 0
        for k,v in self.signatures.items():
            #print('looping through signatures key: ', k, 'value: ', v, '\n')
            sum_stake += v
        #print('block signature sums: ', sum_stake, 'transaction sums: ', sum([tx.amount for tx in self.transactions]), '\n')
        if sum_stake > sum([tx.amount for tx in self.transactions]):
            #print('verified proof of stake')
            return True
        else:
            #print('not enough stake?')
            return False

if __name__ == '__main__':
    new_block = {
        'index': 1,
        'timestamp' : str(datetime.datetime.now()),
        'transactions': [Transaction(_to='1', _from='2', amount=2.5),
                         Transaction(_to='3', _from='2', amount=4.1)],
        'signatures': {'0': 3, '1': 3.0}
    }
    new_block['transactions'] = [str(tx) for tx in new_block['transactions']]
    new_block_json = json.dumps(new_block)
    b = Block(json_string=new_block_json)
    print('\njson representation of block b: \n', str(b), '\n')
    b2 = Block(str(b))
    print(b2.verify_proof_of_stake())