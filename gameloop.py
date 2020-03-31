import pickle

import numpy as np
import pygame

from camera import Camera
from collider import Group
from enemy import Enemy
from helpers import norm2, basis
from menu import State, Menu, PlayerMenu, MainMenu
from player import Player


class GameLoop:
    def __init__(self, option_handler):
        self.state = State.MENU

        self.level = None
        self.players = []
        self.enemies = []
        self.colliders = dict()
        for g in Group:
            if g is not Group.NONE:
                self.colliders[g] = []

        self.scores = [0] * len(self.players)

        #self.reset_level()

        self.time_scale = 1.0

        self.camera = Camera([0, 0], option_handler.resolution)

        self.respawn_time = 50.0

        self.menu = MainMenu()
        self.player_menus = []
        for i in range(4):
            self.player_menus.append(PlayerMenu((5 * i - 10) * basis(0)))

    def reset_level(self):
        with open('levels/lvl.pickle', 'rb') as f:
            self.level = pickle.load(f)

        self.enemies.clear()

        for g in Group:
            if g not in [Group.NONE, Group.PLAYERS, Group.HITBOXES]:
                self.colliders[g] = []

        for wall in self.level.walls:
            self.colliders[wall.collider.group].append(wall.collider)

        for obj in self.level.objects:
            self.colliders[obj.collider.group].append(obj.collider)

        for i, p in enumerate(self.level.player_spawns):
            if i >= len(self.players):
                break
            self.players[i].set_position(p.position)

        self.scores = [0] * len(self.players)

    def add_player(self, controller_id):
        player = Player([0, 0], controller_id)
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
        if self.state is State.PLAY:
            for player in self.players:
                if player.destroyed and player.timer >= self.respawn_time:
                    i = 0
                    max_dist = 0.0
                    for j, s in enumerate(self.level.player_spawns):
                        min_dist = np.inf
                        for p in self.players:
                            if not p.destroyed:
                                min_dist = min(min_dist, norm2(s.position - p.position))
                        if min_dist > max_dist:
                            max_dist = min_dist
                            i = j

                    player.reset(self.colliders)
                    player.set_position(self.level.player_spawns[i].position)

                player.update(self.level.gravity, self.time_scale * time_step, self.colliders)

            for e in self.enemies:
                if e.active:
                    e.seek_players(self.players)
                    e.update(self.level.gravity, self.time_scale * time_step, self.colliders)
                else:
                    self.enemies.remove(e)

            self.level.update(self.time_scale * time_step, self.colliders)

            self.camera.update(self.time_scale * time_step, self.players)
        elif self.state is State.MENU:
            self.state = self.menu.target_state
        elif self.state is State.PLAYER_SELECT:
            for pm in self.player_menus:
                if pm.controller_id is not None and all(p.controller_id != pm.controller_id for p in self.players):
                    self.add_player(pm.controller_id)

            if not self.players:
                return

            for pm in self.player_menus:
                if pm.controller_id is not None and pm.target_state is not State.PLAY:
                    return

            self.state = State.PLAY
            self.reset_level()

    def input(self, input_handler):
        input_handler.update(self.camera)

        if input_handler.quit:
            self.state = State.QUIT

        if self.state is State.PLAY:
            if self.players:
                input_handler.relative_mouse[:] = input_handler.mouse_position - self.players[0].shoulder

            if input_handler.keys_pressed[pygame.K_v]:
                self.add_enemy(input_handler.mouse_position)

            for i, player in enumerate(self.players):
                player.input(input_handler)

            if input_handler.keys_pressed[pygame.K_r]:
                self.reset_level()
        elif self.state is State.MENU:
            self.menu.input(input_handler)
        elif self.state is State.PLAYER_SELECT:
            for i, controller in enumerate(input_handler.controllers):
                for pm in self.player_menus:
                    if pm.controller_id == i:
                        pm.input(input_handler, i)
                        break
                else:
                    for pm in self.player_menus:
                        if pm.controller_id is None:
                            pm.input(input_handler, i)
                        if pm.controller_id == i:
                            break

    def draw(self, screen, image_handler):
        screen.fill((150, 150, 150))

        if self.state is State.PLAY:
            self.level.draw(screen, self.camera, image_handler)

            for player in self.players:
                player.draw(screen, self.camera, image_handler)

            for e in self.enemies:
                e.draw(screen, self.camera, image_handler)

            #self.debug_draw(screen, image_handler)
        elif self.state is State.MENU:
            self.menu.draw(screen, self.camera, image_handler)
        elif self.state is State.PLAYER_SELECT:
            for pm in self.player_menus:
                pm.draw(screen, self.camera, image_handler)

    def debug_draw(self, screen, image_handler):
        for player in self.players:
            player.debug_draw(screen, self.camera, image_handler)

        self.level.debug_draw(screen, self.camera, image_handler)

    def play_sounds(self, sound_handler):
        if self.state is State.PLAY:
            for p in self.players:
                p.play_sounds(sound_handler)

            self.level.play_sounds(sound_handler)
