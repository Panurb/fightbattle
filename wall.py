import numpy as np
import pygame

from gameobject import GameObject
from collider import Rectangle, Group
from helpers import basis


class Wall(GameObject):
    def __init__(self, position, width, height, angle):
        super().__init__(position)
        self.add_collider(Rectangle([0, 0], width, height, Group.WALLS))
        self.collider.rotate(angle)
        self.angle = angle
        self.image_path = 'wall'
        self.image_position[1] = 0.05

    def draw(self, screen, camera, image_handler):
        width = int(2 * self.collider.half_width[0])

        offset = 0.0 if width % 2 else 0.5

        for i in range(-width // 2 + 1, width // 2 + 1):
            self.image_position[0] = i - offset
            GameObject.draw(self, screen, camera, image_handler)

        size = int(camera.zoom / 20)

        start = camera.world_to_screen(self.position + np.array([width / 2, 0.7]))
        end = camera.world_to_screen(self.position + np.array([width / 2, -0.6]))
        pygame.draw.line(screen, pygame.Color('black'), start, end, size)

        start = camera.world_to_screen(self.position + np.array([-width / 2, 0.7]))
        end = camera.world_to_screen(self.position + np.array([-width / 2, -0.6]))
        pygame.draw.line(screen, pygame.Color('black'), start, end, size)


class Platform(Wall):
    def __init__(self, position, width):
        super().__init__(position, width, 1, 0.0)
        self.collider.group = Group.PLATFORMS
        self.image_path = 'platform'
        self.image_position[1] = 0.33

    def draw(self, screen, camera, image_handler):
        width = int(2 * self.collider.half_width[0])

        offset = 0.0 if width % 2 else 0.5

        for i in range(-width // 2 + 1, width // 2 + 1):
            self.image_position[0] = i - offset
            GameObject.draw(self, screen, camera, image_handler)

        size = int(camera.zoom / 20)

        start = camera.world_to_screen(self.position + np.array([width / 2, 0.65]))
        end = camera.world_to_screen(self.position + np.array([width / 2, 0.25]))
        pygame.draw.line(screen, pygame.Color('black'), start, end, size)

        start = camera.world_to_screen(self.position + np.array([-width / 2, 0.65]))
        end = camera.world_to_screen(self.position + np.array([-width / 2, 0.25]))
        pygame.draw.line(screen, pygame.Color('black'), start, end, size)
