import numpy as np
import enum
import pygame


class Type(enum.Enum):
    RECTANGLE = 1
    CIRCLE = 2


class Group(enum.IntEnum):
    NONE = 0
    PLAYERS = 1
    WALLS = 2
    GUNS = 3
    HAND = 4
    BOXES = 5


COLLISION_MATRIX = [[False, False, False, False, False, False],
                    [False, True, True, False, False, True],
                    [False, True, True, True, False, True],
                    [False, False, True, False, False, True],
                    [False, False, False, False, False, False],
                    [False, True, True, True, False, True]]


class Collision:
    def __init__(self, collider, overlap, supports):
        self.collider = collider
        self.overlap = overlap
        self.supports = supports


class Collider:
    def __init__(self, parent, position, group=Group.WALLS):
        self.parent = parent
        self.position = np.array(position, dtype=float)
        self.group = group
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

            if not COLLISION_MATRIX[self.group][c.group]:
                continue

            overlap, supports = self.overlap(c)
            if overlap.any():
                self.collisions.append(Collision(c, overlap, supports))

    def draw(self, screen, camera):
        for c in self.collisions:
            for s in c.supports:
                pygame.draw.circle(screen, (255, 0, 255), camera.world_to_screen(s), 4)

    def overlap(self, other):
        pass


class Rectangle(Collider):
    def __init__(self, parent, position, width, height, group=Group.WALLS):
        super().__init__(parent, position, group)
        self.half_width = np.array([0.5 * width, 0.0])
        self.half_height = np.array([0.0, 0.5 * height])
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

    def overlap(self, other):
        overlap = np.zeros(2)
        supports = []

        if other.type is Type.RECTANGLE:
            #m = self.transformation_matrix()
            #pos = np.matmul(m, other.position)

            #for c in other.corners:
            #    c = np.matmul(m, c)

            if other.left() < self.right() and self.left() < other.right():
                if other.bottom() < self.top() and self.bottom() < other.top():
                    if self.position[0] > other.position[0]:
                        overlap[0] = other.right() - self.left()
                    else:
                        overlap[0] = other.left() - self.right()

                    if self.position[1] > other.position[1]:
                        overlap[1] = other.top() - self.bottom()

                        if self.right() < other.right():
                            supports.append(self.bottomright())
                        if self.left() > other.left():
                            supports.append(self.bottomleft())
                        if self.right() > other.right():
                            supports.append(other.topright())
                        if self.left() < other.left():
                            supports.append(other.topleft())
                    else:
                        overlap[1] = other.bottom() - self.top()

                    i = np.argmax(np.abs(overlap))
                    overlap[i] = 0.0
        elif other.type is Type.CIRCLE:
            overlap, supports = other.overlap(self)
            overlap *= -1

        return overlap, supports

    def draw(self, screen, camera):
        super().draw(screen, camera)

        color = (255, 0, 255)
        points = []
        for c in self.corners():
            points.append(camera.world_to_screen(c))

        pygame.draw.polygon(screen, color, points, 1)


class Circle(Collider):
    def __init__(self, parent, position, radius, group=Group.WALLS):
        super().__init__(parent, position, group)
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

        if other.type is Type.CIRCLE:
            dist = np.linalg.norm(self.position - other.position)
            if dist < self.radius + other.radius:
                unit = (self.position - other.position) / dist
                overlap = (self.radius + other.radius - dist) * unit
                supports.append(other.position + other.radius * unit)
        elif other.type is Type.RECTANGLE:
            overlap = np.zeros(2)
            if other.left() < self.position[0] < other.right():
                if self.bottom() < other.top() and other.bottom() < self.top():
                    if self.position[1] > other.position[1]:
                        overlap[1] = other.top() - self.bottom()
                        supports.append(self.position - np.array([0, self.radius]))
                    else:
                        overlap[1] = other.bottom() - self.top()
                        supports.append(self.position + np.array([0, self.radius]))
            elif other.bottom() < self.position[1] < other.top():
                if self.left() < other.right() and other.left() < self.right():
                    if self.position[0] > other.position[0]:
                        overlap[0] = other.right() - self.left()
                        supports.append(self.position - np.array([self.radius, 0]))
                    else:
                        overlap[0] = other.left() - self.right()
                        supports.append(self.position + np.array([self.radius, 0]))
            else:
                for corner in other.corners():
                    dist = np.linalg.norm(self.position - corner)
                    if dist < self.radius:
                        unit = (self.position - corner) / dist
                        overlap = (self.radius - dist) * unit
                        supports.append(self.position - self.radius * unit)

        return overlap, supports


    def draw(self, screen, camera):
        super().draw(screen, camera)

        color = (255, 0, 255)
        center = camera.world_to_screen(self.position)
        pygame.draw.circle(screen, color, center, int(self.radius * camera.zoom), 1)
