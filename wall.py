import numpy as np
import pygame
import pyglet
from numpy.linalg import norm

from gameobject import GameObject
from collider import Rectangle, Group, ColliderGroup, Circle
from helpers import basis, rotate


class Wall(GameObject):
    def __init__(self, position, width, height):
        super().__init__(position, image_path='wall')
        self.add_collider(Rectangle([0, 0], width, height, Group.WALLS))
        self.size = 1.0
        self.vertical = False

        self.image_position = -0.7 * basis(1)
        if width == 1:
            self.vertical = True
            self.image_position = np.array([-0.5, -0.2])

        self.sprites = []

    def get_data(self):
        return (type(self), self.position[0], self.position[1],
                2 * self.collider.half_width[0], 2 * self.collider.half_height[1])

    def draw(self, batch, camera, image_handler):
        if self.vertical:
            h = self.collider.half_height[1]
            ny = int(2 * h)
            if not self.sprites:
                self.sprites = ny * [None]

            for j, y in enumerate(np.linspace(-h, h, ny, False)):
                if j == 0:
                    l = 0
                elif j == ny - 1:
                    l = 2
                else:
                    l = 1

                pos = self.position + self.image_position + y * basis(1)
                if len(self.sprites) < j + 1:
                    self.sprites.append(None)
                self.sprites[j] = camera.draw_image(image_handler, f'{self.image_path}_vertical_0_{l}', pos, 1, 1, 0.0,
                                                    batch=batch, layer=0, sprite=self.sprites[j])
        else:
            w = self.collider.half_width[0]
            nx = int(2 * w)
            if not self.sprites:
                self.sprites = nx * [None]

            for i, x in enumerate(np.linspace(-w, w, nx, False)):
                if i == 0:
                    k = 0
                elif i == nx - 1:
                    k = 2
                else:
                    k = 1

                pos = self.position + self.image_position + x * basis(0)
                self.sprites[i] = camera.draw_image(image_handler, f'{self.image_path}_{k}_{0}', pos, 1, 1, 0.0,
                                                    batch=batch, layer=0, sprite=self.sprites[i])

    def draw_front(self, screen, camera, image_handler):
        pass

    def draw_shadow(self, screen, camera, image_handler, light):
        self.collider.draw_shadow(screen, camera, image_handler, light)


class Platform(Wall):
    def __init__(self, position, width):
        super().__init__(position, width, 1)
        self.collider.group = Group.PLATFORMS
        self.image_path = 'platform'
        self.image_position = np.array([0.5, 0.33])

    def get_data(self):
        return type(self), self.position[0], self.position[1], 2 * self.collider.half_width[0]


class Basket(GameObject):
    def __init__(self, position, team=0):
        super().__init__(position, image_path='basket')
        self.image_position = np.array([0.4, -0.15])
        self.add_collider(ColliderGroup(self.position))
        self.collider.add_collider(Circle([-0.3, 0.0], 0.1, Group.WALLS))
        self.collider.add_collider(Circle([1.3, 0.0], 0.1, Group.WALLS))
        self.collider.add_collider(Circle([0.5, -0.5], 0.2, Group.GOALS))
        self.collider.add_collider(Rectangle([0.5, -0.9], 1.4, -0.5, Group.WALLS))
        self.team = team
        self.score = 0
        self.front = GameObject(self.position, 'basket_front', layer=3)
        self.front.image_position = np.array([0.4, -0.7])

    def get_data(self):
        return type(self), self.position[0], self.position[1], self.team

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        self.front.draw(batch, camera, image_handler)

    def draw_shadow(self, batch, camera, image_handler, light):
        super().draw_shadow(batch, camera, image_handler, light)
        self.front.draw_shadow(batch, camera, image_handler, light)


class Scoreboard(GameObject):
    def __init__(self, position):
        super().__init__(position)
        self.add_collider(Rectangle([0, 0], 7, 4))
        self.scores = [0, 0]

    def draw(self, batch, camera, image_handler):
        camera.draw_polygon(batch, self.collider.corners(), (10, 10, 10))
        camera.draw_rectangle(batch, self.position, self.collider.width, self.collider.height, (80, 80, 80), 5)

        text = ' - '.join(map(str, self.scores))
        camera.draw_text(batch, text, self.position, 3, 'Seven Segment.ttf', (200, 255, 0))

    def update(self, gravity, time_step, colliders):
        pass
