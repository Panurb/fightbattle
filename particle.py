import numpy as np
from numpy.linalg import norm
import pygame

from helpers import polar_angle, polar_to_cartesian, norm2, random_unit, basis


class Cloud:
    def __init__(self, position, velocity, number, lifetime, size, gravity_scale=1.0, image_path='',
                 start_color=(255, 255, 255), end_color=(255, 255, 255), base_velocity=(0, 0), shading=0.0, shine=0.0,
                 stretch=0.0):
        self.position = np.repeat(np.array(position, dtype=float)[np.newaxis], number, axis=0)
        self.velocity = 0.5 * np.repeat(np.array(base_velocity, dtype=float)[np.newaxis], number, axis=0)
        self.acceleration = np.zeros_like(self.position)
        self.lifetime = lifetime
        self.size = size
        self.gravity_scale = gravity_scale
        self.image_path = image_path
        self.start_color = np.array(start_color, dtype=int)
        self.end_color = np.array(end_color, dtype=int)
        self.shading = shading
        self.shine = shine
        self.stretch = stretch

        self.time = 0.0

        self.add_particles(velocity, number)
        self.active = True

    def add_particles(self, velocity, number):
        if np.any(velocity):
            angle = polar_angle(velocity)
        else:
            angle = None

        v_norm = norm(velocity)
        for i in range(number):
            if angle is None:
                v = 0.5 * random_unit()
            else:
                theta = np.random.normal(angle, 0.25)
                r = np.abs(np.random.normal(v_norm, v_norm))
                v = polar_to_cartesian(r, theta)
            self.velocity[i, :] += v

    def update(self, gravity, time_step):
        self.time += time_step
        if self.time >= self.lifetime:
            self.active = False
            return

        delta_pos = self.velocity * time_step + 0.5 * self.acceleration * time_step**2
        self.position += delta_pos
        acc_old = self.acceleration.copy()
        self.acceleration[:] = self.gravity_scale * gravity

        self.velocity += 0.5 * (acc_old + self.acceleration) * time_step

    def draw(self, screen, camera, image_handler):
        if not self.active:
            return

        size = int(camera.zoom * (1 - self.time / self.lifetime) * self.size)
        if size == 0:
            return

        if self.image_path:
            scale = size / 100

            img = image_handler.images[self.image_path]
            image = pygame.transform.rotozoom(img, 0.0, scale)

            for p in self.position:
                rect = image.get_rect()
                rect.center = camera.world_to_screen(p)

                screen.blit(image, rect)
        else:
            color = self.start_color + self.time / self.lifetime * (self.end_color - self.start_color)
            size = [(1 + self.stretch * norm2(self.velocity)) * size, size]
            for i, p in enumerate(self.position):
                surface = pygame.Surface(size)
                surface.set_colorkey(pygame.Color('black'))

                if self.shading:
                    pygame.draw.ellipse(surface, (1 - self.shading) * color, [0, 0] + size)
                    pygame.draw.ellipse(surface, color, [size[0] // 4, 0, 0.8 * size[0], 0.8 * size[1]])
                else:
                    pygame.draw.ellipse(surface, color, [0, 0] + size)

                if self.shine:
                    pygame.draw.circle(surface, color + (255 - color) * self.shine, [int(0.8 * size[0]), size[1] // 2],
                                       size[1] // 5)

                surface = pygame.transform.rotate(surface, np.degrees(polar_angle(self.velocity[i, :])))
                pos = camera.world_to_screen(p)
                screen.blit(surface, [pos[0] - 0.5 * size[0], pos[1] - 0.5 * size[1]])


class BloodSplatter(Cloud):
    def __init__(self, position, direction, number=10):
        super().__init__(position, direction, number, 10.0, 0.5, start_color=(255, 0, 0), end_color=(255, 0, 0),
                         shading=0.17, shine=1.0, stretch=0.5)


class MuzzleFlash(Cloud):
    def __init__(self, position, velocity, base_velocity=(0, 0)):
        super().__init__(position, velocity, 3, 10.0, 0.8, base_velocity=base_velocity, gravity_scale=0.0,
                         start_color=(255, 255, 200), end_color=(255, 215, 0))


class Explosion(Cloud):
    def __init__(self, position):
        super().__init__(position, np.zeros(2), 10, 8.0, 5.0, gravity_scale=0.0, start_color=(255, 255, 255),
                         end_color=(50, 50, 50), shading=0.2)


class Sparks(Cloud):
    def __init__(self, position, velocity):
        super().__init__(position, velocity, 3, 5.0, 0.4)
