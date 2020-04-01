import socket
from _thread import *
import pickle

import pygame

from collider import Group
from player import Player


class Server:
    def __init__(self, server, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.sock.bind((server, port))
        except socket.error as e:
            str(e)

        self.sock.listen(2)
        print("Waiting for a connection, Server Started")

        self.players = dict()
        with open('data/levels/lvl.pickle', 'rb') as f:
            self.level = pickle.load(f)

        self.colliders = dict()
        for g in Group:
            if g not in [Group.NONE, Group.PLAYERS, Group.HITBOXES]:
                self.colliders[g] = []

        for wall in self.level.walls:
            self.colliders[wall.collider.group].append(wall.collider)

        for obj in self.level.objects:
            self.colliders[obj.collider.group].append(obj.collider)

    def start(self):
        start_new_thread(self.physics_thread, ())
        p = 0
        while True:
            conn, addr = self.sock.accept()
            print("Connected to:", addr)

            start_new_thread(self.threaded_client, (conn, p))
            p += 1

    def threaded_client(self, conn, p):
        self.players[p] = Player([0, 0], network_id=p)
        conn.send(pickle.dumps(self.players[p]))

        while True:
            try:
                data = pickle.loads(conn.recv(2048 * 20))
                self.players[p] = data[0]
                if data[1]:
                    for i, o in enumerate(self.level.objects):
                        if o.id == data[1][0].id:
                            o.set_position(data[1][0].position)
                            o.velocity[:] = data[1][0].velocity
                            break

                if not data:
                    print('Disconnected')
                    break
                else:
                    reply = [[v for v in self.players.values() if v.network_id != p],
                             [o for o in self.level.objects if o.parent is None or o.parent.id != self.players[p].id]]
                conn.sendall(pickle.dumps(reply))
            except:
                break

        print("Lost connection")
        conn.close()

    def physics_thread(self):
        clock = pygame.time.Clock()

        while True:
            self.level.clear_sounds()
            self.level.update(15.0 / 60, self.colliders)
            clock.tick(60)


if __name__ == '__main__':
    s = Server('84.249.49.75', 5555)
    s.start()
