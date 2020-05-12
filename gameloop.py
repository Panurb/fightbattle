from _thread import *

import numpy as np
import pygame

from camera import Camera
from collider import Group, GRID_SIZE
from gameobject import Destroyable
from helpers import basis
from level import Level
from menu import State, PlayerMenu, MainMenu, OptionsMenu
from player import Player
from network import Network
from prop import Ball
from wall import Basket
from weapon import Bullet


class GameLoop:
    def __init__(self, option_handler):
        self.option_handler = option_handler
        self.state = State.MENU

        self.level = Level()
        self.players = dict()
        self.colliders = []

        self.time_scale = 1.0

        self.camera = Camera([0, 0], option_handler.resolution)

        self.respawn_time = 50.0

        self.menu = MainMenu()
        self.player_menus = []
        for i in range(4):
            self.player_menus.append(PlayerMenu((6 * i - 9) * basis(0)))
        self.options_menu = OptionsMenu()

        self.network = None
        self.network_id = -1
        self.obj_id = -1

        self.controller_id = 0

        self.light = np.zeros(2) if option_handler.shadows else None

    def load_level(self):
        self.level = Level('lvl')

        self.colliders.clear()

        self.colliders = [[[] for _ in range(int(self.level.height))] for _ in range(int(self.level.width))]

        for wall in self.level.walls:
            wall.collider.update_occupied_squares(self.colliders)

        for obj in self.level.objects.values():
            obj.collider.update_occupied_squares(self.colliders)

        if self.light is not None:
            self.light = np.array([0.5 * self.level.width, self.level.height])

    def reset_game(self):
        for w in self.level.walls:
            if type(w) is Basket:
                self.level.scoreboard.scores[w.team] = w.score

        for o in self.level.objects.values():
            if o.collider:
                o.collider.clear_occupied_squares(self.colliders)

        self.level.reset()

        for o in self.level.objects.values():
            o.collider.update_occupied_squares(self.colliders)

        for p in self.players.values():
            p.set_spawn(self.level, self.players)
            p.reset(self.colliders)

    def add_player(self, controller_id, network_id=-1):
        if network_id == -1:
            network_id = controller_id
        player = Player([0, 0], controller_id, network_id)
        self.players[network_id] = player

    def update(self, time_step):
        if self.state is State.PLAY:
            alive = 0
            for player in self.players.values():
                if player.active:
                    alive += 1

                player.update(self.level.gravity, self.time_scale * time_step, self.colliders)

            if len(self.players) > 1 >= alive:
                self.reset_game()

            self.level.update(self.time_scale * time_step, self.colliders)

            for o in list(self.level.objects.values()):
                if type(o) is Ball and o.scored and o.speed < 0.1:
                    self.reset_game()

            self.camera.update(self.time_scale * time_step, self.players, self.level)
        elif self.state is State.MENU:
            self.menu.update(time_step)
            self.state = self.menu.target_state
            self.menu.target_state = State.MENU
        elif self.state is State.PLAYER_SELECT:
            if not self.players:
                return

            for pm in self.player_menus:
                if pm.controller_id is not None:
                    # FIXME: hardcoded index
                    self.players[pm.controller_id].body_type = pm.buttons[1].get_value()
                    self.players[pm.controller_id].head_type = pm.buttons[0].get_value()

            for pm in self.player_menus:
                if pm.controller_id is None:
                    if pm.controller_id in self.players:
                        del self.players[pm.controller_id]

                if pm.target_state is State.MENU:
                    pm.target_state = State.PLAYER_SELECT
                    self.state = State.MENU
                    self.players.clear()
                    return

                if pm.controller_id is not None and pm.target_state is State.PLAYER_SELECT:
                    return

            self.state = State.PLAY
            self.load_level()
            for p in self.players.values():
                p.set_spawn(self.level, self.players)
                p.reset(self.colliders)
        elif self.state is State.LAN:
            if self.network is None:
                self.network = Network()
                data = self.network.data

                if data is None:
                    print('Server can not be reached')
                    self.network = None
                    self.state = State.MENU
                    return

                self.network_id = data[0][0]

                self.add_player(self.controller_id, data[0][0])
                self.players[data[0][0]].apply_data(data[0])

                self.level.clear()
                self.level.apply_data(data[1])

                self.colliders = [[[] for _ in range(int(self.level.height + 1))]
                                  for _ in range(int(self.level.width + 1))]

                for wall in self.level.walls:
                    wall.collider.update_occupied_squares(self.colliders)

                for obj in self.level.objects.values():
                    obj.collider.update_occupied_squares(self.colliders)

                start_new_thread(self.network_thread, ())

            player = self.players[self.network_id]
            player.update(self.level.gravity, self.time_scale * time_step, self.colliders)

            obj = self.players[self.network_id].object
            if obj is not None:
                obj.update(self.level.gravity, self.time_scale * time_step, self.colliders)

            self.camera.update(time_step, self.players, self.level)

            for i in list(self.level.objects):
                obj = self.level.objects[i]
                if isinstance(obj, Destroyable):
                    obj.update(self.level.gravity, self.time_scale * time_step, self.colliders)
                    if obj.destroyed and not obj.debris:
                        del self.level.objects[i]
                elif isinstance(obj, Bullet):
                    obj.update(self.level.gravity, self.time_scale * time_step, self.colliders)
                    if obj.destroyed and not obj.particle_clouds:
                        del self.level.objects[i]
        elif self.state is State.OPTIONS:
            self.state = self.options_menu.target_state
            self.options_menu.target_state = State.OPTIONS
            if self.options_menu.resolution_changed:
                if self.options_menu.buttons[0].get_value() == 'windowed':
                    pygame.display.set_mode(self.options_menu.buttons[1].get_value())
                else:
                    pygame.display.set_mode(self.options_menu.buttons[1].get_value(), pygame.FULLSCREEN)

                self.camera.set_resolution(self.options_menu.buttons[1].get_value())

                self.options_menu.resolution_changed = False

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
                    if player.health <= 0 < p[9]:
                        player.set_spawn(self.level, self.players)
                        player.reset(self.colliders)
                    player.health = p[9]
                else:
                    if p[0] not in self.players:
                        self.add_player(-1, p[0])

                    self.players[p[0]].apply_data(p)

            # kinda purkka
            ids = [p[0] for p in data[0]]
            for k in list(self.players.keys()):
                if k != self.network_id and k not in ids:
                    del self.players[k]

            for d in data[1]:
                if d[0] == self.obj_id:
                    continue

                if d[0] in self.level.objects:
                    self.level.objects[d[0]].apply_data(d)
                else:
                    obj = d[1]([d[2], d[3]])
                    obj.apply_data(d)
                    self.level.objects[d[0]] = obj
                    self.colliders[obj.collider.group].append(obj.collider)

            ids = [o[0] for o in data[1]]
            for i in list(self.level.objects):
                obj = self.level.objects[i]
                obj.collider.update_occupied_squares(self.colliders)
                if i not in ids:
                    if isinstance(obj, Destroyable):
                        obj.destroy(self.colliders)
                    elif isinstance(obj, Bullet):
                        obj.destroy()

    def input(self, input_handler):
        input_handler.update(self.camera)

        if input_handler.quit:
            self.state = State.QUIT

        if self.state is State.PLAY:
            if 0 in self.players:
                input_handler.relative_mouse[:] = input_handler.mouse_position - self.players[0].shoulder

            for i, player in enumerate(self.players.values()):
                player.input(input_handler)

            if input_handler.keys_pressed[pygame.K_r]:
                self.reset_game()
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
                            self.add_player(i)
                            break

            if all(pm.target_state is State.PLAYER_SELECT for pm in self.player_menus):
                for i, controller in enumerate(input_handler.controllers):
                    if controller.button_down['B']:
                        self.state = State.MENU
        elif self.state is State.LAN:
            if self.network is not None:
                player = self.players[self.network_id]

                input_handler.relative_mouse[:] = input_handler.mouse_position - player.shoulder

                self.obj_id = player.object.id if player.object is not None else -1

                player.input(input_handler)
        elif self.state is State.OPTIONS:
            self.options_menu.input(input_handler)

    def draw(self, screen, image_handler):
        if self.state in [State.PLAY, State.LAN]:
            screen.fill((150, 150, 150))
            if self.light is not None:
                for w in self.level.walls:
                    w.draw_shadow(screen, self.camera, self.light)

                for o in self.level.objects.values():
                    o.draw_shadow(screen, self.camera, self.light)

            self.level.draw(screen, self.camera, image_handler)

            for player in self.players.values():
                player.draw(screen, self.camera, image_handler)

            if self.option_handler.debug_draw:
                self.debug_draw(screen, image_handler)
        elif self.state is State.MENU:
            screen.fill((50, 50, 50))
            self.menu.draw(screen, self.camera, image_handler)
        elif self.state is State.PLAYER_SELECT:
            screen.fill((50, 50, 50))
            for pm in self.player_menus:
                pm.draw(screen, self.camera, image_handler)
                if pm.controller_id is not None:
                    self.players[pm.controller_id].set_position(pm.position + 3 * basis(1))
                    self.players[pm.controller_id].on_ground = True
                    self.players[pm.controller_id].animate(0.0)
                    self.players[pm.controller_id].draw(screen, self.camera, image_handler)
        elif self.state is State.OPTIONS:
            screen.fill((50, 50, 50))
            self.options_menu.draw(screen, self.camera, image_handler)

    def debug_draw(self, screen, image_handler):
        for player in self.players.values():
            player.debug_draw(screen, self.camera, image_handler)

        self.level.debug_draw(screen, self.camera, image_handler)

    def play_sounds(self, sound_handler):
        if self.state in [State.PLAY, State.LAN]:
            for p in self.players.values():
                p.play_sounds(sound_handler)

            self.level.play_sounds(sound_handler)
        elif self.state is State.OPTIONS:
            sound_handler.set_volume(self.options_menu.buttons[2].get_value() / 100)
            sound_handler.set_music_volume(self.options_menu.buttons[3].get_value() / 100)
            self.menu.play_sounds(sound_handler)
            self.options_menu.play_sounds(sound_handler)
        else:
            self.menu.play_sounds(sound_handler)
            self.options_menu.play_sounds(sound_handler)
            for pm in self.player_menus:
                pm.play_sounds(sound_handler)
