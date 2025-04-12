import pickle
import socket

from ipaddress import ip_network
from concurrent.futures import ThreadPoolExecutor, as_completed


PACKET_SIZE = 2500


def scan_ip(ip, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)  # Set a short timeout for responsiveness
            if s.connect_ex((str(ip), port)) == 0:  # Check if the port is open
                return str(ip)
    except Exception:
        pass
    return None


def list_sockets_on_port(port, network_cidr):
    """
    Scan the LAN for open sockets on the specified port using multithreading.

    :param port: Port to check for open sockets.
    :param network_cidr: CIDR notation of the LAN (e.g., '192.168.1.0/24').
    :return: A list of IPs with open sockets on the specified port.
    """
    open_sockets = []
    with ThreadPoolExecutor(max_workers=50) as executor:  # Adjust max_workers as needed
        futures = {executor.submit(scan_ip, ip, port): ip for ip in ip_network(network_cidr, strict=False).hosts()}
        for future in as_completed(futures):
            result = future.result()
            if result:
                open_sockets.append(result)
    return open_sockets


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
