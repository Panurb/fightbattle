import numpy as np

from gameobject import GameObject, PhysicsObject, Group
from collider import Rectangle, Circle
from player import Player
from camera import Camera


class Wall(GameObject):
    def __init__(self, position, width, height):
        super().__init__(position, group=Group.WALLS)
        collider = Rectangle(self, position, width, height)
        self.add_collider(collider)


class Gun(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, group=Group.GUNS)
        self.add_collider(Rectangle(self, position + np.array([0.4, 0.3]), 1, 0.2))
        self.add_collider(Rectangle(self, position, 0.2, 0.5))


class Box(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, group=Group.BOXES)
        self.add_collider(Rectangle(self, position, 1, 1))

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)


class Ball(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, group=Group.BOXES)
        self.add_collider(Circle(self, position, 0.5))


class Level:
    def __init__(self):
        self.camera = Camera([0, 0])

        self.players = []
        self.walls = []
        self.objects = []
        self.colliders = []

        self.gravity = np.array([0, -0.1])

        self.add_player([-2, 0])
        self.add_wall(np.array([0, -3]), 12, 1)
        self.add_wall(np.array([5, -1]), 12, 1)
        self.add_gun([0, 2])

    def input(self, input_handler):
        if input_handler.mouse_pressed[1]:
            self.add_box(self.camera.screen_to_world(input_handler.mouse_position))
        if input_handler.mouse_pressed[3]:
            self.add_ball(self.camera.screen_to_world(input_handler.mouse_position))

        for player in self.players:
            player.input(input_handler)

    def add_box(self, position):
        box = Box(position)
        self.objects.append(box)
        self.colliders += box.colliders

    def add_ball(self, position):
        ball = Ball(position)
        self.objects.append(ball)
        self.colliders += ball.colliders

    def add_wall(self, position, width, height):
        wall = Wall(position, width, height)
        self.walls.append(wall)
        self.colliders += wall.colliders

    def add_gun(self, position):
        gun = Gun(position)
        self.objects.append(gun)
        self.colliders += gun.colliders

    def add_player(self, position):
        player = Player(position)
        self.players.append(player)
        self.colliders += player.colliders
        self.colliders.append(player.hand)

    def update(self, time_step):
        for player in self.players:
            player.update(self.gravity, time_step, self.colliders)

        for obj in self.objects:
            obj.update(self.gravity, time_step, self.colliders)

        self.camera.position[:] = self.players[0].position

    def draw(self, screen):
        for wall in self.walls:
            wall.draw(screen, self.camera)

        for player in self.players:
            player.draw(screen, self.camera)

        for obj in self.objects:
            obj.draw(screen, self.camera)
