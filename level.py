import numpy as np
import pygame

from collider import Group
from enemy import Enemy
from helpers import basis
from wall import Wall
from player import Player
from camera import Camera
from weapon import Shield, Sword, Shotgun
from prop import Crate, Ball


class Level:
    def __init__(self, option_handler):
        self.camera = Camera([0, 0], option_handler.resolution)
        self.time_scale = 1.0

        self.players = []
        self.enemies = []
        self.walls = []
        self.objects = []

        self.colliders = dict()
        for g in Group:
            if g is not Group.NONE:
                self.colliders[g] = []

        self.gravity = np.array([0, -0.1])

        self.add_room([0, 10], 50, 20)
        self.add_wall([15.1, 3.1], 20, 1, 0.1 * np.pi)
        self.add_wall([-15.1, 3.1], 20, 1, -0.1 * np.pi)

        self.reset()

    def reset(self):
        self.players.clear()
        self.enemies.clear()
        self.objects.clear()

        for g in Group:
            if g is not Group.WALLS:
                self.colliders[g] = []

        self.add_object(Shotgun([0, 4]))
        self.add_player([-5, 0])
        #self.add_player([2, 0])

        #self.add_object(Ball([0, 2]))
        #self.add_object(Sword([-2, 0]))
        #self.add_object(Shield([4, 2]))
        self.add_object(Crate([-1, 2]))

    def input(self, input_handler):
        if input_handler.keys_pressed[pygame.K_c]:
            self.add_object(Crate(input_handler.mouse_position))
        if input_handler.keys_pressed[pygame.K_b]:
            self.add_object(Ball(input_handler.mouse_position))
        if input_handler.keys_pressed[pygame.K_ESCAPE]:
            self.reset()
        if input_handler.keys_pressed[pygame.K_v]:
            self.add_enemy(input_handler.mouse_position)

        for i, player in enumerate(self.players):
            player.input(input_handler)

    def add_wall(self, position, width, height, angle=0.0):
        wall = Wall(position, width, height, angle)
        self.walls.append(wall)
        self.colliders[wall.collider.group].append(wall.collider)

    def add_object(self, obj):
        self.objects.append(obj)
        self.colliders[obj.collider.group].append(obj.collider)

    def add_room(self, position, width, height):
        self.add_wall(position + 0.5 * width * basis(0), 1, height)
        self.add_wall(position - 0.5 * width * basis(0), 1, height)
        self.add_wall(position + 0.5 * height * basis(1), width, 1)
        self.add_wall(position - 0.5 * height * basis(1), width, 1)

    def add_player(self, position):
        n = len(self.players)
        player = Player(position, n)
        self.players.append(player)
        self.colliders[player.collider.group].append(player.collider)
        self.colliders[player.head.collider.group].append(player.head.collider)
        self.colliders[player.body.collider.group].append(player.body.collider)

    def add_enemy(self, position):
        e = Enemy(position)
        self.enemies.append(e)
        self.colliders[e.collider.group].append(e.collider)
        self.colliders[e.head.collider.group].append(e.head.collider)
        self.colliders[e.body.collider.group].append(e.body.collider)

    def update(self, time_step):
        for p in self.players:
            if p.destroyed and p.active:
                self.time_scale = 0.5
                break
        else:
            self.time_scale = 1.0

        for player in self.players:
            player.update(self.gravity, self.time_scale * time_step, self.colliders)

        for e in self.enemies:
            if e.destroyed and not e.active:
                self.enemies.remove(e)
            e.seek_players(self.players)
            e.update(self.gravity, self.time_scale * time_step, self.colliders)

        for obj in self.objects:
            obj.update(self.gravity, self.time_scale * time_step, self.colliders)

        self.camera.position[:] = np.zeros(2)
        for player in self.players:
            self.camera.position += player.position
        self.camera.position /= len(self.players)

        if len(self.players) > 1:
            dist = 0
            for player in self.players:
                dist = max(dist, np.sum((player.position - self.camera.position)**2))

            if dist != 0:
                self.camera.zoom = min(500 / np.sqrt(dist), self.camera.max_zoom)

    def draw(self, screen, image_handler):
        for wall in self.walls:
            wall.draw(screen, self.camera, image_handler)

        for obj in self.objects:
            obj.draw(screen, self.camera, image_handler)

        for player in self.players:
            player.draw(screen, self.camera, image_handler)

        for e in self.enemies:
            e.draw(screen, self.camera, image_handler)

        #self.debug_draw(screen, image_handler)

    def debug_draw(self, screen, image_handler):
        for wall in self.walls:
            wall.debug_draw(screen, self.camera, image_handler)

        for obj in self.objects:
            obj.debug_draw(screen, self.camera, image_handler)

        for player in self.players:
            player.debug_draw(screen, self.camera, image_handler)

