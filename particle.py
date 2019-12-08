import numpy as np
from numpy.linalg import norm
import pygame

from helpers import polar_angle


class Cloud:
    def __init__(self, position, direction, number, lifetime, size, gravity_scale=1.0, image_path='',
                 start_color=(255, 255, 255), end_color=(255, 255, 255)):
        self.position = position
        self.gravity_scale = gravity_scale
        self.particles = []
        if np.any(direction):
            angle = polar_angle(direction)
        else:
            angle = None
        v_norm = norm(direction)
        for _ in range(number):
            if angle is None:
                v = v_norm * np.random.normal(size=2)
            else:
                theta = np.random.normal(angle, 0.25)
                r = norm(direction)
                r = np.abs(np.random.normal(v_norm, v_norm))
                v = r * np.array([np.cos(theta), np.sin(theta)])
            self.particles.append(Particle(self.position, v, lifetime, size, image_path, start_color, end_color))

    def update(self, gravity, time_step):
        for p in self.particles:
            p.update(self.gravity_scale * gravity, time_step)
            if p.size < 1e-3:
                self.particles.remove(p)

    def draw(self, screen, camera, image_handler):
        for p in self.particles:
            p.draw(screen, camera, image_handler)


class Splatter(Cloud):
    def __init__(self, position, direction):
        if np.any(direction):
            number = 20
        else:
            number = 50
        super().__init__(position, direction, number, 8.0, 0.8, image_path='blood')


class Particle:
    def __init__(self, position, velocity, lifetime, size, image_path='', start_color=(255, 255, 255),
                 end_color=(255, 255, 255)):
        self.velocity = np.array(velocity, dtype=float)
        self.position = np.array(position, dtype=float)
        self.acceleration = np.zeros(2)
        self.gravity_scale = 1.0
        self.size = size
        self.max_size = size
        self.image_path = image_path
        self.image = None
        self.start_color = np.array(start_color, dtype=int)
        self.end_color = np.array(end_color, dtype=int)
        self.time = 0
        self.lifetime = lifetime

    def update(self, gravity, time_step):
        self.time += time_step
        delta_pos = self.velocity * time_step + 0.5 * self.acceleration * time_step**2
        self.position += delta_pos
        acc_old = self.acceleration.copy()
        self.acceleration = self.gravity_scale * gravity

        self.size = (1 - self.time / self.lifetime) * self.max_size

        self.velocity += 0.5 * (acc_old + self.acceleration) * time_step

    def draw(self, screen, camera, image_handler):
        if self.image_path:
            image = image_handler.images[self.image_path]

            scale = camera.zoom * self.size / 100

            # TODO: use scale
            self.image = pygame.transform.rotozoom(image, 0.0, scale)

            rect = self.image.get_rect()
            rect.center = camera.world_to_screen(self.position)

            screen.blit(self.image, rect)
        else:
            c = self.start_color + self.time / self.lifetime * (self.end_color - self.start_color)
            s = int(camera.zoom * self.size)
            pygame.draw.circle(screen, c, camera.world_to_screen(self.position), s)
