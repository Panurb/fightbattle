import numpy as np
from numpy.linalg import norm
import pygame


class Cloud:
    def __init__(self, position, direction):
        self.position = position
        self.particles = []
        for _ in range(20):
            v = np.random.normal(size=2)
            v *= 0.25 / norm(v)
            self.particles.append(Particle(self.position, v, 10))

    def update(self, gravity, time_step):
        for p in self.particles:
            p.update(gravity, time_step, self.particles)

    def draw(self, screen, camera):
        for p in self.particles:
            p.draw(screen, camera)


class Particle:
    def __init__(self, position, velocity, size):
        self.position = np.array(position, dtype=float)
        self.velocity = np.array(velocity, dtype=float)
        self.acceleration = np.zeros(2)
        self.gravity_scale = 1.0
        self.size = size
        self.color = (255, 0, 0)

    def update(self, gravity, time_step, particles):
        delta_pos = self.velocity * time_step + 0.5 * self.acceleration * time_step**2
        self.position += delta_pos
        acc_old = self.acceleration.copy()
        self.acceleration = self.gravity_scale * gravity

        if self.size > 1:
            self.size -= 0.25

        #for p in particles:
        #    r = p.position - self.position
        #    r_norm = norm(r)
        #    if r_norm != 0:
        #        self.acceleration += 0.001 * r / r_norm

        self.velocity += 0.5 * (acc_old + self.acceleration) * time_step

    def draw(self, screen, camera):
        pygame.draw.circle(screen, self.color, camera.world_to_screen(self.position), int(self.size))
