from Transaction import Transaction
import pickle, os, copy


class Ledger:
    """
    This class is designed to hold a list of balance states of the blockchain network where each state corresponds to
    the state of the network after the transactions within its associated block were applied to the network balances.
    BlockChain[1] -> Ledger[1]

    Attributes
    ----------
    blockchain_balances : list.
        This list holds all balance states of the blockchain, each state corresponds to a new block added to the chain.

    Methods
    ----------
    verify_and_add_transaction(transactions: list of Transaction objects, index: int)
        Takes transaction objects and applies them to the ledger at index. If any balance is negative return false.
    add_balance_state(balance: dict, index: int)
        Adds a ledger state (in form of dictionary of peers and balances) to the ledger list at index.
    get_curr_balance_for_node(node: str)
        Returns current balance of a given node (as defined in last entry in ledger)
    get_total_currency_in_chain()
        Returns sum of all member balances (represents coin in circulation)
    create_or_read_file()
        Check for existing Ledger on disk, else create Ledger
    write_to_file()
        dump ledger contents to pickle on disk
    """

    def __init__(self, node_id):
        """
        Constructor for the Ledger. Initializes balance of genesis block to introduce init currency into blockchain.
        """
        self.node_id = node_id
        self.file_path = '../files/ledger' + node_id + '.txt'
        self.pickle_path = '../files/ledger' + node_id + '.pickle'
        self.blockchain_balances = [{}]  # initial bc balance
        self.create_or_read_file()

    def verify_transaction(self, transactions, index):
        """
        Takes transaction objects and applies them to the ledger at index. If any balance is negative return false.

        :param transactions: list. List of Transaction objects to verify
        :param index: int. index at which the transactions are applied (equal to block index)
        :return: bool, list. Return True, [new balance dict] if all valid, otherwise return false, [bad transactions] if
        transactions cause any balance to go negative.
        """

        change = copy.deepcopy(self.blockchain_balances[index-1])  # get previous state
        for tx in transactions:  # apply all transactions to that state
            change[tx.from_node] -= tx.amount
            change[tx.to_node] += tx.amount
        all_bad_tx = []
        for node, balance in change.items():
            if balance < 0:
                print('found negative balance')
                all_bad_tx.extend([tx.unique_id for tx in transactions if tx.from_node == node])
        if all_bad_tx:
            print('bad transactions found: ', all_bad_tx)
            return False, all_bad_tx
        else:
            return True, [change]

    def add_balance_state(self, balance, index):
        """
        Adds a ledger state (in form of dictionary of peers and balances) to the ledger list at index.

        :param balance: dict. Dictionary of peer keys and balance values.
        :param index: int.
        :return: None
        """
        if index >= len(self.blockchain_balances):
            self.blockchain_balances.append(balance)
        else:
            self.blockchain_balances[index] = balance
        self.write_to_disk()

    def add_transactions(self, transactions: list, index):
        """
        Add transactions directly to Ledger without verifying them (assumed valid)

        :param transactions: list. list of transaction objects
        :param index: int. index at which tx are applied
        :return: None
        """
        change = copy.deepcopy(self.blockchain_balances[index - 1])  # get previous state
        for tx in transactions:  # apply all transactions to that state
            change[tx.from_node] -= tx.amount
            change[tx.to_node] += tx.amount
        self.add_balance_state(change, index)

    def get_curr_balance_for_node(self, node) -> float:
        """
        Returns current balance of a given node (as defined in last entry in ledger)

        :param node: str. Name of node in question
        :return: float.
        """
        return self.blockchain_balances[-1][node]

    def get_total_currency_in_chain(self) -> float:
        """
        Returns sum of all member balances (represents coin in circulation)
        :return: float.
        """
        _sum = 0
        for v in self.blockchain_balances[-1].values():
            _sum += v
        return _sum

    def create_or_read_file(self):
        """
        Check for existing Ledger on disk, else create Ledger
        :return: None
        """
        # make sure the 'files' directory exists
        if not os.path.isdir('../files'):
            os.mkdir('../files')
        try:
            # try to read in file from disk if it exists
            read_file = open(self.pickle_path, 'rb')
            self.blockchain_balances = pickle.load(read_file)
            read_file.close()
            print('Ledger loaded from file')
        except FileNotFoundError:
            # if no ledger exists, initialize one with the initial balances
            self.blockchain_balances = [{'node0': 10, 'node1': 10, 'node2': 10, 'node3': 10}]
            self.write_to_disk()

    def write_to_disk(self):
        """
        dump ledger contents to pickle on disk
        :return: None
        """
        # dump to pickle
        ledger_string = 'Ledger: \n'
        for entry in self.blockchain_balances:
            print(entry)
            ledger_string += str(entry) + '\n'

        text_file = open(self.file_path, "w")
        text_file.write(ledger_string)
        text_file.close()

        pickle.dump(self.blockchain_balances, open(self.pickle_path, "wb"))


if __name__ == '__main__':
    transactions = [Transaction(_to='node1', _from='node3', amount=1.1),
                    Transaction(_to='node3', _from='node1', amount=0.5)]
    nodes = ['node0', 'node1', 'node2', 'node3']
    L = Ledger('0')
    print(L.blockchain_balances)
    verify_boolean, change = L.verify_transaction(transactions, 1)
    if verify_boolean:
        L.add_balance_state(change[0], 1)
    for node in nodes:
        print('Balance: ', node, ': ', L.get_curr_balance_for_node(node))
    print(L.blockchain_balances)
    print("total currency: ", L.get_total_currency_in_chain())