import pickle
import socket

import psutil

PACKET_SIZE = 2500


def list_sockets_on_port(port):
    connections = psutil.net_connections(kind='inet')  # Get all IPv4 and IPv6 connections

    filtered_connections = []

    for conn in connections:
        if conn.laddr and conn.laddr.port == port:  # Filter by the specified port
            filtered_connections.append(conn.laddr)

    return filtered_connections


class Network:
    def __init__(self, server):
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

    def close(self):
        self.client.close()
