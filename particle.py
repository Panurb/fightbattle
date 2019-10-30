import numpy as np
import pygame


class Cloud:
    def __init__(self, position, direction):
        self.position = position
        self.particles = []
        angle = np.arctan2(direction[1], direction[0]) + np.pi
        for _ in range(20):
            r = np.abs(np.random.normal(0.25, 0.5))
            theta = np.random.normal(angle, 0.25)
            v = r * np.array([np.cos(theta), np.sin(theta)])
            #v = 0.25 * np.random.normal(size=2)
            self.particles.append(Particle(self.position, v, 0.75, 'blood'))

    def update(self, gravity, time_step):
        for p in self.particles:
            p.update(gravity, time_step, self.particles)
            if p.size == 0:
                self.particles.remove(p)

    def draw(self, screen, camera, image_handler):
        for p in self.particles:
            p.draw(screen, camera, image_handler)


class Particle:
    def __init__(self, position, velocity, size, image_path):
        self.velocity = np.array(velocity, dtype=float)
        self.position = np.array(position, dtype=float)
        self.acceleration = np.zeros(2)
        self.gravity_scale = 1.0
        self.size = size
        self.image_path = image_path
        self.image = None

    def update(self, gravity, time_step, particles):
        delta_pos = self.velocity * time_step + 0.5 * self.acceleration * time_step**2
        self.position += delta_pos
        acc_old = self.acceleration.copy()
        self.acceleration = self.gravity_scale * gravity

        if self.size > 0:
            self.size -= 0.025

        self.velocity += 0.5 * (acc_old + self.acceleration) * time_step

    def draw(self, screen, camera, image_handler):
        image = image_handler.images[self.image_path]

        scale = camera.zoom * self.size / 100

        self.image = pygame.transform.rotozoom(image, 0.0, scale)

        rect = self.image.get_rect()
        rect.center = camera.world_to_screen(self.position)

        screen.blit(self.image, rect)
