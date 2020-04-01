import pickle

import numpy as np
import pygame

from camera import Camera
from collider import Group
from enemy import Enemy
from gameobject import Destroyable
from helpers import norm2, basis
from menu import State, Menu, PlayerMenu, MainMenu
from player import Player
from network import Network


class GameLoop:
    def __init__(self, option_handler):
        self.state = State.MENU

        self.level = None
        self.players = dict()
        self.enemies = []
        self.colliders = dict()
        for g in Group:
            if g is not Group.NONE:
                self.colliders[g] = []

        self.scores = [0] * len(self.players)

        self.reset_level()

        self.time_scale = 1.0

        self.camera = Camera([0, 0], option_handler.resolution)

        self.respawn_time = 50.0

        self.menu = MainMenu()
        self.player_menus = []
        for i in range(4):
            self.player_menus.append(PlayerMenu((5 * i - 10) * basis(0)))

        self.network = None
        self.network_id = -1
        self.old_obj = None

        self.controller_id = 0

    def reset_level(self):
        with open('data/levels/lvl.pickle', 'rb') as f:
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
        self.players[controller_id] = player
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
            for player in self.players.values():
                if player.destroyed and player.timer >= self.respawn_time:
                    i = 0
                    max_dist = 0.0
                    for j, s in enumerate(self.level.player_spawns):
                        min_dist = np.inf
                        for p in self.players.values():
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
                    e.seek_players(self.players.values())
                    e.update(self.level.gravity, self.time_scale * time_step, self.colliders)
                else:
                    self.enemies.remove(e)

            self.level.update(self.time_scale * time_step, self.colliders)

            self.camera.update(self.time_scale * time_step, self.players)
        elif self.state is State.MENU:
            self.state = self.menu.target_state
        elif self.state is State.PLAYER_SELECT:
            for pm in self.player_menus:
                if pm.controller_id is not None:
                    if all(p.controller_id != pm.controller_id for p in self.players.values()):
                        self.add_player(pm.controller_id)

            if not self.players:
                return

            for pm in self.player_menus:
                if pm.controller_id is not None and pm.target_state is not State.PLAY:
                    return

            self.state = State.PLAY
            self.reset_level()
        elif self.state is State.LAN:
            if self.network is None:
                self.network = Network()
                p = self.network.player
                self.network_id = p[0]

                player = Player([p[1], p[2]], network_id=p[0], controller_id=self.controller_id)
                player.angle = p[3]
                self.players[p[0]] = player

            self.players[self.network_id].update(self.level.gravity, self.time_scale * time_step, self.colliders)
            self.camera.update(time_step, self.players)

            data = [self.players[self.network_id].get_data(), []]
            if self.old_obj is not None:
                data[1].append(self.old_obj.get_data())
            data = self.network.send(data)

            for p in data[0]:
                if p[0] not in self.players:
                    self.players[p[0]] = Player([0, 0], network_id=p[0])
                player = self.players[p[0]]
                player.apply_data(p)

            # kinda purkka
            ids = [self.network_id] + [p[0] for p in data[0]]
            for k in list(self.players.keys()):
                if k not in ids:
                    del self.players[k]

            for i, obj in enumerate(self.level.objects):
                obj.apply_data(data[1][i])
                if isinstance(obj, Destroyable) and obj.health <= 0:
                    obj.destroy(np.zeros(2), self.colliders)

            for g in Group:
                if g not in [Group.NONE, Group.PLAYERS, Group.HITBOXES, Group.WALLS, Group.PLATFORMS]:
                    self.colliders[g] = []

            for obj in self.level.objects:
                if obj.collider is not None:
                    self.colliders[obj.collider.group].append(obj.collider)

            for obj in self.level.objects:
                if isinstance(obj, Destroyable) and obj.destroyed:
                    obj.update(self.level.gravity, self.time_scale * time_step, self.colliders)

    def input(self, input_handler):
        input_handler.update(self.camera)

        if input_handler.quit:
            self.state = State.QUIT

        if self.state is State.PLAY:
            if self.players:
                input_handler.relative_mouse[:] = input_handler.mouse_position - self.players[0].shoulder

            if input_handler.keys_pressed[pygame.K_v]:
                self.add_enemy(input_handler.mouse_position)

            for i, player in enumerate(self.players.values()):
                player.input(input_handler)

            if input_handler.keys_pressed[pygame.K_r]:
                self.reset_level()
        elif self.state is State.MENU:
            self.menu.input(input_handler)
            for i in range(len(input_handler.controllers)):
                if self.menu.selection_moved[i]:
                    self.controller_id = i
                    break
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
        elif self.state is State.LAN:
            if self.network is not None:
                player = self.players[self.network_id]

                input_handler.relative_mouse[:] = input_handler.mouse_position - player.shoulder

                self.old_obj = player.object

                player.input(input_handler)

    def draw(self, screen, image_handler):
        screen.fill((150, 150, 150))

        if self.state in [State.PLAY, State.LAN]:
            self.level.draw(screen, self.camera, image_handler)

            for player in self.players.values():
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
        for player in self.players.values():
            player.debug_draw(screen, self.camera, image_handler)

        self.level.debug_draw(screen, self.camera, image_handler)

    def play_sounds(self, sound_handler):
        if self.state in [State.PLAY, State.LAN]:
            for p in self.players.values():
                p.play_sounds(sound_handler)

            self.level.play_sounds(sound_handler)
