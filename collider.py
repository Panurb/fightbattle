import numpy as np
from numpy.linalg import norm
import enum
from numba import njit, prange

from helpers import norm2, basis

GRID_SIZE = 1


class Group(enum.IntEnum):
    NONE = 0
    PLAYERS = 1
    WALLS = 2
    WEAPONS = 3
    HANDS = 4
    PROPS = 5
    BULLETS = 6
    SHIELDS = 7
    DEBRIS = 8
    SWORDS = 9
    HITBOXES = 10
    PLATFORMS = 11
    GOALS = 12
    THROWN = 13


COLLIDES_WITH = {Group.NONE: set(),
                 Group.PLAYERS: {Group.WALLS, Group.PLATFORMS, Group.PROPS},
                 Group.WALLS: set(),
                 Group.WEAPONS: {Group.WALLS, Group.PLATFORMS},
                 Group.HANDS: {Group.WALLS},
                 Group.PROPS: {Group.WALLS, Group.PROPS, Group.PLATFORMS},
                 Group.BULLETS: {Group.SHIELDS},
                 Group.SHIELDS: {Group.WALLS, Group.PLATFORMS},
                 Group.DEBRIS: {Group.WALLS, Group.PLATFORMS},
                 Group.HITBOXES: set(),
                 Group.PLATFORMS: set(),
                 Group.GOALS: set(),
                 Group.THROWN: {Group.WALLS, Group.PLATFORMS, Group.PLAYERS, Group.PROPS, Group.WEAPONS}}


@njit(cache=True)
def axis_half_width(w, h, u):
    return abs(np.dot(w, u)) + abs(np.dot(h, u))


@njit(cache=True)
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


@njit(cache=True)
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


@njit(cache=True)
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
        self.collisions = []
        self.group = group
        self.occupied_squares = []
        self.half_width = np.zeros(2)
        self.half_height = np.zeros(2)
        self.vertex_list = None
        self.vertex_lists = 100 * [None]

    def set_position(self, position):
        self.position[:] = position

    def axis_half_width(self, axis):
        return axis_half_width(self.half_width, self.half_height, axis)

    def update_collisions(self, colliders, groups=None):
        self.collisions.clear()

        cs = set()
        for i, j in self.occupied_squares:
            for c in colliders[i][j]:
                if not c.parent:
                    continue

                if c.parent is self.parent:
                    continue

                if not c.parent.collision_enabled:
                    continue

                if groups:
                    if c.group not in groups:
                        continue
                elif c.group not in COLLIDES_WITH[self.group]:
                    continue

                cs.add(c)

        for c in cs:
            overlap = self.overlap(c)
            if overlap.any():
                self.collisions.append(Collision(c, overlap))

    def rotate(self, angle):
        pass

    def draw(self, batch, camera, image_handler):
        k = 0
        for i, j in self.occupied_squares:
            self.vertex_lists[k] = camera.draw_rectangle(np.array([GRID_SIZE * (i + 0.5), GRID_SIZE * (j + 1.5)]), GRID_SIZE,
                                                         GRID_SIZE, batch=batch, layer=8, linewidth=1/camera.zoom,
                                                         vertex_list=self.vertex_lists[k])
            k += 1

        while k < len(self.vertex_lists):
            if self.vertex_lists[k]:
                self.vertex_lists[k].delete()
            self.vertex_lists[k] = None
            k += 1

    def overlap(self, other):
        pass

    def point_inside(self, point):
        pass

    def update_occupied_squares(self, colliders):
        self.clear_occupied_squares(colliders)

        x, y = self.position
        w = axis_half_width(self.half_width, self.half_height, basis(0))
        h = axis_half_width(self.half_width, self.half_height, basis(1))

        for i in range(max(int((x - w) / GRID_SIZE) - 1, 0), min(int((x + w) / GRID_SIZE) + 1, len(colliders))):
            for j in range(max(int((y - h) / GRID_SIZE) - 1, 0), min(int((y + h) / GRID_SIZE) + 1, len(colliders[i]))):
                self.occupied_squares.append((i, j))

        for i, j in self.occupied_squares:
            colliders[i][j].append(self)

    def clear_occupied_squares(self, colliders):
        for i, j in self.occupied_squares:
            colliders[i][j].remove(self)
        self.occupied_squares.clear()


class ColliderGroup:
    def __init__(self, position, group=Group.NONE):
        self.parent = None
        self.position = np.array(position, dtype=float)
        self.friction = 0.5
        self.type = None
        self.collisions = []
        self.group = group
        self.occupied_squares = []

        self.colliders = []
        self.radius = 0.0
        self.half_width = 0.5 * basis(0)
        self.half_height = 0.5 * basis(1)

    def set_position(self, position):
        delta_pos = position - self.position
        self.position[:] = position
        for c in self.colliders:
            c.set_position(c.position + delta_pos)

    def add_collider(self, collider):
        self.colliders.append(collider)
        collider.parent = self.parent
        self.radius = max(self.radius, norm(collider.position + collider.half_width + collider.half_height))
        collider.position += self.position

    def update_collisions(self, colliders, groups=None):
        self.collisions.clear()

        for c in self.colliders:
            c.update_collisions(colliders, groups)
            self.collisions += c.collisions

    def rotate(self, angle):
        for c in self.colliders:
            c.rotate(angle)

    def draw(self, screen, camera, image_handler):
        for c in self.colliders:
            c.draw(screen, camera, image_handler)

    def overlap(self, other):
        return sum(c.overlap(other) for c in self.colliders)

    def point_inside(self, point):
        r = point - self.position
        return norm(r) < self.radius

    def update_occupied_squares(self, colliders):
        for c in self.colliders:
            c.update_occupied_squares(colliders)

    def clear_occupied_squares(self, colliders):
        for c in self.colliders:
            c.clear_occupied_squares(colliders)


class Rectangle(Collider):
    def __init__(self, position, width, height, group=Group.NONE):
        super().__init__(position, group)
        self.half_width = np.array([0.5 * width, 0.0])
        self.half_height = np.array([0.0, 0.5 * height])
        self.width = width
        self.height = height
        self.angle = 0.0
        self.ratio = self.width / self.height

    def corners(self):
        ur = self.position + self.half_width + self.half_height
        ul = ur - 2 * self.half_width
        dl = ul - 2 * self.half_height
        dr = dl + 2 * self.half_width

        return [ur, ul, dl, dr]

    def overlap(self, other):
        if type(other) is Rectangle:
            return overlap_rectangle_rectangle(self.half_width, self.half_height, self.position,
                                               other.half_width, other.half_height, other.position)
        elif type(other) is Circle:
            return overlap_rectangle_circle(self.half_width, self.half_height, self.position,
                                            other.radius, other.position)

        return np.zeros(2)

    def point_inside(self, point):
        m = 2 * np.array([self.half_width, self.half_height]).T

        r = point - self.position + self.half_width + self.half_height
        p = np.linalg.solve(m, r)

        if np.all(0 < p) and np.all(p < 1):
            return True

        return False

    def rotate(self, angle):
        r = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        self.half_width = np.matmul(r, self.half_width)
        self.half_height = np.matmul(r, self.half_height)
        self.angle += angle

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        self.vertex_list = camera.draw_line(self.corners() + [self.corners()[0]], 1 / camera.zoom, image_handler.debug_color,
                                            batch=batch, layer=8, vertex_list=self.vertex_list)

    def rest_angle(self):
        if self.ratio > 1.5:
            return np.round(self.angle / np.pi) * np.pi
        elif self.ratio < 0.5:
            return (np.round((self.angle + 0.5 * np.pi) / np.pi) - 0.5) * np.pi
        else:
            return np.round(self.angle / (0.5 * np.pi)) * 0.5 * np.pi


class Circle(Collider):
    def __init__(self, position, radius, group=Group.NONE):
        super().__init__(position, group)
        self.radius = radius
        self.half_width = radius * basis(0)
        self.half_height = radius * basis(1)

    def overlap(self, other):
        overlap = np.zeros(2)

        if type(other) is Circle:
            dist = norm2(self.position - other.position)
            if dist > (self.radius + other.radius) ** 2:
                return overlap

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

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        self.vertex_list = camera.draw_circle(self.position, self.radius, image_handler.debug_color,
                                              linewidth=1 / camera.zoom, batch=batch, layer=8,
                                              vertex_list=self.vertex_list)
