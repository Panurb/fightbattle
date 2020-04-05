import pickle
from _thread import *

import numpy as np
import pygame

from camera import Camera
from collider import Group
from enemy import Enemy
from gameobject import Destroyable, PhysicsObject
from helpers import norm2, basis
from menu import State, Menu, PlayerMenu, MainMenu
from player import Player
from network import Network
from prop import Crate
from weapon import Weapon, Gun, Bullet


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
        self.obj_id = -1

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

        for obj in self.level.objects.values():
            self.colliders[obj.collider.group].append(obj.collider)

        self.scores = [0] * len(self.players)

    def add_player(self, controller_id, network_id=-1):
        player = Player([0, 0], controller_id, network_id)
        self.players[network_id] = player
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
                    player.set_spawn(self.level, self.players)
                    player.reset(self.colliders)

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
                p = self.network.data
                self.network_id = p[0][0]

                self.add_player(self.controller_id, p[0][0])
                self.players[p[0][0]].apply_data(p[0])

                self.level.objects.clear()
                self.colliders[Group.PROPS].clear()

                start_new_thread(self.network_thread, ())

            player = self.players[self.network_id]
            player.update(self.level.gravity, self.time_scale * time_step, self.colliders)

            obj = self.players[self.network_id].object
            if obj is not None:
                obj.update(self.level.gravity, self.time_scale * time_step, self.colliders)

            self.camera.update(time_step, self.players)

            for obj in list(self.level.objects.values()):
                if isinstance(obj, Destroyable):
                    if obj.health <= 0:
                        obj.destroy(-basis(1), self.colliders)
                    if obj.destroyed:
                        obj.update(self.level.gravity, self.time_scale * time_step, self.colliders)

    def network_thread(self):
        while True:
            data = [self.players[self.network_id].get_data()]

            if self.obj_id != -1:
                data.append(self.level.objects[self.obj_id].get_data())
                self.level.objects[self.obj_id].attacked = False

            data = self.network.send(data)

            for p in data[0]:
                if p[0] == self.network_id:
                    player = self.players[self.network_id]
                    if player.health <= 0 and p[9] > 0:
                        player.set_spawn(self.level, self.players)
                        player.reset(self.colliders)
                    player.health = p[9]
                else:
                    if p[0] not in self.players:
                        self.add_player(-1, p[0])

                    self.players[p[0]].apply_data(p)

            # kinda purkka
            ids = [self.network_id] + [p[0] for p in data[0]]
            for k in list(self.players.keys()):
                if k not in ids:
                    del self.players[k]

            for d in data[1]:
                if d[0] == self.obj_id:
                    continue

                if d[0] in self.level.objects:
                    self.level.objects[d[0]].apply_data(d)
                else:
                    obj = d[1]([d[2], d[3]])
                    obj.id = d[0]
                    obj.apply_data(d)
                    self.level.objects[d[0]] = obj

            # kinda purkka
            ids = [p[0] for p in data[1]]
            for k in list(self.level.objects.keys()):
                if k not in ids:
                    del self.level.objects[k]

            for g in Group:
                if g not in [Group.NONE, Group.PLAYERS, Group.HITBOXES, Group.WALLS, Group.PLATFORMS, Group.DEBRIS]:
                    self.colliders[g].clear()

            for obj in self.level.objects.values():
                if obj.collider is not None:
                    self.colliders[obj.collider.group].append(obj.collider)

    def input(self, input_handler):
        input_handler.update(self.camera)

        if input_handler.quit:
            self.state = State.QUIT

        if self.state is State.PLAY:
            if 0 in self.players:
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

                self.obj_id = player.object.id if player.object is not None else -1

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
