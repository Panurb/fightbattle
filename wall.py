import pygame

from gameobject import GameObject
from collider import Rectangle, Group


class Wall(GameObject):
    def __init__(self, position, width, height, angle):
        super().__init__(position)
        collider = Rectangle([0, 0], width, height, Group.WALLS)
        self.add_collider(collider)
        self.collider.rotate(angle)
        self.angle = angle

    def draw(self, screen, camera, image_handler):
        points = []
        for c in self.collider.corners():
            points.append(camera.world_to_screen(c))

        pygame.draw.polygon(screen, pygame.Color('gray'), points)
        pygame.draw.polygon(screen, pygame.Color('black'), points, int(camera.zoom / 25))
