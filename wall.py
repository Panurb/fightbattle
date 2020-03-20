import numpy as np
import pygame

from gameobject import GameObject
from collider import Rectangle, Group


class Wall(GameObject):
    def __init__(self, position, width, height, angle):
        super().__init__(position)
        self.add_collider(Rectangle([0, 0], width, height, Group.WALLS))
        self.collider.rotate(angle)
        self.angle = angle

    def draw(self, screen, camera, image_handler):
        points = []
        for c in self.collider.corners():
            points.append(camera.world_to_screen(c))

        pygame.draw.polygon(screen, pygame.Color('gray'), points)
        pygame.draw.polygon(screen, pygame.Color('black'), points, int(max(1, camera.zoom / 25)))


class Platform(Wall):
    def __init__(self, position, width):
        super().__init__(position, width, 1, 0.0)
        self.collider.group = Group.PLATFORMS
        self.image_path = 'platform'

    def draw(self, screen, camera, image_handler):
        width = int(2 * self.collider.half_width[0])
        if width % 2:
            for i in range(-width // 2, width // 2 + 1):
                self.image_position[0] = i
                GameObject.draw(self, screen, camera, image_handler)
        else:
            for i in range(-width // 2 + 1, width // 2 + 1):
                self.image_position[0] = i
                GameObject.draw(self, screen, camera, image_handler)
