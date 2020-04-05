import socket
from _thread import *
import pickle

import pygame

from collider import Group
from gameobject import Destroyable
from player import Player
from weapon import Gun, Bullet


class Server:
    def __init__(self):
        server = socket.gethostbyname(socket.gethostname())
        server = '25.97.148.11'
        port = 5555
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
            self.colliders[g] = []

        for wall in self.level.walls:
            self.colliders[wall.collider.group].append(wall.collider)

        for obj in self.level.objects.values():
            self.colliders[obj.collider.group].append(obj.collider)

        self.respawn_time = 50.0

    def add_player(self, network_id):
        player = Player([0, 0], -1, network_id)
        player.set_spawn(self.level, self.players)
        self.players[network_id] = player
        self.colliders[player.collider.group].append(player.collider)
        self.colliders[player.head.collider.group].append(player.head.collider)
        self.colliders[player.body.collider.group].append(player.body.collider)

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
        data = [self.players[p].get_data(),
                [o.get_data() for o in self.level.objects.values()]]
        conn.send(pickle.dumps(data))

        while True:
            try:
                data = pickle.loads(conn.recv(4096))

                if not data:
                    print('Disconnected')
                    break

                player = self.players[p]
                old_health = player.health
                player.apply_data(data[0])
                player.health = old_health

                if player.health <= 0 and player.timer >= self.respawn_time:
                    player.reset(self.colliders)

                if len(data) == 2:
                    obj = self.level.objects[data[1][0]]
                    obj.apply_data(data[1])
                    obj.parent = player
                    if isinstance(obj, Gun) and obj.attacked:
                        bs = obj.attack()
                        for b in bs:
                            self.level.objects[b.id] = b

                reply = [[v.get_data() for v in self.players.values()],
                         [o.get_data() for o in self.level.objects.values()]]

                reply = pickle.dumps(reply)

                if len(reply) > 4096:
                    print('Package too large')

                conn.sendall(reply)
            except:
                break

        print("Lost connection")
        conn.close()
        del self.players[p]

    def physics_thread(self):
        clock = pygame.time.Clock()
        time_step = 15.0 / 60

        while True:
            self.level.clear_sounds()
            self.level.update(time_step, self.colliders)

            for p in self.players.values():
                if p.health <= 0:
                    p.timer += time_step

            clock.tick(60)


if __name__ == '__main__':
    s = Server()
    s.start()
