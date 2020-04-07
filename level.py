import pickle

import numpy as np

from collider import Rectangle
from gameobject import GameObject, Destroyable
from prop import Crate
from wall import Wall, Platform
from weapon import Gun, Bullet


class Level:
    def __init__(self, name='', server=False):
        self.player_spawns = []

        self.walls = []
        self.objects = dict()
        self.background = []

        self.gravity = np.array([0, -0.1])
        self.id_count = 0

        self.server = server

        if name:
            with open(f'data/levels/{name}.pickle', 'rb') as f:
                self.apply_data(pickle.load(f))

    def clear(self):
        self.player_spawns.clear()
        self.walls.clear()
        self.objects.clear()

    def get_data(self):
        return (tuple(p.get_data() for p in self.player_spawns), tuple(w.get_data() for w in self.walls),
                tuple(o.get_data() for o in self.objects.values()))

    def apply_data(self, data):
        for p in data[0]:
            self.player_spawns.append(PlayerSpawn(p))

        for w in data[1]:
            if w[3] < 0:
                self.walls.append(Platform([w[0], w[1]], w[2]))
            else:
                self.walls.append(Wall([w[0], w[1]], w[2], w[3]))

        for o in data[2]:
            self.id_count += 1
            self.objects[o[0]] = o[1]([o[2], o[3]])
            self.objects[o[0]].apply_data(o)

    def add_wall(self, position, width, height, angle=0.0):
        wall = Wall(position, width, height, angle)
        self.walls.append(wall)

    def add_platform(self, position, width):
        plat = Platform(position, width)
        self.walls.append(plat)

    def add_object(self, obj):
        obj.id = self.id_count
        self.objects[self.id_count] = obj
        self.id_count += 1

    def update(self, time_step, colliders):
        for k in list(self.objects.keys()):
            obj = self.objects[k]
            obj.update(self.gravity, time_step, colliders)

            if type(obj) is Crate and obj.destroyed:
                if obj.loot_list:
                    loot = np.random.choice(obj.loot_list)(obj.position)
                    self.add_object(loot)
                    colliders[loot.collider.group].append(loot.collider)
                    obj.loot_list.clear()

            if isinstance(obj, Destroyable):
                if obj.destroyed and (self.server or not obj.debris):
                    del self.objects[k]
                    continue
            elif isinstance(obj, Gun) and obj.attacked:
                bs = obj.attack()
                for b in bs:
                    self.add_object(b)
                    colliders[b.collider.group].append(b.collider)
            elif isinstance(obj, Bullet):
                if obj.destroyed and (self.server or not obj.particle_clouds):
                    del self.objects[k]
                    continue

    def draw(self, screen, camera, image_handler):
        for wall in self.walls:
            wall.draw(screen, camera, image_handler)

        for obj in list(self.objects.values()):
            obj.draw(screen, camera, image_handler)

    def debug_draw(self, screen, camera, image_handler):
        for wall in self.walls:
            wall.debug_draw(screen, camera, image_handler)

        for obj in self.objects.values():
            obj.debug_draw(screen, camera, image_handler)

    def play_sounds(self, sound_handler):
        for o in list(self.objects.values()):
            o.play_sounds(sound_handler)

    def clear_sounds(self):
        for o in self.objects.values():
            o.sounds.clear()


class PlayerSpawn(GameObject):
    def __init__(self, position):
        super().__init__(position)

        self.add_collider(Rectangle([0, 0], 1, 3))

    def get_data(self):
        return tuple(self.position)

    def apply_data(self, data):
        self.set_position(np.array(data))
