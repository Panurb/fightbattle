import numpy as np
from numpy.linalg import norm
import pygame

from helpers import polar_angle, polar_to_carteesian, rotate


class Cloud:
    def __init__(self, position, velocity, number, lifetime, size, gravity_scale=1.0, image_path='',
                 start_color=(255, 255, 255), end_color=(255, 255, 255), base_velocity=(0, 0)):
        self.position = position
        self.velocity = np.array(base_velocity, dtype=float)
        self.lifetime = lifetime
        self.size = size
        self.gravity_scale = gravity_scale
        self.image_path = image_path
        self.start_color = np.array(start_color, dtype=int)
        self.end_color = np.array(end_color, dtype=int)

        self.particles = []
        self.time = 0.0

        self.add_particles(velocity, number)

    def add_particles(self, velocity, number):
        if np.any(velocity):
            angle = polar_angle(velocity)
        else:
            angle = None
        v_norm = norm(velocity)
        for _ in range(number):
            if angle is None:
                v = v_norm * np.random.normal(size=2)
            else:
                theta = np.random.normal(angle, 0.25)
                r = np.abs(np.random.normal(v_norm, v_norm))
                v = polar_to_carteesian(r, theta) + 0.5 * self.velocity
            self.particles.append(Particle(self.position, v))

    def update(self, gravity, time_step):
        self.time += time_step
        if self.time >= self.lifetime:
            self.particles.clear()

        for p in self.particles:
            p.update(self.gravity_scale * gravity, time_step)

    def draw(self, screen, camera, image_handler):
        size = (1 - self.time / self.lifetime) * self.size
        if self.image_path:
            scale = camera.zoom * size / 100

            img = image_handler.images[self.image_path]
            # TODO: use scale
            image = pygame.transform.rotozoom(img, 0.0, scale)

            for p in self.particles:
                rect = image.get_rect()
                rect.center = camera.world_to_screen(p.position)

                screen.blit(image, rect)
        else:
            for p in self.particles:
                c = self.start_color + self.time / self.lifetime * (self.end_color - self.start_color)
                s = int(camera.zoom * size)
                pygame.draw.circle(screen, c, camera.world_to_screen(p.position), s)


class BloodSplatter(Cloud):
    def __init__(self, position, direction):
        if np.any(direction):
            number = 20
        else:
            number = 50
        super().__init__(position, direction, number, 8.0, 0.8, image_path='blood')


class MuzzleFlash(Cloud):
    def __init__(self, position, velocity, base_velocity=(0, 0)):
        super().__init__(position, velocity, 3, 10.0, 0.3, base_velocity=base_velocity, gravity_scale=0.0,
                         start_color=(255, 255, 200), end_color=(255, 215, 0))
        self.add_particles(rotate(0.5 * velocity, 0.5 * np.pi), 3)
        self.add_particles(rotate(0.5 * velocity, -0.5 * np.pi), 3)


class Particle:
    def __init__(self, position, velocity):
        self.velocity = np.array(velocity, dtype=float)
        self.position = np.array(position, dtype=float)
        self.acceleration = np.zeros(2)

    def update(self, gravity, time_step):
        delta_pos = self.velocity * time_step + 0.5 * self.acceleration * time_step**2
        self.position += delta_pos
        acc_old = self.acceleration.copy()
        self.acceleration = gravity

        self.velocity += 0.5 * (acc_old + self.acceleration) * time_step
