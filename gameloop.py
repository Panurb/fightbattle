import pickle
import enum

import numpy as np
import pygame

from camera import Camera
from collider import Group
from enemy import Enemy
from helpers import norm2
from player import Player


class State(enum.Enum):
    QUIT = 1
    PLAY = 2


class GameLoop:
    def __init__(self, option_handler):
        self.state = State.PLAY

        self.level = None
        self.players = []
        self.enemies = []
        self.colliders = dict()

        self.scores = [0] * len(self.players)

        self.reset_level()

        self.time_scale = 1.0

        self.camera = Camera([0, 0], option_handler.resolution)

        self.respawn_time = 50.0

    def reset_level(self):
        with open('lvl.pickle', 'rb') as f:
            self.level = pickle.load(f)

        self.players = []
        self.enemies = []
        self.colliders = dict()

        for g in Group:
            if g is not Group.NONE:
                self.colliders[g] = []

        for wall in self.level.walls:
            self.colliders[wall.collider.group].append(wall.collider)

        for obj in self.level.objects:
            self.colliders[obj.collider.group].append(obj.collider)

        for p in self.level.player_spawns:
            self.add_player(p.position)

        self.scores = [0] * len(self.players)

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

    def update(self, input_handler, time_step):
        if self.state is State.PLAY:
            if input_handler.keys_pressed[pygame.K_r]:
                self.reset_level()

            self.input(input_handler)

            for player in self.players:
                player.update(self.level.gravity, self.time_scale * time_step, self.colliders)

                if player.destroyed and player.timer >= self.respawn_time:
                    player.reset(self.colliders)
                    player.set_position(self.level.player_spawns[player.number].position)

            for e in self.enemies:
                if e.active:
                    e.seek_players(self.players)
                    e.update(self.level.gravity, self.time_scale * time_step, self.colliders)
                else:
                    self.enemies.remove(e)

            self.level.update(self.time_scale * time_step, self.colliders)

            cam_goal = sum(p.position for p in self.players) / len(self.players)
            self.camera.position[:] += self.time_scale * time_step * (cam_goal - self.camera.position)

            if len(self.players) > 1:
                dist2 = max(norm2(p.position - cam_goal) for p in self.players)
                zoom_goal = min(500 / (np.sqrt(dist2) + 1e-6), self.camera.max_zoom)
                self.camera.zoom += self.time_scale * time_step * (zoom_goal - self.camera.zoom)

    def input(self, input_handler):
        input_handler.update(self.camera)

        if self.players:
            input_handler.relative_mouse[:] = input_handler.mouse_position - self.players[0].shoulder

        if input_handler.keys_pressed[pygame.K_v]:
            self.add_enemy(input_handler.mouse_position)

        for i, player in enumerate(self.players):
            player.input(input_handler)

        if input_handler.quit:
            self.state = State.QUIT

    def draw(self, screen, image_handler):
        screen.fill((150, 150, 150))

        self.level.draw(screen, self.camera, image_handler)

        for player in self.players:
            player.draw(screen, self.camera, image_handler)

        for e in self.enemies:
            e.draw(screen, self.camera, image_handler)

    def debug_draw(self, screen, image_handler):
        for player in self.players:
            player.debug_draw(screen, self.camera, image_handler)
