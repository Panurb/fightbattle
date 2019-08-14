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
    def __init__(self, collider, overlap):
        self.collider = collider
        self.overlap = overlap


class Collider:
    def __init__(self, parent, position, group=Group.WALLS):
        self.parent = parent
        self.position = np.array(position, dtype=float)
        self.group = group
        self.friction = 0.5

    def get_collisions(self, colliders):
        collisions = []

        for c in colliders:
            if c is self:
                continue

            if c.parent is self.parent:
                continue

            if not COLLISION_MATRIX[self.group][c.group]:
                continue

            overlap = self.overlap(c)
            if overlap is not None:
                collisions.append(Collision(c, overlap))

        return collisions

    def overlap(self, other):
        pass


class Rectangle(Collider):
    def __init__(self, parent, position, width, height, group=Group.WALLS):
        super().__init__(parent, position, group)
        self.half_width = np.array([0.5 * width, 0.0])
        self.half_height = np.array([0.0, 0.5 * height])
        self.type = Type.RECTANGLE

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
        if other.type is Type.RECTANGLE:
            if other.left() < self.right() and self.left() < other.right():
                if other.bottom() < self.top() and self.bottom() < other.top():
                    overlap = np.zeros(2)
                    if self.position[0] > other.position[0]:
                        overlap[0] = other.right() - self.left()
                    else:
                        overlap[0] = other.left() - self.right()

                    if self.position[1] > other.position[1]:
                        overlap[1] = other.top() - self.bottom()
                    else:
                        overlap[1] = other.bottom() - self.top()

                    i = np.argmax(np.abs(overlap))
                    overlap[i] = 0.0

                    return overlap
        elif other.type is Type.CIRCLE:
            overlap = other.overlap(self)
            if overlap is not None:
                return -overlap

        return None

    def draw(self, screen, camera):
        color = (255, 0, 255)
        x, y = camera.world_to_screen(self.position - self.half_width + self.half_height)
        w = 2 * self.half_width[0] * camera.zoom
        h = 2 * self.half_height[1] * camera.zoom
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, color, rect, 1)


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
        if other.type is Type.CIRCLE:
            dist = np.linalg.norm(self.position - other.position)
            if dist < self.radius + other.radius:
                overlap = (self.radius + other.radius - dist) * (self.position - other.position) / dist
                return overlap
        elif other.type is Type.RECTANGLE:
            if other.left() < self.position[0] < other.right():
                if self.bottom() < other.top() and other.bottom() < self.top():
                    overlap = np.zeros(2)
                    if self.position[1] > other.position[1]:
                        overlap[1] = other.top() - self.bottom()
                    else:
                        overlap[1] = other.bottom() - self.top()

                    return overlap

            if other.bottom() < self.position[1] < other.top():
                if self.left() < other.right() and other.left() < self.right():
                    overlap = np.zeros(2)
                    if self.position[0] > other.position[0]:
                        overlap[0] = other.right() - self.left()
                    else:
                        overlap[0] = other.left() - self.right()

                    return overlap

            for corner in other.corners():
                dist = np.linalg.norm(self.position - corner)
                if dist < self.radius:
                    overlap = (self.radius - dist) * (self.position - corner) / dist

                    return overlap

        return None


    def draw(self, screen, camera):
        color = (255, 0, 255)
        center = camera.world_to_screen(self.position)
        pygame.draw.circle(screen, color, center, int(self.radius * camera.zoom), 1)
