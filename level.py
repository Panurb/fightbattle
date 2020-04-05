import numpy as np

from collider import Rectangle
from gameobject import GameObject, Destroyable
from prop import Crate
from wall import Wall, Platform
from weapon import Gun, Bullet


class Level:
    def __init__(self):
        self.player_spawns = []

        self.walls = []
        self.objects = dict()
        self.background = []

        self.gravity = np.array([0, -0.1])

    def add_wall(self, position, width, height, angle=0.0):
        wall = Wall(position, width, height, angle)
        self.walls.append(wall)

    def add_platform(self, position, width):
        plat = Platform(position, width)
        self.walls.append(plat)

    def add_object(self, obj):
        self.objects[obj.id] = obj

    def update(self, time_step, colliders):
        for k in list(self.objects):
            obj = self.objects[k]

            obj.update(self.gravity, time_step, colliders)

            if type(obj) is Crate and obj.loot is not None and not obj.loot.active:
                self.objects[obj.loot.id] = obj.loot
                colliders[obj.loot.collider.group].append(obj.loot.collider)
                obj.loot.active = True

            if isinstance(obj, Gun) and obj.attacked:
                bs = obj.attack()
                for b in bs:
                    self.objects[b.id] = b

            if isinstance(obj, Destroyable):
                if obj.destroyed and not obj.debris:
                    del self.objects[k]

            if isinstance(obj, Bullet):
                if obj.destroyed and not obj.particle_clouds:
                    del self.objects[k]

    def draw(self, screen, camera, image_handler):
        for wall in self.walls:
            wall.draw(screen, camera, image_handler)

        for obj in self.objects.values():
            obj.draw(screen, camera, image_handler)

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
