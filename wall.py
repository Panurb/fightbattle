import numpy as np
import pygame

from gameobject import GameObject
from collider import Rectangle, Group


class Wall(GameObject):
    def __init__(self, position, width, height, angle=0.0):
        super().__init__(position)
        self.add_collider(Rectangle([0, 0], width, height, Group.WALLS))
        self.collider.rotate(angle)
        self.angle = angle
        self.size = 1.0
        self.vertical = False

        if width == 1:
            self.vertical = True

    def get_data(self):
        return self.position[0], self.position[1], 2 * self.collider.half_width[0], 2 * self.collider.half_height[1]

    def draw(self, screen, camera, image_handler):
        if self.vertical:
            h = self.collider.half_height[1]
            ny = int(2 * h)

            for j, y in enumerate(np.linspace(-h, h, ny, False)):
                if j == 0:
                    l = 2
                elif j == ny - 1:
                    l = 0
                else:
                    l = 1

                self.image_position[0] = 0.5
                self.image_position[1] = y + 0.52
                self.image_path = f'wall_vertical_0_{l}'
                GameObject.draw(self, screen, camera, image_handler)
        else:
            w = self.collider.half_width[0]
            nx = int(2 * w)

            for i, x in enumerate(np.linspace(-w, w, nx, False)):
                if i == 0:
                    k = 0
                elif i == nx - 1:
                    k = 2
                else:
                    k = 1

                self.image_position[0] = x + 0.5
                self.image_position[1] = 0.04
                self.image_path = f'wall_{k}_0'
                GameObject.draw(self, screen, camera, image_handler)


class Platform(Wall):
    def __init__(self, position, width):
        super().__init__(position, width, -1, 0.0)
        self.collider.group = Group.PLATFORMS
        self.image_path = 'platform'
        self.image_position[1] = 0.33

    def draw(self, screen, camera, image_handler):
        w = self.collider.half_width[0]
        nx = int(2 * w)

        for i, x in enumerate(np.linspace(-w, w, nx, False)):
            if i == 0:
                k = 0
            elif i == nx - 1:
                k = 2
            else:
                k = 1

            self.image_position[0] = x + 0.5
            self.image_position[1] = 0.33
            self.image_path = f'platform_{k}_0'
            GameObject.draw(self, screen, camera, image_handler)
