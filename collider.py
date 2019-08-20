import numpy as np
from numpy.linalg import norm
import enum
import pygame
import itertools


class Type(enum.Enum):
    RECTANGLE = 1
    CIRCLE = 2


COLLISION_MATRIX = [[False, False, False, False, False, False],
                    [False, True, True, False, False, False],
                    [False, True, True, True, False, True],
                    [False, False, True, False, False, True],
                    [False, False, False, False, False, False],
                    [False, False, True, True, False, True]]


class Collision:
    def __init__(self, collider, overlap, supports):
        self.collider = collider
        self.overlap = overlap
        self.supports = supports


class Collider:
    id_iter = itertools.count()

    def __init__(self, parent, position):
        self.id = next(self.id_iter)
        self.parent = parent
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
    def __init__(self, parent, position, width, height):
        super().__init__(parent, position)
        self.half_width = np.array([0.5 * width, 0.0])
        self.half_height = np.array([0.0, 0.5 * height])
        self.width = width
        self.height = height
        self.radius = norm(self.half_width + self.half_height)
        self.type = Type.RECTANGLE

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

        w = 2 * self.half_width / self.width
        h = 2 * self.half_height / self.height

        p_w = np.dot(p, w)
        p_h = np.dot(p, h)

        o_w = 0.5 * self.width - abs(p_w)
        o_h = 0.5 * self.height - abs(p_h)

        if o_w > 0 and o_h > 0:
            if o_w < o_h:
                overlap = -np.sign(p_w) * o_w * w
            else:
                overlap = -np.sign(p_h) * o_h * h

        return overlap

    def overlap(self, other):
        overlap = np.zeros(2)
        supports = []

        if norm(self.position - other.position) > self.radius + other.radius:
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
    def __init__(self, parent, position, radius):
        super().__init__(parent, position)
        self.radius = radius
        self.type = Type.CIRCLE

    def right(self):
        return self.position[0] + self.radius

    def left(self):
        return self.position[0] - self.radius

    def top(self):
        return self.position[1] + self.radius

    def bottom(self):
        return self.position[1] - self.radius

    def overlap(self, other):
        overlap = np.zeros(2)
        supports = []

        dist = norm(self.position - other.position)
        if dist > self.radius + other.radius:
            return overlap, supports

        if dist == 0:
            overlap = 2 * self.radius * np.array([0, 1])
            supports.append(self.position + 0.5 * overlap)
            return overlap, supports

        if other.type is Type.CIRCLE:
            unit = (self.position - other.position) / dist
            overlap = (self.radius + other.radius - dist) * unit
            supports.append(other.position + other.radius * unit)
        elif other.type is Type.RECTANGLE:
            overlap = np.zeros(2)

            r_w = 2 * other.half_width / other.width * self.radius
            r_h = 2 * other.half_height / other.height * self.radius

            for r in [r_w, -r_w, r_h, -r_h]:
                p = self.position + r
                o = other.point_overlap(p)
                if o.any():
                    overlap = -o
                    break
            else:
                for corner in other.corners():
                    dist = norm(self.position - corner)
                    if dist <= self.radius:
                        unit = (self.position - corner) / dist
                        overlap = (self.radius - dist) * unit
                        supports.append(self.position - self.radius * unit)

        return overlap, supports


    def draw(self, screen, camera):
        super().draw(screen, camera)

        color = (255, 0, 255)
        center = camera.world_to_screen(self.position)
        pygame.draw.circle(screen, color, center, int(self.radius * camera.zoom), 1)
