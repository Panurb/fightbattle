import numpy as np
from numpy.linalg import norm
import enum
import pygame
import itertools

from gameobject import COLLISION_MATRIX, Group


class Type(enum.Enum):
    RECTANGLE = 1
    CIRCLE = 2


class Collision:
    def __init__(self, collider, overlap, supports):
        self.collider = collider
        self.overlap = overlap
        self.supports = supports


class Collider:
    id_iter = itertools.count()

    def __init__(self, position):
        self.id = next(self.id_iter)
        self.parent = None
        self.position = np.array(position, dtype=float)
        self.friction = 0.5
        self.type = None
        self.collisions = []

    def update_collisions(self, colliders):
        self.collisions.clear()

        for c in colliders:
            if c is self:
                continue

            if c.parent is self.parent:
                continue

            if not COLLISION_MATRIX[self.parent.group][c.parent.group]:
                continue

            overlap, supports = self.overlap(c)
            if overlap.any():
                self.collisions.append(Collision(c, overlap, supports))

    def rotate(self, angle):
        pass

    def draw(self, screen, camera):
        for c in self.collisions:
            for s in c.supports:
                pygame.draw.circle(screen, (255, 0, 255), camera.world_to_screen(s), 4)

    def overlap(self, other):
        pass


class Rectangle(Collider):
    def __init__(self, position, width, height):
        super().__init__(position)
        self.half_width = np.array([0.5 * width, 0.0])
        self.half_height = np.array([0.0, 0.5 * height])
        self.type = Type.RECTANGLE

    def radius(self):
        return norm(self.half_width + self.half_height)

    def transformation_matrix(self):
        return np.inv(np.array([2 * self.half_width, 2 * self.half_height]).T)

    def right(self):
        return (self.position + self.half_width)[0]

    def left(self):
        return (self.position - self.half_width)[0]

    def top(self):
        return (self.position + self.half_height)[1]

    def bottom(self):
        return (self.position - self.half_height)[1]

    def topleft(self):
        return self.position - self.half_width + self.half_height

    def topright(self):
        return self.position + self.half_width + self.half_height

    def bottomleft(self):
        return self.position - self.half_width - self.half_height

    def bottomright(self):
        return self.position + self.half_width - self.half_height

    def corners(self):
        return self.topright(), self.topleft(), self.bottomleft(), self.bottomright()

    def point_overlap(self, point):
        overlap = np.zeros(2)

        p = point - self.position

        hw = norm(self.half_width)
        hh = norm(self.half_height)

        w = self.half_width / hw
        h = self.half_height / hh

        p_w = np.dot(p, w)
        p_h = np.dot(p, h)

        o_w = hw - abs(p_w)
        o_h = hh - abs(p_h)

        if o_w >= 0 and o_h >= 0:
            if o_w != 0 and o_w < o_h:
                overlap = -np.sign(p_w) * o_w * w
            elif o_h != 0:
                overlap = -np.sign(p_h) * o_h * h

        return overlap

    def overlap(self, other):
        overlap = np.zeros(2)
        supports = []

        dist = norm(self.position - other.position)
        if dist > self.radius() + other.radius():
            return overlap, supports

        if dist == 0:
            overlap = 2 * self.half_height
            supports.append(self.position + self.half_height)
            return overlap, supports

        if other.type is Type.RECTANGLE:
            for c in other.corners():
                o = self.point_overlap(c)
                if o.any():
                    supports.append(c)
                    if norm(o) > norm(overlap):
                        overlap = o
            for c in self.corners():
                o = -other.point_overlap(c)
                if o.any():
                    supports.append(c + o)
                    if norm(o) > norm(overlap):
                        overlap = o
        elif other.type is Type.CIRCLE:
            overlap, supports = other.overlap(self)
            overlap *= -1

        return overlap, supports

    def rotate(self, angle):
        r = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        self.half_width = np.matmul(r, self.half_width)
        self.half_height = np.matmul(r, self.half_height)

    def draw(self, screen, camera):
        super().draw(screen, camera)

        color = (255, 0, 255)
        points = []
        for c in self.corners():
            points.append(camera.world_to_screen(c))

        pygame.draw.polygon(screen, color, points, 1)


class Circle(Collider):
    def __init__(self, position, radius):
        super().__init__(position)
        self._radius = radius
        self.type = Type.CIRCLE

    def radius(self):
        return self._radius

    def right(self):
        return self.position[0] + self._radius

    def left(self):
        return self.position[0] - self._radius

    def top(self):
        return self.position[1] + self._radius

    def bottom(self):
        return self.position[1] - self._radius

    def overlap(self, other):
        overlap = np.zeros(2)
        supports = []

        dist = norm(self.position - other.position)
        if dist > self._radius + other.radius():
            return overlap, supports

        if dist == 0:
            overlap = 2 * self._radius * np.array([0, 1])
            supports.append(self.position + 0.5 * overlap)
            return overlap, supports

        if other.type is Type.CIRCLE:
            unit = (self.position - other.position) / dist
            overlap = (self._radius + other.radius() - dist) * unit
            supports.append(other.position + other.radius() * unit)
        elif other.type is Type.RECTANGLE:
            overlap = np.zeros(2)

            r_w = other.half_width / norm(other.half_width) * self._radius
            r_h = other.half_height / norm(other.half_height) * self._radius

            for r in [r_w, -r_w, r_h, -r_h]:
                p = self.position + r
                o = other.point_overlap(p)
                if o.any():
                    overlap = -o
                    break
            else:
                for corner in other.corners():
                    dist = norm(self.position - corner)
                    if dist <= self._radius:
                        unit = (self.position - corner) / dist
                        overlap = (self._radius - dist) * unit
                        supports.append(self.position - self._radius * unit)

        return overlap, supports


    def draw(self, screen, camera):
        super().draw(screen, camera)

        color = (255, 0, 255)
        center = camera.world_to_screen(self.position)
        pygame.draw.circle(screen, color, center, int(self._radius * camera.zoom), 1)
