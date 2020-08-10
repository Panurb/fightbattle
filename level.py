import os
import pickle

import numpy as np
import pyglet
from PIL import Image

from collider import Rectangle
from drawable import Decal
from gameobject import GameObject, Destroyable
from goal import Basket
from helpers import basis
from prop import Crate
from wall import Wall, Platform, Scoreboard
from weapon import Gun, Bullet, Grenade


class Level:
    def __init__(self, path='', server=False, editor=False):
        self.name = path.split(os.sep)[1] if path else ''
        self.path = path
        self.player_spawns = []

        self.walls = []
        self.objects = dict()
        self.goals = []
        self.scoreboard = None
        self.background = None
        self.walls_sprite = None
        self.decals = []

        self.gravity = np.array([0, -25.0])
        self.id_count = 0

        self.server = server
        self.editor = editor

        self.width = 0.0
        self.height = 0.0
        self.position = np.zeros(2)

        self.light = None
        self.dust = True

        if self.path:
            with open(os.path.join('data', 'levels', self.path) + '.pickle', 'rb') as f:
                self.apply_data(pickle.load(f))

    def reset(self):
        for g in self.goals:
            if type(g) is Basket:
                g.reset()
                
        for o in self.objects.values():
            o.delete()
        self.objects.clear()

        if self.path:
            with open(os.path.join('data', 'levels', self.path) + '.pickle', 'rb') as f:
                data = pickle.load(f)
                for o in data[2]:
                    self.id_count += 1
                    self.objects[o[0]] = o[1](o[2:4])
                    self.objects[o[0]].apply_data(o)

                offset = 0.5 * np.array([self.width, self.height]) - self.position

                for o in self.objects.values():
                    o.set_position(o.position + offset)
                    o.dust = self.dust

    def delete(self):
        for g in self.goals:
            g.delete()
        if self.scoreboard:
            self.scoreboard.delete()
        for obj in self.objects.values():
            obj.delete()
        for w in self.walls:
            w.delete()
        if self.light:
            self.light.delete()
        for p in self.player_spawns:
            p.delete()

    def clear(self):
        self.delete()
        self.player_spawns.clear()
        self.walls.clear()
        self.objects.clear()
        self.light = None
        self.scoreboard = None

    def get_data(self):
        data = (tuple(p.get_data() for p in self.player_spawns), tuple(w.get_data() for w in self.walls),
                tuple(o.get_data() for o in self.objects.values()), tuple(g.get_data() for g in self.goals))

        if self.scoreboard:
            data += (self.scoreboard.get_data(),)

        return data

    def apply_data(self, data):
        for d in data[0]:
            self.player_spawns.append(PlayerSpawn(d[0:2], d[2]))

        for d in data[1]:
            w = d[0]([d[1], d[2]], *d[3:])
            self.walls.append(w)

        for o in data[2]:
            self.id_count += 1
            self.objects[o[0]] = o[1]([o[2], o[3]])
            self.objects[o[0]].apply_data(o)

        for d in data[3]:
            goal = d[0]([d[1], d[2]], d[3])
            self.goals.append(goal)

        if len(data) == 5:
            self.scoreboard = Scoreboard([0, 0])
            self.scoreboard.apply_data(data[4])

        self.update_shape()

        offset = 0.5 * np.array([self.width, self.height]) - self.position

        for w in self.walls:
            w.set_position(w.position + offset)

        self.walls.sort(key=lambda x: x.position[1])

        for o in self.objects.values():
            o.set_position(o.position + offset)

        for p in self.player_spawns:
            p.set_position(p.position + offset)

        for g in self.goals:
            g.set_position(g.position + offset)

        if self.scoreboard:
            self.scoreboard.set_position(self.scoreboard.position + offset)

        self.light = GameObject([0.5 * self.width, self.height - 2], 'lamp', layer=3)

    def update_shape(self):
        x_min = np.inf
        y_min = np.inf

        x_max = -np.inf
        y_max = -np.inf

        for w in self.walls:
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
            if not obj.grabbed:
                obj.update(self.gravity, time_step, colliders)

            if type(obj) is Crate and obj.destroyed:
                if obj.loot_list:
                    loot = np.random.choice(obj.loot_list)(obj.position)
                    loot.velocity[:] = obj.velocity + 10.0 * basis(1)
                    loot.angular_velocity = 5.0 * np.sign(obj.velocity[0] + 1e-3)
                    loot.dust = self.dust
                    self.add_object(loot)
                    loot.collider.update_occupied_squares(colliders)
                    obj.loot_list.clear()

            if type(obj) is Grenade and obj.attacked:
                obj.attack()

            if isinstance(obj, Destroyable):
                if obj.destroyed and (self.server or (not obj.active)):
                    obj.delete()
                    del self.objects[k]
                    continue
            elif isinstance(obj, Gun):
                if obj.attacked:
                    bs = obj.attack()
                    for b in bs:
                        self.add_object(b)
                        b.collider.update_occupied_squares(colliders)
            elif isinstance(obj, Bullet):
                if obj.destroyed and (self.server or not obj.particle_clouds):
                    obj.collider.clear_occupied_squares(colliders)
                    if obj.sprite:
                        obj.sprite.delete()
                    del self.objects[k]
                    continue

        if self.scoreboard:
            for g in self.goals:
                self.scoreboard.scores[g.team] = g.score

    def draw(self, batch, camera, image_handler):
        if not self.editor and self.width > 0 and self.height > 0:
            if self.background is None:
                self.background = Background(self.width, self.height)
                self.background.draw(batch, camera, image_handler)
                self.background.add_decal(image_handler, 'light', self.light.position, scale=2)
                for p in self.player_spawns:
                    self.background.add_decal(image_handler, 'door', p.position + p.image_position)
                for g in self.goals:
                    self.background.add_decal(image_handler, g.image_path, g.position + g.image_position)
            else:
                self.background.draw(batch, camera, image_handler)

            if self.walls_sprite is None:
                width = int(self.width * 100)
                height = int(self.height * 100)
                image = Image.new('RGBA', (width, height), (0, 0, 0, 0))

                for wall in self.walls:
                    if int(wall.position[0]) == 0 or int(wall.position[0]) == self.width - 1:
                        wall.border = True
                    if int(wall.position[1]) == 0 or int(wall.position[1]) == self.height - 1:
                        wall.border = True

                for wall in self.walls:
                    wall.blit_to_image(image, image_handler, self.light)

                for wall in self.walls:
                    wall.blit_to_image(image, image_handler)

                image = pyglet.image.ImageData(width, height, 'RGBA', image.tobytes())

                self.walls_sprite = pyglet.sprite.Sprite(img=image, x=0, y=0, batch=batch, group=camera.layers[3])

            self.walls_sprite.update(*camera.world_to_screen(np.zeros(2)), scale=camera.zoom / 100)
        else:
            for w in self.walls:
                w.draw(batch, camera, image_handler)

        for g in self.goals:
            if type(g) is Basket:
                g.front.draw(batch, camera, image_handler)

        if self.scoreboard:
            self.scoreboard.draw(batch, camera, image_handler)

        for obj in list(self.objects.values()):
            if (isinstance(obj, Bullet) or type(obj) is Grenade) and obj.decal:
                self.decals.append(Decal(obj.position, obj.decal, size=np.random.random() + 1,
                                         angle=2*np.pi*np.random.random()))
                obj.decal = ''

            obj.draw(batch, camera, image_handler)

        for b in self.decals:
            b.draw(batch, camera, image_handler)

        if self.light:
            self.light.draw(batch, camera, image_handler)

    def draw_shadow(self, screen, camera, image_handler):
        for g in self.goals:
            g.draw_shadow(screen, camera, image_handler, self.light)

        for o in self.objects.values():
            o.draw_shadow(screen, camera, image_handler, self.light)

    def debug_draw(self, screen, camera, image_handler):
        for wall in self.walls:
            wall.debug_draw(screen, camera, image_handler)

        for g in self.goals:
            g.debug_draw(screen, camera, image_handler)

        for obj in self.objects.values():
            obj.debug_draw(screen, camera, image_handler)

    def play_sounds(self, sound_handler):
        for o in self.objects.values():
            o.play_sounds(sound_handler)

    def clear_sounds(self):
        for o in self.objects.values():
            o.sounds.clear()


class PlayerSpawn(GameObject):
    def __init__(self, position, team='blue'):
        super().__init__(position, image_path='door')
        self.team = team
        self.add_collider(Rectangle([0, 0], 1, 3))
        self.image_position = 0.45 * basis(1)

    def get_data(self):
        return tuple(self.position) + (self.team,)

    def apply_data(self, data):
        self.set_position(np.array(data[0:2]))
        self.team = data[2]

    def change_team(self):
        self.team = 'blue' if self.team == 'red' else 'red'


class Background:
    def __init__(self, width, height):
        self.position = 1.05 * np.ones(2)
        self.width = width - 2
        self.height = height - 2
        self.resolution = [int(100 * self.width), int(100 * self.height)]
        self.image = Image.new('RGBA', self.resolution, (150, 150, 150))
        self.sprite = None
        self.layer = 0
        self.number_of_decals = 10
        self.image_changed = False

    def draw(self, batch, camera, image_handler):
        if not self.sprite:
            image = pyglet.image.ImageData(*self.resolution, 'RGBA', self.image.tobytes())
            self.sprite = pyglet.sprite.Sprite(img=image, x=0, y=0, batch=batch, group=camera.layers[self.layer])

            for _ in range(self.number_of_decals):
                x = np.random.random() * self.width
                y = np.random.random() * self.height
                angle = 2 * np.pi * np.random.random()
                scale = np.random.uniform(1.0, 1.5)
                path = np.random.choice(['crack', 'crack2'])
                self.add_decal(image_handler, path, [x, y], angle, scale)

            for _ in range(self.number_of_decals):
                x = np.random.random() * self.width
                y = np.random.random() * self.height
                angle = 0.5 * (np.random.random() - 0.5)
                path = np.random.choice(['warning', 'poster', 'radioactive'])
                self.add_decal(image_handler, path, [x, y], angle)

        if self.image_changed:
            image = pyglet.image.ImageData(*self.resolution, 'RGBA', self.image.tobytes())
            self.sprite.image = image
            self.image_changed = False

        self.sprite.update(*camera.world_to_screen(self.position), scale=camera.zoom / 100)

    def add_decal(self, image_handler, path, position, angle=0, scale=1.0):
        decal = image_handler.decals[path].rotate(-np.rad2deg(angle) + 180, expand=1)
        decal = decal.resize([int(scale * x) for x in decal.size], Image.ANTIALIAS)
        pos = [int(100 * position[0] - 0.5 * decal.width - 100), int(100 * position[1] - 0.5 * decal.height - 100)]
        self.image.paste(decal, pos, decal.convert('RGBA'))
        self.image_changed = True
