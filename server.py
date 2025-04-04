import os
import socket
from _thread import *
import pickle

import pygame

from inputhandler import Controller
from level import Level
from network import PACKET_SIZE
from player import Player
from weapon import Gun


class Server:
    def __init__(self):
        server = socket.gethostbyname(socket.gethostname())
        port = 5555
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.sock.bind((server, port))
        except socket.error as e:
            str(e)

        self.sock.listen(2)
        print(f'Server started, ip={server}, waiting for a connection')

        self.players = dict()
        self.controllers = dict()
        self.level = None
        self.colliders = []

        self.load_level(os.path.join('multiplayer', 'circle'))

    def load_level(self, name):
        self.level = Level(name, server=True)
        self.level.dust = False

        self.colliders.clear()

        self.colliders = [[[] for _ in range(int(self.level.height))] for _ in range(int(self.level.width))]

        for wall in self.level.walls:
            wall.collider.update_occupied_squares(self.colliders)

        for goal in self.level.goals:
            goal.collider.update_occupied_squares(self.colliders)

        for obj in self.level.objects.values():
            obj.collider.update_occupied_squares(self.colliders)

    def add_player(self, network_id):
        player = Player([0, 0], -1, network_id)
        player.set_spawn(self.level, self.players)
        self.players[network_id] = player
        self.controllers[network_id] = Controller(-1)

    def start(self):
        start_new_thread(self.physics_thread, ())
        p = 0
        while True:
            conn, addr = self.sock.accept()
            print("Connected to:", addr)

            start_new_thread(self.threaded_client, (conn, p))
            p += 1

    def threaded_client(self, conn, p):
        self.add_player(p)
        data = [self.players[p].get_data(), self.level.get_data()]
        #print(len(pickle.dumps(data)))
        conn.send(pickle.dumps(data))

        while True:
            try:
                data = pickle.loads(conn.recv(PACKET_SIZE))

                if not data:
                    break

                player_data, object_data = data

                player = self.players[p]
                player.apply_data(player_data)

                object_id = player_data[-1]
                if object_id != -1:
                    obj = self.level.objects[object_id]
                    obj.apply_data(object_data)

                    if isinstance(obj, Gun) and obj.bullets_spawned:
                        bs = obj.attack()
                        for b in bs:
                            self.level.add_object(b)
                            b.collider.update_occupied_squares(self.colliders)

                reply = [[v.get_data() for v in self.players.values() if v.network_id != p],
                         [o.get_data() for i, o in self.level.objects.items() if i != object_id],]

                reply = pickle.dumps(reply)

                if len(reply) > PACKET_SIZE:
                    print('Packet too large:', len(reply))

                conn.sendall(reply)
            except:
                break

        print("Lost connection")
        conn.close()
        del self.players[p]

    def physics_thread(self):
        clock = pygame.time.Clock()
        time_step = 1.0 / 60

        while True:
            grabbed_objects = set()

            for p in self.players.values():
                p.input(self.controllers[p.network_id])
                p.update(self.level.gravity, time_step, self.colliders)

                if p.object_id != -1:
                    grabbed_objects.add(p.object_id)

            self.level.update(time_step, self.colliders)
            self.level.clear_sounds()

            for i, o in list(self.level.objects.items()):
                if o.grabbed and i not in grabbed_objects:
                    o.grabbed = False

            clock.tick(60)


if __name__ == '__main__':
    s = Server()
    s.start()
