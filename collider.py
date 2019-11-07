import numpy as np
from numpy.linalg import norm
import enum
import pygame

from helpers import norm2, perp


class Group(enum.IntEnum):
    NONE = 0
    PLAYERS = 1
    WALLS = 2
    GUNS = 3
    HANDS = 4
    PROPS = 5
    BULLETS = 6
    SHIELDS = 7
    DEBRIS = 8


COLLIDES_WITH = {Group.NONE: [],
                 Group.PLAYERS: [Group.WALLS],
                 Group.WALLS: [],
                 Group.GUNS: [Group.WALLS],
                 Group.HANDS: [Group.WALLS],
                 Group.PROPS: [Group.WALLS, Group.PROPS, Group.BULLETS, Group.SHIELDS],
                 Group.BULLETS: [Group.WALLS, Group.PLAYERS, Group.PROPS, Group.SHIELDS],
                 Group.SHIELDS: [Group.WALLS, Group.PROPS],
                 Group.DEBRIS: [Group.WALLS]}


class Type(enum.Enum):
    RECTANGLE = 1
    CIRCLE = 2


class Collision:
    def __init__(self, collider, overlap):
        self.collider = collider
        self.overlap = overlap


class Collider:
    def __init__(self, position, group=Group.NONE):
        self.parent = None
        self.position = np.array(position, dtype=float)
        self.friction = 0.5
        self.type = None
        self.collisions = []
        self.group = group

    def update_collisions(self, colliders, groups=None):
        self.collisions.clear()

        if not groups:
            groups = COLLIDES_WITH[self.group]

        for g in groups:
            for c in colliders[g]:
                if c is self:
                    continue

                if c.parent is self.parent:
                    continue

                overlap = self.overlap(c)
                if overlap.any():
                    self.collisions.append(Collision(c, overlap))

    def rotate(self, angle):
        pass

    def draw(self, screen, camera, image_handler):
        return

    def radius(self):
        pass

    def overlap(self, other):
        pass


class Rectangle(Collider):
    def __init__(self, position, width, height, group=Group.NONE):
        super().__init__(position, group)
        self.half_width = np.array([0.5 * width, 0.0])
        self.half_height = np.array([0.0, 0.5 * height])
        self.type = Type.RECTANGLE

        self.radius = norm(self.half_width + self.half_height)

    def corners(self):
        return [self.position + self.half_width + self.half_height,
                self.position - self.half_width + self.half_height,
                self.position - self.half_width - self.half_height,
                self.position + self.half_width - self.half_height]

    def axis_half_width(self, axis):
        return abs(np.dot(self.half_width, axis)) + abs(np.dot(self.half_height, axis))

    def axis_overlap(self, other, axis):
        overlap = 0

        r = np.dot(self.position - other.position, axis)

        o = self.axis_half_width(axis) + other.axis_half_width(axis) - abs(r)

        if o > 0:
            if r == 0:
                overlap = o
            else:
                overlap = np.sign(r) * o

        return overlap

    def overlap(self, other):
        overlap = np.zeros(2)

        dist = norm2(self.position - other.position)
        if dist > (self.radius + other.radius)**2:
            return overlap

        if other.type is Type.RECTANGLE:
            axes = [self.half_width, self.half_height]
            if self.parent.angle != other.parent.angle:
                axes += [other.half_width, other.half_height]

            min_axis = None
            min_overlap = other.radius + self.radius

            for axis in axes:
                u = axis / norm(axis)
                overlap = self.axis_overlap(other, u)

                if abs(overlap) <= 0:
                    return np.zeros(2)
                elif abs(overlap) < abs(min_overlap):
                    min_overlap = overlap
                    min_axis = u

            overlap = min_overlap * min_axis

        elif other.type is Type.CIRCLE:
            min_axis = None
            min_overlap = other.radius + self.radius
            overlaps = []
            near_corner = True

            for axis in [self.half_width, self.half_height]:
                u = axis / norm(axis)
                overlap = self.axis_overlap(other, u)
                o = abs(overlap)

                if o >= other.radius:
                    near_corner = False
                else:
                    overlaps.append(overlap)

                if o <= 0:
                    return np.zeros(2)
                elif o < abs(min_overlap):
                    min_overlap = overlap
                    min_axis = u

            if not near_corner:
                return min_overlap * min_axis

            corner = self.position - np.sign(overlaps[0]) * self.half_width - np.sign(overlaps[1]) * self.half_height

            axis = corner - other.position
            axis /= norm(axis)

            overlap = self.axis_overlap(other, axis)

            if 0 < abs(overlap) < abs(min_overlap):
                min_overlap = overlap
                min_axis = axis
                overlaps.append(overlap)
            else:
                return np.zeros(2)

            overlap = min_overlap * min_axis

        return overlap

    def rotate(self, angle):
        r = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        self.half_width = np.matmul(r, self.half_width)
        self.half_height = np.matmul(r, self.half_height)

    def rotate_90(self):
        self.half_width = perp(self.half_width)
        self.half_height = perp(self.half_height)

    def draw(self, screen, camera, image_handler):
        points = []
        for c in self.corners():
            points.append(camera.world_to_screen(c))

        pygame.draw.polygon(screen, image_handler.debug_color, points, 1)


class Circle(Collider):
    def __init__(self, position, radius, group=Group.NONE):
        super().__init__(position, group)
        self.radius = radius
        self.type = Type.CIRCLE

    def axis_half_width(self, axis):
        return self.radius

    def overlap(self, other):
        overlap = np.zeros(2)

        dist = norm2(self.position - other.position)
        if dist > (self.radius + other.radius)**2:
            return overlap

        if other.type is Type.CIRCLE:
            dist = np.sqrt(dist)
            unit = (self.position - other.position) / dist
            overlap = (self.radius + other.radius - dist) * unit
        elif other.type is Type.RECTANGLE:
            overlap = -other.overlap(self)

        return overlap

    def draw(self, screen, camera, image_handler):
        center = camera.world_to_screen(self.position)
        pygame.draw.circle(screen, image_handler.debug_color, center, int(self.radius * camera.zoom), 1)


class Capsule(Collider):
    def __init__(self, position, group=Group.NONE):
        super().__init__(position, group)
