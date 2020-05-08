import hashlib, json, datetime


class Transaction:
    """
    This class holds all attributes that define a transaction within the BlockChain network.

    Attributes
    _________
    to_node: str
        the node the amount of currency is being transferred to
    from_node: str
        the node the amount of currency is being transferred from.
    amount : str
        the amount of currency being transferred
    timestamp: str
        timestamp of when the transaction was created
    unique_id: str
        hash of the transaction contents. Unique to that transaction. Used to identify transactions in network.

    Methods
    _______
    txHeaderToJSON()
        return a JSON string representation of the transaction attributes but not the unique_id
    generateIDh()
        return a hash representation of the JSON form of the transaction attributes to use as a unique_id

    """
    def __init__(self, json_string = '', _to: str = '', _from: str = '', amount: float = 0.0):
        """
        Transaction constructor. Takes a JSON string or a set of variables to init instance variables

        :param json_string: str. Used to construct transaction entirely from a JSON representation.
        :param _to: str. Used if JSON string parameter not used.
        :param _from: str. Used if JSON string parameter not used.
        :param amount: str. Used if JSON string parameter not used.
        """
        # if a json string parameter is given, use that to construct the object
        if json_string != '':
            json_obj = json.loads(json_string)
            self.to_node = json_obj['to_node']
            self.from_node = json_obj['from_node']
            self.amount = json_obj['amount']
            self.timestamp = json_obj['timestamp']
            self.unique_id = json_obj['unique_id']
        else:  # else use given parameters to construct new tx
            self.to_node = _to
            self.from_node = _from
            self.amount = amount
            self.timestamp = str(datetime.datetime.now())
            self.unique_id = self.generateIDh()  # hash of to, from, amount, timestamp

    def txHeaderToJSON(self) -> str:
        """
        return a JSON string representation of the transaction attributes but not the unique_id

        :return: str
        """
        self_dict = {
            'to_node': self.to_node,
            'from_node': self.from_node,
            'amount': self.amount,
            'timestamp': self.timestamp
        }
        return json.dumps(self_dict)

    def generateIDh(self) -> str:
        """
        return a hash representation of the JSON form of the transaction attributes to use as a unique_id

        :return: str
        """
        hashMe = self.txHeaderToJSON()
        return hashlib.sha256(hashMe.encode()).hexdigest()

    def __str__(self) -> str:
        """
        override of the string representation. Return the JSON representation of the object attributes.
        :return: str.
        """
        return json.dumps(self.__dict__)

    def __eq__(self, _in) -> bool:
        """
        Override of the equality attribute. Transactions are the same if their unique IDs are equivalent.

        :param _in: str. Transaction to compare with self.
        :return: bool.
        """
        return _in.unique_id == self.unique_id


if __name__ == '__main__':
    t = Transaction(_to='node1', _from='node2', amount=12.5)
    print(str(t))
    jsonT = str(t)
    backToT = Transaction(json_string=jsonT)
    print(type(backToT))
    print(str(backToT))
