import numpy as np

from gameobject import GameObject, PhysicsObject, Group
from collider import Rectangle, Circle
from player import Player
from camera import Camera
from weapon import Gun


class Level:
    def __init__(self):
        self.camera = Camera([0, 0])

        self.players = []
        self.walls = []
        self.objects = []

        self.colliders = dict()
        for g in Group:
            self.colliders[g] = []

        self.gravity = np.array([0, -0.1])

        self.add_player([0, 0])
        #self.add_player([5, 0])

        self.add_wall(np.array([0, -3]), 100, 1)
        self.add_wall([-5, 0], 1, 10)
        self.add_gun([0, 2])

    def input(self, input_handler):
        if input_handler.mouse_pressed[1]:
            self.add_box(input_handler.mouse_position + self.camera.position)
        if input_handler.mouse_pressed[3]:
            self.add_ball(input_handler.mouse_position + self.camera.position)

        for i, player in enumerate(self.players):
            player.input(input_handler)

    def add_box(self, position):
        box = Box(position)
        #box.angular_velocity = 0.1
        self.objects.append(box)
        self.colliders[box.group].append(box.collider)

    def add_ball(self, position):
        ball = Ball(position)
        self.objects.append(ball)
        self.colliders[ball.group].append(ball.collider)

    def add_wall(self, position, width, height):
        wall = Wall(position, width, height)
        self.walls.append(wall)
        self.colliders[wall.group].append(wall.collider)

    def add_gun(self, position):
        gun = Gun(position)
        self.objects.append(gun)
        self.colliders[gun.group].append(gun.collider)

    def add_player(self, position):
        n = len(self.players) - 1
        player = Player(position, n)
        self.players.append(player)
        self.colliders[player.group].append(player.collider)

    def update(self, time_step):
        for player in self.players:
            player.update(self.gravity, time_step, self.colliders)

        for obj in self.objects:
            obj.update(self.gravity, time_step, self.colliders)

        self.camera.position[:] = np.zeros(2)
        for player in self.players:
            self.camera.position += player.position
        self.camera.position /= len(self.players)

        if len(self.players) > 1:
            dist = 0
            for player in self.players:
                dist = max(dist, np.sum((player.position - self.camera.position)**2))

            self.camera.zoom = min(500 / np.sqrt(dist), 50)

    def draw(self, screen):
        for wall in self.walls:
            wall.draw(screen, self.camera)

        for player in self.players:
            player.draw(screen, self.camera)

        for obj in self.objects:
            obj.draw(screen, self.camera)


class Wall(GameObject):
    def __init__(self, position, width, height):
        super().__init__(position, group=Group.WALLS)
        collider = Rectangle([0, 0], width, height)
        self.add_collider(collider)


class Box(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, group=Group.BOXES)
        self.add_collider(Rectangle([0, 0], 1, 1))

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)


class Ball(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, group=Group.BOXES)
        self.add_collider(Circle([0, 0], 0.5))
