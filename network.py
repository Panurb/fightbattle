import socket
import pickle


PACKET_SIZE = 2500


class Network:
    def __init__(self):
        server = socket.gethostbyname(socket.gethostname())
        port = 5555
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = (server, port)
        self.data = self.connect()

    def connect(self):
        try:
            self.client.connect(self.addr)
            return pickle.loads(self.client.recv(5000))
        except:
            pass

    def send(self, data):
        try:
            self.client.send(pickle.dumps(data))
            reply = self.client.recv(PACKET_SIZE)
            return pickle.loads(reply)
        except socket.error as e:
            print(e)
