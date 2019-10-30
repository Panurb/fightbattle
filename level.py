import numpy as np
import pygame

from gameobject import Pendulum
from collider import Group
from wall import Wall
from player import Player
from camera import Camera
from weapon import Revolver
from prop import Crate, Ball


class Level:
    def __init__(self, option_handler):
        self.camera = Camera([0, 0], option_handler.resolution)

        self.players = []
        self.walls = []
        self.objects = []

        self.colliders = dict()
        for g in Group:
            if g is not Group.NONE:
                self.colliders[g] = []

        self.gravity = np.array([0, -0.1])

        self.add_player([-5, 0])
        self.add_player([5, 0])

        self.add_wall(np.array([0, -3]), 19, 1)
        self.add_wall([-10, 1.5], 1, 10)
        self.add_wall([10, 1.5], 1, 10)

        self.add_wall([-8, 3], 0.2, 0.2)
        self.add_wall([8, 3], 0.2, 0.2)

        self.add_ball([0, 2])
        self.add_gun([2, 2])

        #pendulum = Pendulum([0, 0], 1.0, -0.5)
        #self.objects.append(pendulum)
        #self.colliders[pendulum.group].append(pendulum.collider)

    def input(self, input_handler):
        if input_handler.keys_pressed[pygame.K_c]:
            self.add_crate(input_handler.mouse_position + self.camera.position)
        if input_handler.keys_pressed[pygame.K_b]:
            self.add_ball(input_handler.mouse_position + self.camera.position)

        for i, player in enumerate(self.players):
            player.input(input_handler)

    def add_crate(self, position):
        box = Crate(position)
        self.objects.append(box)
        self.colliders[box.collider.group].append(box.collider)

    def add_ball(self, position):
        ball = Ball(position)
        self.objects.append(ball)
        self.colliders[ball.collider.group].append(ball.collider)

    def add_wall(self, position, width, height):
        wall = Wall(position, width, height)
        self.walls.append(wall)
        self.colliders[wall.collider.group].append(wall.collider)

    def add_gun(self, position):
        gun = Revolver(position)
        self.objects.append(gun)
        self.colliders[gun.collider.group].append(gun.collider)

    def add_player(self, position):
        n = len(self.players)
        player = Player(position, n)
        self.players.append(player)
        self.colliders[player.collider.group].append(player.collider)

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

            self.camera.zoom = min(500 / np.sqrt(dist), self.camera.max_zoom)

    def draw(self, screen, image_handler):
        for wall in self.walls:
            wall.draw(screen, self.camera, image_handler)

        for obj in self.objects:
            obj.draw(screen, self.camera, image_handler)

        for player in self.players:
            player.draw(screen, self.camera, image_handler)
