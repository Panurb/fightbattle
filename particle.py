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
        self.vertex_list = []

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

    def draw(self, batch, camera):
        if not self.active:
            return

        color = self.start_color + self.time / self.lifetime * (self.end_color - self.start_color)
        height = (1 - self.time / self.lifetime) * self.size
        width = (1 + self.stretch * norm2(self.velocity)) * height

        if not self.vertex_list:
            for i, p in enumerate(self.position):
                angle = np.degrees(polar_angle(self.velocity[i, :]))

                if self.shading:
                    camera.draw_ellipse(self.position[i, :], width, height,
                                        color=(1 - self.shading) * color, angle=angle, batch=batch, layer=2)
                    camera.draw_ellipse(self.position[i, :] + 0.25 * width * basis(0), 0.8 * width, 0.8 * height,
                                        color=color, angle=angle, batch=batch, layer=2)
                else:
                    camera.draw_ellipse(self.position[i, :], width, height, color=color, angle=angle,
                                        batch=batch, layer=2)

                if self.shine:
                    camera.draw_circle(self.position[i, :] + np.array([0.8 * width, 0.5 * height]), 0.2 * height,
                                       color=color + (255 - color) * self.shine, batch=batch, layer=2)
        else:
            for i, p in enumerate(self.position):
                angle = np.degrees(polar_angle(self.velocity[i, :]))

                if self.shading:
                    camera.draw_ellipse(self.position[i, :], width, height,
                                        color=(1 - self.shading) * color, angle=angle, batch=batch, layer=2)
                    camera.draw_ellipse(self.position[i, :] + 0.25 * width * basis(0), 0.8 * width, 0.8 * height,
                                        color=color, angle=angle, batch=batch, layer=2)
                else:
                    camera.draw_ellipse(self.position[i, :], width, height, color=color, angle=angle,
                                        batch=batch, layer=2)

                if self.shine:
                    camera.draw_circle(self.position[i, :] + np.array([0.8 * width, 0.5 * height]), 0.2 * height,
                                       color=color + (255 - color) * self.shine, batch=batch, layer=2)


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


class Dust(Cloud):
    def __init__(self, position, velocity, number):
        super().__init__(position, 0.2 * velocity, number, 5.0, 0.7, gravity_scale=0.5, start_color=(200, 200, 200),
                         end_color=(200, 200, 200), shading=0.2)
