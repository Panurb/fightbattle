import socket
from _thread import *
import pickle

import pygame

from collider import Group
from level import Level
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
        print("Server started, waiting for a connection")

        self.players = dict()
        self.level = Level('lvl', True)

        self.colliders = [[[] for _ in range(int(self.level.height + 1))] for _ in range(int(self.level.width + 1))]

        for wall in self.level.walls:
            wall.collider.update_occupied_squares(self.colliders)

        for obj in self.level.objects.values():
            obj.collider.update_occupied_squares(self.colliders)

    def add_player(self, network_id):
        player = Player([0, 0], -1, network_id)
        player.set_spawn(self.level, self.players)
        self.players[network_id] = player

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
        conn.send(pickle.dumps(data))

        while True:
            try:
                data = pickle.loads(conn.recv(1500))

                if not data:
                    print('Disconnected')
                    break

                player = self.players[p]
                old_health = player.health
                player.apply_data(data[0])
                player.health = old_health

                if len(data) == 2:
                    obj = self.level.objects[data[1][0]]
                    obj.apply_data(data[1])
                    obj.parent = player

                    if isinstance(obj, Gun) and obj.attacked:
                        bs = obj.attack()
                        for b in bs:
                            self.level.add_object(b)
                            b.collider.update_occupied_squares(self.colliders)

                reply = [[v.get_data() for v in self.players.values()],
                         [o.get_data() for o in self.level.objects.values()]]

                reply = pickle.dumps(reply)

                if len(reply) > 1500:
                    print('Packet too large:', len(reply))

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
            self.level.update(time_step, self.colliders)
            self.level.clear_sounds()

            for p in self.players.values():
                if p.health <= 0:
                    p.timer += time_step

            clock.tick(60)


if __name__ == '__main__':
    s = Server()
    s.start()
