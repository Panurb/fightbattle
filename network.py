import socket
import pickle


class Network:
    def __init__(self):
        server = '25.97.148.11'
        port = 5555
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = (server, port)
        self.data = self.connect()

    def connect(self):
        try:
            self.client.connect(self.addr)
            return pickle.loads(self.client.recv(4096))
        except:
            pass

    def send(self, data):
        try:
            self.client.send(pickle.dumps(data))
            return pickle.loads(self.client.recv(4096))
        except socket.error as e:
            print(e)
