from datetime import datetime
from time import sleep
from Transaction import Transaction
import boto3, random

message_queue_URLs = {
    '0': 'https://sqs.us-east-1.amazonaws.com/622058021374/0.fifo',
    '1': 'https://sqs.us-east-1.amazonaws.com/622058021374/1.fifo',
    '2': 'https://sqs.us-east-1.amazonaws.com/622058021374/2.fifo',
    '3': 'https://sqs.us-east-1.amazonaws.com/622058021374/3.fifo',
}


class Tx_Generator:
    def __init__(self):
        self.nodes = ['0', '1', '2', '3']
        self.sqs = boto3.client('sqs')  # make a new SQS object
        self.msg_count = 0

    def make_tx(self) -> str:
        from_node = self.nodes[random.randrange(4)]
        to_node = self.nodes[random.randrange(4)]
        while to_node == from_node:
            to_node = self.nodes[random.randrange(4)]

        amount = round(random.uniform(0.1, 2), 2)

        return str(Transaction(_from=str(from_node), _to=str(to_node), amount=amount))

    def format_for_SQS(self, message: dict) -> dict:
        SQSmsg = {}
        for key, value in message.items():
            SQSmsg[key] = {
                'DataType': 'String',
                'StringValue': value
            }
        return SQSmsg

    def send(self, message: dict, destination: str):
        # used to uniquely identify messages:
        self.msg_count += 1
        # included to ensure all messages have a different non-duplication hash:
        timestamp = str(datetime.now())
        message_body = 'Message # {} from tx Generator. {}'.format(self.msg_count, timestamp)
        SQSmsg = self.format_for_SQS(message)

        # response stores confirmation data from SQS
        response = self.sqs.send_message(
            QueueUrl=message_queue_URLs[destination],
            MessageAttributes=SQSmsg,
            MessageGroupId='queue',
            MessageBody=message_body
        )


if __name__ == '__main__':
    txg = Tx_Generator()
    while True:
        tx = txg.make_tx()
        msg_dict = {'contents': str(tx), 'type': 'Transaction'}
        for node in txg.nodes:
            not_this_node = txg.nodes[random.randrange(4)]
            if node == not_this_node:
                continue
            else:
                sleep(random.uniform(0.1, 1))
                txg.send(msg_dict, node)
        sleep(6)

        # if msg['type'] == 'Transaction':  # if transaction append to tx queue
        #     contents = json.loads(msg['contents'])
        #     # TODO: fix the sending side of this shit
        #     self.transaction_queue.append(Transaction(contents['transaction']))