import numpy as np
from numpy.linalg import norm
import enum
import pygame
from numba import njit, prange

from helpers import norm2, perp, basis


GRID_SIZE = 1


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
    GOALS = 12


COLLIDES_WITH = {Group.NONE: [],
                 Group.PLAYERS: [Group.WALLS, Group.PLATFORMS],
                 Group.WALLS: [],
                 Group.GUNS: [Group.WALLS, Group.SHIELDS, Group.PLATFORMS],
                 Group.HANDS: [Group.WALLS],
                 Group.PROPS: [Group.WALLS, Group.PROPS, Group.PLATFORMS],
                 Group.BULLETS: [Group.WALLS, Group.SHIELDS],
                 Group.SHIELDS: [Group.WALLS, Group.SHIELDS, Group.PLATFORMS],
                 Group.DEBRIS: [Group.WALLS, Group.PLATFORMS],
                 Group.SWORDS: [Group.WALLS, Group.SHIELDS, Group.PLATFORMS],
                 Group.HITBOXES: [],
                 Group.PLATFORMS: [],
                 Group.GOALS: []}

COLLISION_MATRIX = [[(j in gs) for j in COLLIDES_WITH.keys()] for i, gs in COLLIDES_WITH.items()]


#@njit
def axis_half_width(w, h, u):
    return abs(np.dot(w, u)) + abs(np.dot(h, u))


#@njit
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


#@njit
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


#@njit
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

    def set_position(self, position):
        self.position[:] = position

    def update_collisions(self, colliders, groups=None):
        self.collisions.clear()

        cs = set()
        for i, j in self.occupied_squares:
            for c in colliders[i][j]:
                if c.parent is self.parent:
                    continue

                if groups:
                    if c.group not in groups:
                        continue
                elif not COLLISION_MATRIX[self.group][c.group]:
                    continue

                cs.add(c)

        for c in cs:
            overlap = self.overlap(c)
            if overlap.any():
                self.collisions.append(Collision(c, overlap))

    def rotate(self, angle):
        pass

    def draw(self, screen, camera, image_handler):
        for i, j in self.occupied_squares:
            x, y = camera.world_to_screen(np.array([GRID_SIZE * i, GRID_SIZE * (j + 1)]))
            rect = pygame.rect.Rect(x, y, GRID_SIZE * camera.zoom, GRID_SIZE * camera.zoom)
            pygame.draw.rect(screen, pygame.Color('white'), rect, 1)

    def overlap(self, other):
        pass

    def point_inside(self, point):
        pass

    def update_occupied_squares(self, colliders):
        pass

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

    def set_position(self, position):
        delta_pos = position - self.position
        self.position[:] = position
        for c in self.colliders:
            c.set_position(c.position + delta_pos)

    def add_collider(self, collider):
        self.colliders.append(collider)
        collider.parent = self.parent
        # FIXME: why half?
        collider.position += 0.5 * self.position

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
        for c in self.colliders:
            if c.point_inside(point):
                return True

        return False

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
        super().draw(screen, camera, image_handler)

        points = [camera.world_to_screen(p) for p in self.corners()]

        pygame.draw.polygon(screen, image_handler.debug_color, points, 1)

    def update_occupied_squares(self, colliders):
        for i, j in self.occupied_squares:
            colliders[i][j].remove(self)

        pos = self.position

        half_width = axis_half_width(self.half_width, self.half_height, basis(0))
        half_height = axis_half_width(self.half_width, self.half_height, basis(1))

        self.occupied_squares.clear()

        for i in range(int((pos[0] - half_width) / GRID_SIZE), int((pos[0] + half_width) / GRID_SIZE) + 1):
            for j in range(int((pos[1] - half_height) / GRID_SIZE), int((pos[1] + half_height) / GRID_SIZE) + 1):
                self.occupied_squares.append((i, j))

        for i, j in self.occupied_squares:
            colliders[i][j].append(self)


class Circle(Collider):
    def __init__(self, position, radius, group=Group.NONE):
        super().__init__(position, group)
        self.radius = radius
        self.half_height = radius * basis(1)
        self.half_width = radius * basis(0)

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

    def draw(self, screen, camera, image_handler):
        super().draw(screen, camera, image_handler)
        center = camera.world_to_screen(self.position)
        pygame.draw.circle(screen, image_handler.debug_color, center, int(self.radius * camera.zoom), 1)

    def update_occupied_squares(self, colliders):
        for i, j in self.occupied_squares:
            colliders[i][j].remove(self)

        pos = self.position

        squares = []

        for i in range(int(pos[0] - 0.5 * self.radius), int(pos[0] + 0.5 * self.radius + 1)):
            for j in range(int(pos[1] - 0.5 * self.radius), int(pos[1] + 0.5 * self.radius + 1)):
                squares.append((i, j))

        r = 0.5 * self.radius

        for i in range(int((pos[0] - r) / GRID_SIZE), int((pos[0] + r) / GRID_SIZE) + 1):
            for j in range(int((pos[1] - r) / GRID_SIZE), int((pos[1] + r) / GRID_SIZE) + 1):
                squares.append((i, j))

        self.occupied_squares = squares

        for i, j in self.occupied_squares:
            colliders[i][j].append(self)
