import numpy as np
from numpy.linalg import norm
import enum
import pygame
from numba import njit, prange

from helpers import norm2, perp, basis


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
    SWORDS = 9
    HITBOXES = 10
    PLATFORMS = 11


COLLIDES_WITH = {Group.NONE: [],
                 Group.PLAYERS: [Group.WALLS, Group.PLATFORMS],
                 Group.WALLS: [],
                 Group.GUNS: [Group.WALLS, Group.SHIELDS, Group.PLATFORMS],
                 Group.HANDS: [Group.WALLS],
                 Group.PROPS: [Group.WALLS, Group.PROPS, Group.SHIELDS, Group.PLATFORMS],
                 Group.BULLETS: [Group.WALLS, Group.SHIELDS],
                 Group.SHIELDS: [Group.WALLS, Group.PROPS, Group.SHIELDS],
                 Group.DEBRIS: [Group.WALLS, Group.PLATFORMS],
                 Group.SWORDS: [Group.WALLS, Group.SHIELDS, Group.SWORDS],
                 Group.HITBOXES: [],
                 Group.PLATFORMS: []}


@njit
def axis_half_width(w1, h1, u):
    return abs(np.dot(w1, u)) + abs(np.dot(h1, u))


@njit
def axis_overlap(r1, p1, r2, p2, u):
    overlap = 0.0
    r = np.dot(p1 - p2, u)
    o = r1 + r2 - abs(r)
    if o > 0.0:
        if r == 0.0:
            overlap = o
        else:
            overlap = np.sign(r) * o

    return overlap


@njit
def overlap_rectangle_rectangle(w1, h1, p1, w2, h2, p2):
    overlaps = np.zeros(4)

    axes = np.zeros((4, 2))
    axes[0, :] = w1 / norm(w1)
    axes[1, :] = h1 / norm(h1)
    axes[2, :] = w2 / norm(w2)
    axes[3, :] = h2 / norm(h2)

    for i in prange(4):
        u = axes[i, :]
        overlaps[i] = axis_overlap(axis_half_width(w1, h1, u), p1, axis_half_width(w2, h2, u), p2, u)
        if overlaps[i] == 0.0:
            return np.zeros(2)

    i = np.argmin(np.abs(overlaps))

    return overlaps[i] * axes[i, :]


@njit
def overlap_rectangle_circle(w1, h1, p1, r2, p2):
    overlaps = np.zeros(2)
    near_corner = True

    axes = np.zeros((2, 2))
    axes[0, :] = w1 / norm(w1)
    axes[1, :] = h1 / norm(h1)

    for i in prange(2):
        u = axes[i, :]
        overlaps[i] = axis_overlap(axis_half_width(w1, h1, u), p1, r2, p2, u)

        if overlaps[i] == 0.0:
            return np.zeros(2)

        if abs(overlaps[i]) >= r2:
            near_corner = False

    i = np.argmin(np.abs(overlaps))
    if not near_corner:
        return overlaps[i] * axes[i, :]

    corner = p1 - np.sign(overlaps[0]) * w1 - np.sign(overlaps[1]) * h1

    axis = corner - p2
    u = axis / norm(axis)

    overlap = axis_overlap(axis_half_width(w1, h1, u), p1, r2, p2, u)

    if 0 < abs(overlap) < abs(overlaps[i]):
        return overlap * u

    return np.zeros(2)


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

    def point_inside(self, point):
        pass


class Rectangle(Collider):
    def __init__(self, position, width, height, group=Group.NONE):
        super().__init__(position, group)
        self.half_width = np.array([0.5 * width, 0.0])
        self.half_height = np.array([0.0, 0.5 * height])

        self.radius = norm(self.half_width + self.half_height)

    def corners(self):
        ur = self.position + self.half_width + self.half_height
        ul = ur - 2 * self.half_width
        dl = ul - 2 * self.half_height
        dr = dl + 2 * self.half_width

        return [ur, ul, dl, dr]

    def overlap(self, other):
        dist = norm2(self.position - other.position)
        if dist > (self.radius + other.radius)**2:
            return np.zeros(2)

        if type(other) is Rectangle:
            return overlap_rectangle_rectangle(self.half_width, self.half_height, self.position,
                                               other.half_width, other.half_height, other.position)
        elif type(other) is Circle:
            return overlap_rectangle_circle(self.half_width, self.half_height, self.position,
                                            other.radius, other.position)

        return np.zeros(2)

    def point_inside(self, point):
        # TODO
        if -self.half_width[0] < point[0] - self.position[0] < self.half_width[0]:
            if -self.half_height[1] < point[1] - self.position[1] < self.half_height[1]:
                return True

        return False

    def rotate(self, angle):
        r = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        self.half_width = np.matmul(r, self.half_width)
        self.half_height = np.matmul(r, self.half_height)

    def rotate_90(self):
        self.half_width = perp(self.half_width)
        self.half_height = perp(self.half_height)

    def draw(self, screen, camera, image_handler):
        points = [camera.world_to_screen(p) for p in self.corners()]

        pygame.draw.polygon(screen, image_handler.debug_color, points, 1)


class Circle(Collider):
    def __init__(self, position, radius, group=Group.NONE):
        super().__init__(position, group)
        self.radius = radius
        self.half_height = radius * basis(1)

    def overlap(self, other):
        overlap = np.zeros(2)

        dist = norm2(self.position - other.position)
        if dist > (self.radius + other.radius)**2:
            return overlap

        if type(other) is Circle:
            if dist == 0.0:
                overlap = (self.radius + other.radius) * basis(1)
            else:
                dist = np.sqrt(dist)
                unit = (self.position - other.position) / dist
                overlap = (self.radius + other.radius - dist) * unit
        elif type(other) is Rectangle:
            overlap = -other.overlap(self)

        return overlap

    def point_inside(self, point):
        return norm2(self.position - point) <= self.radius**2

    def draw(self, screen, camera, image_handler):
        center = camera.world_to_screen(self.position)
        pygame.draw.circle(screen, image_handler.debug_color, center, int(self.radius * camera.zoom), 1)


class Capsule(Collider):
    def __init__(self, position, group=Group.NONE):
        super().__init__(position, group)
