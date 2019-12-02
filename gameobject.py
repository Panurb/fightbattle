import numpy as np
from numpy.linalg import norm

import pygame

from collider import Circle, Group, Type
from helpers import random_unit


MAX_SPEED = 5.0


class GameObject:
    def __init__(self, position, image_path='', size=1.0):
        super().__init__()
        self.position = np.array(position, dtype=float)
        self.collider = None
        self.collision = True
        self.direction = 1
        self.angle = 0.0

        self.image = None
        self.image_path = image_path
        self.size = size
        self.image_position = np.zeros(2)

    def flip_horizontally(self):
        if self.collider:
            self.collider.position[0] -= 2 * (self.collider.position - self.position)[0]

        self.direction *= -1
        self.image_position[0] *= -1

    def set_position(self, position):
        delta_pos = position - self.position

        self.position += delta_pos
        if self.collider:
            self.collider.position += delta_pos

    def add_collider(self, collider):
        self.collider = collider
        collider.parent = self
        collider.position += self.position

    def draw(self, screen, camera, image_handler):
        if not self.image_path:
            self.debug_draw(screen, camera, image_handler)
            return

        image = image_handler.images[self.image_path]

        scale = 1.05 * camera.zoom * self.size / 100

        if self.direction == -1:
            image = pygame.transform.flip(image, True, False)

        self.image = pygame.transform.rotozoom(image, np.degrees(self.angle), scale)

        rect = self.image.get_rect()
        rect.center = camera.world_to_screen(self.position + self.image_position)

        screen.blit(self.image, rect)

    def debug_draw(self, screen, camera, image_handler):
        self.collider.draw(screen, camera, image_handler)


class PhysicsObject(GameObject):
    def __init__(self, position, velocity=(0, 0), image_path='', size=1.0):
        super().__init__(position, image_path, size)
        self.velocity = np.array(velocity, dtype=float)
        self.speed = norm(self.velocity)
        self.acceleration = np.zeros(2)

        self.angular_velocity = 0.0
        self.angular_acceleration = 0.0

        self.bounce = 0.5
        self.on_ground = False
        self.mass = 1.0
        self.inertia = 0.0
        self.gravity_scale = 1.0

        self.active = True

    def set_position(self, position):
        super().set_position(position)
        self.velocity[:] = np.zeros(2)

    def rotate(self, delta_angle):
        self.angle += delta_angle
        self.collider.rotate(delta_angle)

    def rotate_90(self):
        self.angle += np.pi / 2
        self.collider.rotate_90()

    def get_acceleration(self, gravity):
        return self.gravity_scale * gravity

    def update(self, gravity, time_step, colliders):
        if not self.active:
            return

        if self.velocity[1] > 0:
            self.on_ground = False

        delta_pos = self.velocity * time_step + 0.5 * self.acceleration * time_step**2
        self.position += delta_pos
        acc_old = self.acceleration.copy()
        self.acceleration = self.get_acceleration(gravity)

        delta_angle = self.angular_velocity * time_step + 0.5 * self.angular_acceleration * time_step**2
        self.angle += delta_angle
        ang_acc_old = float(self.angular_acceleration)
        self.angular_acceleration = 0.0

        self.collider.position += delta_pos

        if delta_angle:
            self.collider.rotate(delta_angle)

        self.collider.update_collisions(colliders)

        if not self.collision:
            return

        for collision in self.collider.collisions:
            if not collision.collider.parent.collision:
                continue

            if collision.overlap[1] > 0:
                self.on_ground = True

            self.position += collision.overlap

            self.collider.position += collision.overlap

            if self.bounce:
                n = collision.overlap
                self.velocity -= 2 * self.velocity.dot(n) * n / n.dot(n)
                self.velocity *= self.bounce
            else:
                if not collision.overlap[0]:
                    self.velocity[1] = 0.0
                    self.acceleration[0] -= np.sign(self.velocity[0]) * collision.collider.friction
                elif not collision.overlap[1]:
                    self.velocity[0] = 0.0

        self.velocity += 0.5 * (acc_old + self.acceleration) * time_step
        self.angular_velocity += 0.5 * (ang_acc_old + self.angular_acceleration) * time_step

        if abs(self.velocity[0]) < 0.05:
            self.velocity[0] = 0.0

        self.speed = norm(self.velocity)
        if self.speed != 0:
            self.velocity *= min(self.speed, MAX_SPEED) / self.speed

        if self.collider.type is Type.CIRCLE:
            self.angular_velocity = -self.gravity_scale * self.velocity[0]

    def damage(self, amount, position, velocity):
        self.velocity += velocity


class Destroyable(PhysicsObject):
    def __init__(self, position, velocity=(0, 0), image_path='', size=1.0, health=100):
        super().__init__(position, velocity, image_path, size)
        self.health = health
        self.destroyed = False
        self.debris = []

    def damage(self, amount, position, velocity):
        if self.health > 0:
            self.health -= amount
            self.velocity += velocity

        if self.health <= 0 and not self.destroyed:
            self.destroy()

    def destroy(self):
        if self.destroyed:
            return

        self.destroyed = True
        for _ in range(4):
            v = random_unit()
            d = PhysicsObject(self.position, v, image_path='crate', size=0.5)
            d.add_collider(Circle([0, 0], 0.1, Group.DEBRIS))
            self.debris.append(d)

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if self.destroyed:
            if self.collider.group is not Group.NONE:
                colliders[self.collider.group].remove(self.collider)
                self.collider.group = Group.NONE

            debris_active = False
            for d in self.debris:
                d.update(gravity, time_step, colliders)
                if d.speed > norm(gravity) * time_step:
                    debris_active = True

            if not debris_active:
                self.active = False

    def draw(self, screen, camera, image_handler):
        if self.destroyed:
            for d in self.debris:
                d.draw(screen, camera, image_handler)
        else:
            super().draw(screen, camera, image_handler)


class Pendulum(PhysicsObject):
    def __init__(self, position, length, angle, image_path):
        super().__init__(position, np.zeros(2), image_path)
        self.support = position
        self.length = length
        self.angle = angle
        angle = self.angle - np.pi / 2
        self.position = self.support + self.length * np.array([np.cos(angle), np.sin(angle)])
        self.add_collider(Circle([0, 0], 0.1, Group.PROPS))
        self.friction = 0.5

    def draw(self, screen, camera, image_handler):
        self.angle -= np.pi / 2
        super().draw(screen, camera, image_handler)
        self.angle += np.pi / 2

        pygame.draw.circle(screen, image_handler.debug_color, camera.world_to_screen(self.support), 5)

    def update(self, gravity, time_step, colliders):
        if self.velocity[1] > 0:
            self.on_ground = False

        delta_angle = self.angular_velocity * time_step + 0.5 * self.angular_acceleration * time_step**2
        self.angle += delta_angle
        ang_acc_old = float(self.angular_acceleration)
        self.angular_acceleration = -self.gravity_scale * norm(gravity) / self.length * np.sin(self.angle)

        angle = self.angle - np.pi / 2
        self.set_position(self.support + self.length * np.array([np.cos(angle), np.sin(angle)]))

        if delta_angle:
            self.collider.rotate(delta_angle)

        self.collider.update_collisions(colliders)

        for collision in self.collider.collisions:
            if not collision.collider.parent.collision:
                continue

            if collision.overlap[1] > 0:
                self.on_ground = True

            self.position += collision.overlap

            self.collider.position += collision.overlap

            n = collision.overlap
            self.velocity -= 2 * self.velocity.dot(n) * n / n.dot(n)
            self.velocity *= self.bounce

        self.angular_velocity += 0.5 * (ang_acc_old + self.angular_acceleration) * time_step
