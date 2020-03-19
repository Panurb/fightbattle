import numpy as np

from collider import Rectangle
from gameobject import GameObject
from helpers import basis
from wall import Wall


class Level:
    def __init__(self):
        self.player_spawns = []

        self.walls = []
        self.objects = []

        self.gravity = np.array([0, -0.1])

    def add_wall(self, position, width, height, angle=0.0):
        wall = Wall(position, width, height, angle)
        self.walls.append(wall)

    def add_object(self, obj):
        self.objects.append(obj)

    def add_room(self, position, width, height):
        self.add_wall(position + 0.5 * width * basis(0), 1, height)
        self.add_wall(position - 0.5 * width * basis(0), 1, height)
        self.add_wall(position + 0.5 * height * basis(1), width, 1)
        self.add_wall(position - 0.5 * height * basis(1), width, 1)

    def update(self, time_step, colliders):
        for obj in self.objects:
            obj.update(self.gravity, time_step, colliders)

    def draw(self, screen, camera, image_handler):
        for wall in self.walls:
            wall.draw(screen, camera, image_handler)

        for obj in self.objects:
            obj.draw(screen, camera, image_handler)

    def debug_draw(self, screen, camera, image_handler):
        for wall in self.walls:
            wall.debug_draw(screen, camera, image_handler)

        for obj in self.objects:
            obj.debug_draw(screen, camera, image_handler)


class PlayerSpawn(GameObject):
    def __init__(self, position):
        super().__init__(position)

        self.add_collider(Rectangle([0, 0], 1, 3))
