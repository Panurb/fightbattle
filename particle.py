import numpy as np
import pyglet
from numpy.linalg import norm
import pygame

from helpers import polar_angle, polar_to_cartesian, norm2, random_unit, basis


class Cloud:
    def __init__(self, position, velocity, number, lifetime, size, gravity_scale=1.0,
                 start_color=(255, 255, 255), end_color=(255, 255, 255), base_velocity=(0, 0), shading=0.0, shine=0.0,
                 stretch=0.0):
        self.lifetime = lifetime
        self.time = 0.0

        self.particles = []

        self.active = True

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

            self.particles.append(Particle(position, base_velocity + v, lifetime=lifetime, size=size,
                                           gravity_scale=gravity_scale, start_color=start_color,
                                           end_color=end_color, shading=shading, shine=shine, stretch=stretch))

    def update(self, gravity, time_step):
        self.time += time_step
        if self.time >= self.lifetime:
            self.active = False
            for p in self.particles:
                for v in p.vertex_list:
                    if v:
                        v.delete()

            self.particles.clear()
            return

        for p in self.particles:
            p.update(gravity, time_step)

    def draw(self, batch, camera):
        if not self.active:
            return

        for p in self.particles:
            p.draw(batch, camera)


class Particle:
    def __init__(self, position, velocity, lifetime, size, gravity_scale=1.0,
                 start_color=(255, 255, 255), end_color=(255, 255, 255), shading=0.0, shine=0.0, stretch=0.0):
        self.position = position.copy()
        self.velocity = velocity
        self.acceleration = np.zeros_like(self.position)
        self.lifetime = lifetime
        self.size = size
        self.gravity_scale = gravity_scale
        self.start_color = np.array(start_color, dtype=int)
        self.end_color = np.array(end_color, dtype=int)
        self.shading = shading
        self.shine = shine
        self.stretch = stretch
        self.vertex_list = [None, None, None]
        self.time = 0.0
        self.layer = 7

    def update(self, gravity, time_step):
        self.time = min(self.time + time_step, self.lifetime)

        delta_pos = self.velocity * time_step + 0.5 * self.acceleration * time_step**2
        self.position += delta_pos
        acc_old = self.acceleration.copy()
        self.acceleration[:] = self.gravity_scale * gravity

        self.velocity += 0.5 * (acc_old + self.acceleration) * time_step

    def draw(self, batch, camera):
        color = self.start_color + self.time / self.lifetime * (self.end_color - self.start_color)
        height = (1 - self.time / self.lifetime) * self.size
        width = (1 + self.stretch * norm2(self.velocity)) * height

        angle = polar_angle(self.velocity)

        if self.shading:
            self.vertex_list[0] = camera.draw_ellipse(self.position, width, height, angle, (1 - self.shading) * color,
                                                      batch=batch, layer=self.layer, vertex_list=self.vertex_list[0])

            self.vertex_list[1] = camera.draw_ellipse(self.position + 0.25 * width * basis(0),
                                                      0.8 * width, 0.8 * height, angle, color,
                                                      batch=batch, layer=self.layer, vertex_list=self.vertex_list[1])
        else:
            self.vertex_list[0] = camera.draw_ellipse(self.position, width, height, angle, color,
                                                      batch=batch, layer=self.layer, vertex_list=self.vertex_list[0])

        if self.shine:
            self.vertex_list[2] = camera.draw_circle(self.position + np.array([0.8 * width, 0.5 * height]), 0.2 * height,
                                                     color + (255 - color) * self.shine,
                                                     batch=batch, layer=self.layer, vertex_list=self.vertex_list[2])


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
        super().__init__(position, 0.2 * velocity, number, 5.0, 0.5, gravity_scale=0.5, start_color=(200, 200, 200),
                         end_color=(200, 200, 200), shading=0.1)
