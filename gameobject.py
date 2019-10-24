import numpy as np
import enum

import pygame


class Group(enum.IntEnum):
    NONE = 0
    PLAYERS = 1
    WALLS = 2
    GUNS = 3
    HANDS = 4
    BOXES = 5
    BULLETS = 6


COLLIDES_WITH = {Group.NONE: [],
                 Group.PLAYERS: [Group.PLAYERS, Group.WALLS, Group.BULLETS],
                 Group.WALLS: [Group.PLAYERS, Group.WALLS, Group.GUNS, Group.BOXES, Group.BULLETS],
                 Group.GUNS: [Group.WALLS],
                 Group.HANDS: [Group.WALLS],
                 Group.BOXES: [Group. WALLS, Group.BOXES, Group.BULLETS],
                 Group.BULLETS: [Group.WALLS, Group.PLAYERS, Group.BOXES]}


class GameObject:
    def __init__(self, position, group=Group.NONE, image=None):
        super().__init__()
        self.position = np.array(position, dtype=float)
        self.collider = None
        self.group = group
        self.collision = True
        self.flipped = False
        self.health = 100
        self.destroyed = False
        self.angle = 0.0

        self.image = None
        self.image_path = ''
        self.size = 1.0
        self.update_image = False

    def damage(self, amount):
        if self.health > 0:
            self.health -= amount
        else:
            self.health = 0
            self.destroyed = True

    def flip_horizontally(self):
        self.collider.position[0] -= 2 * (self.collider.position - self.position)[0]

        self.flipped = not self.flipped
        self.update_image = True

    def set_position(self, position):
        delta_pos = position - self.position

        self.position += delta_pos
        self.collider.position += delta_pos

    def add_collider(self, collider):
        self.collider = collider
        collider.parent = self
        collider.position += self.position

    def draw(self, screen, camera, image_handler):
        if not self.image_path:
            self.debug_draw(screen, camera)
            return

        if not self.image or self.update_image:
            image = image_handler.images[self.image_path]

            scale = 1.05 * camera.zoom * self.size / 100

            if self.flipped:
                image = pygame.transform.flip(image, True, False)

            self.image = pygame.transform.rotozoom(image, np.degrees(self.angle), scale)

            self.update_image = False

        rect = self.image.get_rect()
        rect.center = camera.world_to_screen(self.position)

        screen.blit(self.image, rect)

    def debug_draw(self, screen, camera):
        self.collider.draw(screen, camera)


class PhysicsObject(GameObject):
    def __init__(self, position, velocity=(0, 0), group=Group.NONE):
        super().__init__(position, group)
        self.velocity = np.array(velocity, dtype=float)
        self.acceleration = np.zeros(2)

        self.angular_velocity = 0.0
        self.angular_acceleration = 0.0

        self.bounce = 0.5
        self.on_ground = False
        self.mass = 1.0
        self.inertia = 0.0
        self.gravity_scale = 1.0

    def set_position(self, position):
        super().set_position(position)
        self.velocity[:] = np.zeros(2)

    def rotate(self, delta_angle):
        self.angle += delta_angle

        self.collider.rotate(delta_angle)

    def update(self, gravity, time_step, colliders):
        if self.velocity[1] > 0:
            self.on_ground = False

        delta_pos = self.velocity * time_step + 0.5 * self.acceleration * time_step**2
        self.position += delta_pos
        acc_old = self.acceleration.copy()
        self.acceleration = self.gravity_scale * gravity

        delta_angle = self.angular_velocity * time_step + 0.5 * self.angular_acceleration * time_step**2
        self.angle += delta_angle
        ang_acc_old = float(self.angular_acceleration)
        self.angular_acceleration = 0.0

        self.collider.position += delta_pos

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
            self.velocity[0] = 0

    def draw(self, screen, camera, image_handler):
        if self.angular_velocity:
            image = image_handler.images[self.image_path]

            scale = 1.05 * camera.zoom * self.size / 100

            if self.flipped:
                image = pygame.transform.flip(image, True, False)

            self.image = pygame.transform.rotozoom(image, np.degrees(self.angle), scale)

        super().draw(screen, camera, image_handler)
