import pickle

import numpy as np
import pygame

from collider import Rectangle, Group
from gameobject import GameObject, Destroyable
from helpers import basis
from prop import Crate, Ball
from wall import Wall, Platform, Basket, Scoreboard
from weapon import Gun, Bullet, Grenade


class Level:
    def __init__(self, name='', server=False):
        self.name = name
        self.player_spawns = []

        self.walls = []
        self.objects = dict()
        self.scoreboard = None
        self.background = None

        self.gravity = np.array([0, -0.1])
        self.id_count = 0

        self.server = server

        self.width = 0.0
        self.height = 0.0
        self.position = np.zeros(2)

        self.light = np.zeros(2)

        if self.name:
            with open(f'data/levels/{self.name}.pickle', 'rb') as f:
                self.apply_data(pickle.load(f))

    def reset(self):
        for w in self.walls:
            if type(w) is Basket:
                w.collider.colliders[-1].group = Group.WALLS

        self.objects.clear()
        if self.name:
            with open(f'data/levels/{self.name}.pickle', 'rb') as f:
                data = pickle.load(f)
                for o in data[2]:
                    self.id_count += 1
                    self.objects[o[0]] = o[1]([o[2], o[3]])
                    self.objects[o[0]].apply_data(o)

                offset = 0.5 * np.array([self.width, self.height]) - self.position

                for o in self.objects.values():
                    o.set_position(o.position + offset)

    def clear(self):
        self.player_spawns.clear()
        self.walls.clear()
        self.objects.clear()

    def get_data(self):
        return (tuple(p.get_data() for p in self.player_spawns), tuple(w.get_data() for w in self.walls),
                tuple(o.get_data() for o in self.objects.values()), self.scoreboard.get_data())

    def apply_data(self, data):
        for p in data[0]:
            self.player_spawns.append(PlayerSpawn(p))

        # FIXME: hardcoded index
        i = 1
        for d in data[1]:
            w = d[0]([d[1], d[2]], *d[3:])
            self.walls.append(w)
            if d[0] is Basket:
                w.team = i
                i -= 1

        for o in data[2]:
            self.id_count += 1
            self.objects[o[0]] = o[1]([o[2], o[3]])
            self.objects[o[0]].apply_data(o)

        self.update_shape()

        offset = 0.5 * np.array([self.width, self.height]) - self.position

        for w in self.walls:
            w.set_position(w.position + offset)

        for o in self.objects.values():
            o.set_position(o.position + offset)

        for p in self.player_spawns:
            p.set_position(p.position + offset)

        self.scoreboard = Scoreboard([0, 0])
        self.scoreboard.apply_data(data[-1])

        self.light = np.array([0.5 * self.width, self.height])

    def update_shape(self):
        x_min = np.inf
        y_min = np.inf

        x_max = -np.inf
        y_max = -np.inf

        for w in self.walls:
            if type(w) is Basket:
                continue

            x_min = min(x_min, w.position[0] - w.collider.half_width[0])
            y_min = min(y_min, w.position[1] - w.collider.half_height[1])

            x_max = max(x_max, w.position[0] + w.collider.half_width[0])
            y_max = max(y_max, w.position[1] + w.collider.half_height[1])

        self.width = x_max - x_min
        self.height = y_max - y_min

        self.position = np.array([x_min + 0.5 * self.width, y_min + 0.5 * self.height])

    def add_wall(self, position, width, height):
        wall = Wall(position, width, height)
        self.walls.append(wall)

    def add_platform(self, position, width):
        plat = Platform(position, width)
        self.walls.append(plat)

    def add_object(self, obj):
        obj.id = self.id_count
        self.objects[self.id_count] = obj
        self.id_count += 1

    def update(self, time_step, colliders):
        for k, obj in list(self.objects.items()):
            obj.update(self.gravity, time_step, colliders)

            if type(obj) is Crate and obj.destroyed:
                if obj.loot_list:
                    loot = np.random.choice(obj.loot_list)(obj.position)
                    loot.velocity[:] = obj.velocity
                    loot.angular_velocity = 0.5 * np.sign(obj.velocity[0])
                    self.add_object(loot)
                    loot.collider.update_occupied_squares(colliders)
                    obj.loot_list.clear()

            if type(obj) is Grenade and obj.attacked:
                obj.attack()

            if isinstance(obj, Destroyable):
                if obj.destroyed and (self.server or (not obj.active)):
                    del self.objects[k]
                    continue
            elif isinstance(obj, Gun) and obj.attacked:
                bs = obj.attack()
                for b in bs:
                    self.add_object(b)
                    b.collider.update_occupied_squares(colliders)
            elif isinstance(obj, Bullet):
                if obj.destroyed and (self.server or not obj.particle_clouds):
                    obj.collider.clear_occupied_squares(colliders)
                    del self.objects[k]
                    continue

    def draw(self, screen, camera, image_handler):
        #image = pygame.transform.scale(self.background, 0.0, 2 * camera.zoom / 100)
        #rect = image.get_rect()
        #rect.center = self.world_to_screen(position)
        screen.blit(self.background, camera.world_to_screen(np.array([0, self.height])))

        for wall in self.walls:
            wall.draw(screen, camera, image_handler)

        if self.scoreboard:
            self.scoreboard.draw(screen, camera, image_handler)

        for obj in self.objects.values():
            if type(obj) is Bullet and obj.destroyed:
                image = image_handler.images['blood']
                pos = obj.position * camera.zoom
                pos[1] -= 0.5 * self.height * camera.zoom
                pos[1] *= -1
                pos[1] += 0.5 * self.height * camera.zoom
                self.background.blit(image, pos)

            obj.draw(screen, camera, image_handler)

        for w in self.walls:
            w.draw_front(screen, camera, image_handler)

    def draw_shadow(self, screen, camera, image_handler):
        for w in self.walls:
            w.draw_shadow(screen, camera, image_handler, self.light)

        for o in self.objects.values():
            o.draw_shadow(screen, camera, image_handler, self.light)

    def debug_draw(self, screen, camera, image_handler):
        for wall in self.walls:
            wall.debug_draw(screen, camera, image_handler)

        for obj in self.objects.values():
            obj.debug_draw(screen, camera, image_handler)

    def play_sounds(self, sound_handler):
        for o in self.objects.values():
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
