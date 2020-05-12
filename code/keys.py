import cryptography
from time import clock
from Messenger import Messenger
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes


# Much of this code came from :
# https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/

class Test:
    def __init__(self):
        self.m = Messenger('0', self)

        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        self.string_public_key = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")
        #print(self.string_public_key)

        self.msg = b'secret'

    def handle_incoming_message(self, msg_dict: dict):
        print(msg_dict)
        key_string = msg_dict['key'].encode("utf-8")
        incoming_public_key = serialization.load_pem_public_key(
            key_string,
            backend=default_backend()
        )
        signature = self.private_key.sign(
            self.msg,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        print(type(signature), signature)
        string_sig = signature.hex()
        print(type(string_sig), string_sig)
        sig = bytes.fromhex(string_sig)
        try:
            incoming_public_key.verify(
                sig,
                self.msg,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            print("\nsig valid")
        except cryptography.exceptions.InvalidSignature:
            print("\nwrong!!!!!")

t = Test()
t.m.send({'key': t.string_public_key}, '0')
start = clock()
while clock() - start < 5:
    continue


        # def handle_incoming_message(self, msg_dict: dict):
        #     public_pickle
#

#
#
