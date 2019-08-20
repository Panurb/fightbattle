import numpy as np
from numpy.linalg import norm
import enum

from collider import COLLISION_MATRIX


class Group(enum.IntEnum):
    NONE = 0
    PLAYERS = 1
    WALLS = 2
    GUNS = 3
    HAND = 4
    BOXES = 5


class GameObject:
    def __init__(self, position, group=Group.NONE):
        self.position = np.array(position, dtype=float)
        self.colliders = []
        self.group = group

    def flip_horizontally(self):
        for c in self.colliders:
            #c.flip_horizontally()
            c.position[0] -= 2 * (c.position - self.position)[0]

    def set_position(self, position):
        delta_pos = position - self.position

        self.position += delta_pos
        for c in self.colliders:
            c.position += delta_pos

    def add_collider(self, collider):
        self.colliders.append(collider)

    def draw(self, screen, camera):
        for collider in self.colliders:
            collider.draw(screen, camera)


class PhysicsObject(GameObject):
    def __init__(self, position, velocity=(0, 0), group=Group.NONE):
        super().__init__(position, group)
        self.velocity = np.array(velocity, dtype=float)
        self.acceleration = np.zeros(2)

        self.angle = 0.0
        self.angular_velocity = 0.0
        self.angular_acceleration = 0.0

        self.bounce = 0.5
        self.on_ground = False
        self.mass = 1.0
        self.inertia = 1.0
        self.gravity_scale = 1.0

    def draw(self, screen, camera):
        super().draw(screen, camera)

    def set_position(self, position):
        super().set_position(position)
        self.velocity[:] = np.zeros(2)

    def update(self, gravity, time_step, colliders):
        if self.velocity[1] > 0:
            self.on_ground = False

        delta_pos = self.velocity * time_step + 0.5 * self.acceleration * time_step**2
        self.position += delta_pos
        acc_old = self.acceleration.copy()
        self.acceleration[:] = self.gravity_scale * gravity

        delta_angle = self.angular_velocity * time_step + 0.5 * self.angular_acceleration * time_step**2
        self.angle += delta_angle
        ang_acc_old = float(self.angular_acceleration)
        self.angular_acceleration = 0.0

        for collider in self.colliders:
            impact = None

            collider.position += delta_pos
            collider.rotate(delta_angle)

            collider.update_collisions(colliders)

            left = None
            right = None

            for collision in collider.collisions:
                if not COLLISION_MATRIX[self.group][collision.collider.parent.group]:
                    continue

                if collision.overlap[1] > 0:
                    self.on_ground = True

                self.position += collision.overlap

                for c in self.colliders:
                    c.position += collision.overlap

                if self.bounce:
                    n = collision.overlap
                    impact = -5 * self.bounce * self.velocity.dot(n) * n / n.dot(n)
                    self.acceleration += impact
                    #self.velocity -= 2 * self.velocity.dot(n) * n / n.dot(n)
                    #self.velocity *= self.bounce
                else:
                    if not collision.overlap[0]:
                        self.velocity[1] = 0.0
                        self.acceleration[0] -= np.sign(self.velocity[0]) * collision.collider.friction
                    elif not collision.overlap[1]:
                        self.velocity[0] = 0.0

                for s in collision.supports:
                    if left is None or s[0] < left[0]:
                        left = s
                    if right is None or s[0] > right[0]:
                        right = s

            if self.inertia:
                r = None
                if left is not None and self.position[0] < left[0]:
                    r = self.position - left
                if right is not None and self.position[0] > right[0]:
                    r = self.position - right

                if r is not None:
                    # Steiner's theorem
                    inertia = self.inertia + self.mass * np.sum(r**2)

                    #self.angular_acceleration += np.cross(r, self.gravity_scale * gravity) / inertia
                    self.angular_acceleration += np.cross(-r, impact) / self.inertia

                    t = np.cross(r, np.array([0, 0, 1]))[:-1]
                    t /= norm(t)
                    self.acceleration += norm(r) * self.angular_acceleration * t

        self.velocity += 0.5 * (acc_old + self.acceleration) * time_step
        self.angular_velocity += 0.5 * (ang_acc_old + self.angular_acceleration) * time_step

        if abs(self.velocity[0]) < 0.05:
            self.velocity[0] = 0
