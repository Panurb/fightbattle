import numpy as np
from numpy.linalg import norm
import enum
import pygame


def projection(v, a, b):
    return np.array([np.dot(v, a) / norm(a), np.dot(v, b) / norm(b)])


class Type(enum.Enum):
    RECTANGLE = 1
    CIRCLE = 2


class Collision:
    def __init__(self, collider, overlap, supports):
        self.collider = collider
        self.overlap = overlap
        self.supports = supports


class Collider:
    def __init__(self, position):
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

            overlap, supports = self.overlap(c)
            if overlap.any():
                self.collisions.append(Collision(c, overlap, supports))

    def rotate(self, angle):
        pass

    def draw(self, screen, camera):
        for c in self.collisions:
            for s in c.supports:
                pygame.draw.circle(screen, (255, 0, 255), camera.world_to_screen(s), 4)

    def radius(self):
        pass

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

    def corners(self):
        return [self.position + self.half_width + self.half_height,
                self.position - self.half_width + self.half_height,
                self.position - self.half_width - self.half_height,
                self.position + self.half_width - self.half_height]

    def axis_half_width(self, axis):
        return abs(np.dot(self.half_width, axis)) + abs(np.dot(self.half_height, axis))

    def overlap(self, other):
        overlap = np.zeros(2)
        supports = []

        dist = np.sum((self.position - other.position)**2)
        if dist > (self.radius() + other.radius())**2:
            return overlap, supports

        if other.type is Type.RECTANGLE:
            axes = [self.half_width, self.half_height]
            if self.parent.angle != other.parent.angle:
                axes += [other.half_width, other.half_height]

            min_axis = None
            min_overlap = other.radius() + self.radius()

            for axis in axes:
                x = norm(axis)
                u = axis / x

                r = np.dot(self.position - other.position, u)

                o = self.axis_half_width(u) + other.axis_half_width(u) - abs(r)

                if o > 0:
                    if r == 0:
                        overlap = o
                    else:
                        overlap = np.sign(r) * o

                    if abs(overlap) < abs(min_overlap):
                        min_overlap = overlap
                        min_axis = u
                else:
                    return np.zeros(2), []

            overlap = min_overlap * min_axis

        elif other.type is Type.CIRCLE:
            axes = [self.half_width, self.half_height]

            # TODO: figure out closest corner
            for c in self.corners():
                axes.append(c - other.position)

            min_axis = None
            min_overlap = other.radius() + self.radius()

            for axis in axes:
                x = norm(axis)
                u = axis / x

                r = np.dot(self.position - other.position, u)

                o = self.axis_half_width(u) + other.axis_half_width(u) - abs(r)

                if o > 0:
                    if r == 0:
                        overlap = o
                    else:
                        overlap = np.sign(r) * o

                    if abs(overlap) < abs(min_overlap):
                        min_overlap = overlap
                        min_axis = u
                else:
                    return np.zeros(2), []

            overlap = min_overlap * min_axis

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

    def axis_half_width(self, axis):
        return self.radius()

    def overlap(self, other):
        overlap = np.zeros(2)
        supports = []

        dist = np.sum((self.position - other.position)**2)
        if dist > (self._radius + other.radius())**2:
            return overlap, supports

        if other.type is Type.CIRCLE:
            dist = np.sqrt(dist)
            unit = (self.position - other.position) / dist
            overlap = (self._radius + other.radius() - dist) * unit
        elif other.type is Type.RECTANGLE:
            overlap, supports = other.overlap(self)
            overlap *= -1

        return overlap, supports

    def draw(self, screen, camera):
        super().draw(screen, camera)

        color = (255, 0, 255)
        center = camera.world_to_screen(self.position)
        pygame.draw.circle(screen, color, center, int(self._radius * camera.zoom), 1)


class Capsule(Collider):
    def __init__(self, position):
        super().__init__(position)
