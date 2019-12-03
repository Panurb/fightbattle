import numpy as np
from numpy.linalg import norm

import pygame

from collider import Circle, Group, Type
from helpers import random_unit, norm2, rotate


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
        pygame.draw.circle(screen, image_handler.debug_color, camera.world_to_screen(self.position), 2)
        self.collider.draw(screen, camera, image_handler)


class PhysicsObject(GameObject):
    def __init__(self, position, velocity=(0, 0), image_path='', size=1.0, gravity_scale=1.0):
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
        self.gravity_scale = gravity_scale

        self.active = True

    def set_position(self, position):
        super().set_position(position)
        self.velocity[:] = np.zeros(2)

    def rotate(self, delta_angle):
        self.angle += delta_angle
        self.collider.rotate(delta_angle)
        r = self.collider.position - self.position
        self.collider.position = self.position + rotate(r, delta_angle)
        self.image_position = rotate(r, delta_angle)

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

        if self.collider is None:
            return

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

            n = collision.overlap
            self.velocity -= 2 * self.velocity.dot(n) * n / norm2(n)
            self.velocity *= self.bounce

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
    def __init__(self, position, velocity=(0, 0), image_path='', debris_path='', size=1.0, debris_size=1.0,
                 health=100):
        super().__init__(position, velocity, image_path, size)
        self.health = health
        self.debris_path = debris_path
        self.destroyed = False
        self.debris = []
        self.debris_size = debris_size

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
            v = 0.8 * random_unit()
            d = PhysicsObject(self.position, v, image_path=self.debris_path, size=self.debris_size)
            d.add_collider(Circle([0, 0], 0.1, Group.DEBRIS))
            self.debris.append(d)

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if self.destroyed:
            if self.collider and self.collider.group is not Group.NONE:
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


class Animation:
    def __init__(self, xs, ys, angles):
        self.xs = xs
        self.ys = ys
        self.angles = angles
        self.times = np.arange(len(xs))
        self.time = 0.0
        self.direction = 1

    def update(self, time_step):
        self.time += time_step
        if self.time < 0:
            self.time += self.times[-1]
        if self.time > self.times[-1]:
            self.time -= self.times[-1]

        x = np.interp(self.time, self.times, self.xs)
        y = np.interp(self.time, self.times, self.ys)

        position = np.array([x, y])
        angle = np.interp(self.time, self.times, self.angles)

        return position, angle


class AnimatedObject(PhysicsObject):
    def __init__(self, position, image_path, size):
        super().__init__(position, image_path=image_path, size=size)
        self.animations = dict()
        self.animation = 'idle'
        self.animation_direction = 1
        self.loop = False

    def add_animation(self, xs, ys, angles, name):
        self.animations[name] = Animation(xs, ys, angles)

    def loop_animation(self, name, time=0):
        self.animation = name
        self.animations[self.animation].time = time
        self.loop = True

    def play_animation(self, name):
        self.animation = name
        self.animations[self.animation].time = 0
        self.loop = False

    def animate(self, time_step):
        anim = self.animations[self.animation]
        pos, angle = anim.update(self.animation_direction * time_step)

        pos[0] *= self.direction

        self.set_position(self.position + pos)
        self.angle = self.direction * angle

        if not self.loop and anim.time >= anim.times[-1]:
            self.loop_animation('idle')
