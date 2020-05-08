from time import sleep, clock
from datetime import datetime
from threading import Thread
import boto3, botocore, random

message_queue_URLs = {
	'0': 'https://sqs.us-east-1.amazonaws.com/622058021374/0.fifo',
	'1': 'https://sqs.us-east-1.amazonaws.com/622058021374/1.fifo',
	'2': 'https://sqs.us-east-1.amazonaws.com/622058021374/2.fifo',
	'3': 'https://sqs.us-east-1.amazonaws.com/622058021374/3.fifo',
	}

class Messenger:
	"""
	This class is a generic message handler for the RAFT system, using hardcoded
	SQS queues to communicate with other nodes. The nodes accessible using this
	class are  '0', '1', '2', '3'
	This class requires the handle_incoming_message(message) interface

	methods:
		__init__(id, target) : constructor
		start_incoming_message_thread() : starts a 'receive message' thread
		listen_for_messages() : receive messages, pass to parent target

		send(message: dict, destination: str) : <-must be formatted correctly for SQS
	"""

	def __init__(self, id: str, target, run: bool=True):
		"""
		Messenger constructor. Takes id from list
		'0', '1', '2', '3', '4', 'leader', 'client-blue', 'client-red'.
		Constructor must be passed a reference to the class that is using it.
		That class must implement handle_incoming_message(message: dict)
		"""
		self.id = id #id of self in system
		self.run = run
		self.sqs = boto3.client('sqs') # make a new SQS object
		self.incoming_queue_URL = message_queue_URLs[self.id] # store URL of queue for self
		self.target = target    # store class that is using this messenger

		# start a thread to pull incoming messages from queue
		self.incoming_message_thread = self.start_incoming_message_thread()
		self.msg_count = 0

	def start_incoming_message_thread(self):
		"""this method threads @listen_for_messages()"""
		t = Thread(
			target=self.listen_for_messages,
			name=('Incoming Message Thread'+self.id),
			daemon=True #this thread should always be running
			)
		t.start()
		return t

	def off(self):
		self.run = False

	def on(self):
		self.run = True

	def listen_for_messages(self):
		''' loop that pulls messages from given SQS queue

		messages attributes are kept in dictionary form and represent the
		message intended to be received. Messages are then passed to the
		target class via the target.handle_incoming_message(message) interface
		'''
		while True:
			while self.run:
				# response stores results of receive call from SQS
				response = self.sqs.receive_message(
					QueueUrl=self.incoming_queue_URL,
					MaxNumberOfMessages=1,
					MessageAttributeNames=['All'],
					WaitTimeSeconds=0
				)

				# check if a message was received. if no message, try again
				if 'Messages' not in response:
					continue
				else:
					message = response['Messages'][0]['MessageAttributes']

				# this receipt handle is required to delete the  message from queue
				receipt_handle = response['Messages'][0]['ReceiptHandle']
				# delete the message after receiving
				try:
					self.sqs.delete_message(
						QueueUrl=self.incoming_queue_URL,
						ReceiptHandle=receipt_handle
					)
				except botocore.exceptions.ClientError:
					print("Receipt Handle Expired")
				# print('\n',self.id,' Received and deleted message : \n\"{}\"'.format(message))

				# this calls on the holding class to handle the messages,

				msg = self.reduce_message(message)

				self.target.handle_incoming_message(msg)


	def reduce_message(self, SQSmessage:dict) -> dict:
		msg = {}
		for key, value in SQSmessage.items():
			msg[key] = value['StringValue']
		return msg

	def format_for_SQS(self, message:dict) -> dict:
		SQSmsg = {}
		for key, value in message.items():
			SQSmsg[key] = {
				'DataType': 'String',
				'StringValue': value
				}
		return SQSmsg

	def send(self, message: dict, destination: str):
		'''
		send a message to the given destination queue.
		destination string should exist in the queue_suffixes list.
		'''
		# used to uniquely identify messages:
		self.msg_count += 1
		# included to ensure all messages have a different non-duplication hash:
		timestamp = str(datetime.now())

		message_body = 'Message # {} from {}. {}'.format(self.msg_count, self.id, timestamp)
		#print("message from {} to {}: ".format(self.id, destination), message)
		SQSmsg = self.format_for_SQS(message)

		# response stores confirmation data from SQS
		response = self.sqs.send_message(
			QueueUrl=message_queue_URLs[destination],
			MessageAttributes=SQSmsg,
			MessageGroupId='queue',
			MessageBody=message_body
		)


if __name__ == '__main__':

	message = {
		'attribute1': 'value1',
		'attribute2': 'value2',
		'attribute3': 'value3'
		}

	print(message)
	SQSmsg = {}
	for key, value in message.items():
		SQSmsg[key] = {
			'DataType': 'String',
			'StringValue': value
			}

	print(SQSmsg)


	'''
	Append Entries message attributes:
	{
		'messageType' : 'AppendEntriesRPC',
		'leaderId': self.id
		'term'  : str(self.current_term),
		'entries': [],
		'prevLogIndex' : 'self.prevLogIndex',
		'prevLogTerm' : 'self.prevLogTerm',
		'leaderCommit' : 'self.commitIndex'
	}

	Append Response message Attributes:
	{
		'messageType' : 'AppendReply',
		'senderID': self.id
		'term' : str(self.current_term),
		'success' : 'True'
	}

	Request Vote message attributes:
	{
		'messageType' : 'RequestVotesRPC',
		'term': str(self.current_term),
		'candidateID': self.id,
		'lastLogIndex': self.lastLogIndex,
		'lastLogTerm': self.lastLogTerm
	}

	Request Vote Reply:
	{
		'messageType' : 'VoteReply',
		'senderID' : self.id
		'term': str(self.current_term),
		'voteGranted': 'True'
	}

	'''