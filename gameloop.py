import os
import pickle
from _thread import *

import numpy as np
from pyglet.window import key

from camera import Camera
from collider import Group
from enemy import Enemy
from gameobject import Destroyable
from helpers import basis
from inputhandler import Controller
from level import Level
from menu import State, PlayerMenu, MainMenu, OptionsMenu, PauseMenu, LevelMenu, ControlsMenu, CampaignMenu
from player import Player
from network import Network
from prop import Ball
from text import Text
from weapon import Bullet


class GameLoop:
    def __init__(self, option_handler):
        self.option_handler = option_handler
        self.state = State.MENU
        self.previous_state = State.MENU

        self.level = None
        self.players = {}
        self.colliders = []

        self.time_scale = 1.0

        self.camera = Camera([0, 0], self.option_handler.resolution)

        self.respawn_time = 50.0

        self.menu = MainMenu()
        self.campaign_menu = CampaignMenu()
        self.player_menus = [PlayerMenu(np.array([6 * i - 9, -16])) for i in range(4)]
        self.options_menu = OptionsMenu()
        self.options_menu.set_values(self.option_handler)
        self.pause_menu = PauseMenu()
        self.level_menu = LevelMenu()
        self.controls_menu = ControlsMenu()

        self.network = None
        self.network_id = -1
        self.obj_id = -1

        self.controller = None
        self.controller_id = 1

        self.score_limit = 0
        self.text = Text('', np.zeros(2), 2.0)
        self.delay_timer = 0.0
        self.delay = 3.0

        self.timer = 0.0

    def load_level(self, name):
        self.level = Level(name)
        self.level.dust = self.option_handler.dust

        self.colliders.clear()

        self.colliders = [[[] for _ in range(int(self.level.height))] for _ in range(int(self.level.width))]

        for wall in self.level.walls:
            wall.collider.update_occupied_squares(self.colliders)

        for goal in self.level.goals:
            goal.collider.update_occupied_squares(self.colliders)

        for obj in self.level.objects.values():
            obj.collider.update_occupied_squares(self.colliders)

        for p in self.players.values():
            p.set_spawn(self.level, self.players)
            p.collider.update_occupied_squares(self.colliders)

        self.delay_timer = self.delay

    def reset_game(self):
        for o in self.level.objects.values():
            if o.collider:
                o.collider.clear_occupied_squares(self.colliders)

        self.level.reset()

        for obj in self.level.objects.values():
            obj.collider.update_occupied_squares(self.colliders)

        for p in self.players.values():
            p.reset(self.colliders)
            p.set_spawn(self.level, self.players)

        self.delay_timer = self.delay
        self.time_scale = 1.0

        zoom = min(self.camera.resolution[0] / self.level.width, self.camera.resolution[1] / self.level.height)
        self.camera.set_position_zoom(0.5 * np.array([self.level.width, self.level.height]), zoom)

        self.timer = 0.0

    def delete_game(self):
        if self.state is State.CAMPAIGN:
            for k, p in list(self.players.items()):
                if type(p) is Enemy:
                    p.delete()
                    del self.players[k]
                else:
                    p.reset(self.colliders)
        else:
            for p in self.players.values():
                p.reset(self.colliders)

        self.level.delete()
        self.level = None

        self.delay_timer = 0
        self.text.string = ''
        self.camera.set_position_zoom(self.level_menu.position, self.camera.max_zoom)

    def add_player(self, controller_id, network_id=-1):
        if network_id == -1:
            network_id = controller_id
        player = Player([0, 0], controller_id, network_id)
        self.players[network_id] = player

    def update(self, time_step):
        old_state = self.state

        if self.state is State.SINGLEPLAYER:
            if not self.level:
                path = os.path.join('singleplayer', self.campaign_menu.level_slider.get_value())
                self.load_level(path)
                self.delay_timer = 0
                self.campaign_menu.set_visible(False)
                self.score_limit = int(self.level_menu.score_slider.get_value())
                zoom = min(self.camera.resolution[0] / self.level.width, self.camera.resolution[1] / self.level.height)
                self.camera.set_position_zoom(0.5 * np.array([self.level.width, self.level.height]), zoom)
                for p in self.level.player_spawns:
                    if p.team == 'red':
                        player = Enemy(p.position)
                        self.players[len(self.players)] = player

            self.timer += time_step

            self.text.position[:] = self.camera.position

            for player in self.players.values():
                player.update(self.level.gravity, self.time_scale * time_step, self.colliders)
                if player.controller_id == -1:
                    player.update_ai(self.level.objects, list(self.players.values())[0], self.colliders)
                else:
                    player.collider.update_collisions(self.colliders, {Group.GOALS})
                    if player.collider.collisions:
                        self.state = State.CAMPAIGN
                        self.campaign_menu.times[self.level.name] = min(self.timer,
                                                                        self.campaign_menu.times[self.level.name])
                        self.campaign_menu.save()

            self.level.update(self.time_scale * time_step, self.colliders)

            self.camera.set_target(self.players, self.level)
            self.text.position[:] = self.camera.position
        if self.state is State.MULTIPLAYER:
            if not self.level:
                path = os.path.join('multiplayer', self.level_menu.level_slider.get_value())
                self.load_level(path)
                self.level_menu.set_visible(False)
                self.score_limit = int(self.level_menu.score_slider.get_value())
                zoom = min(self.camera.resolution[0] / self.level.width, self.camera.resolution[1] / self.level.height)
                self.camera.set_position_zoom(0.5 * np.array([self.level.width, self.level.height]), zoom)

            if self.delay_timer > 0:
                if self.level.background:
                    self.delay_timer -= time_step
                    if not self.text.string:
                        self.text.string = 'GET READY'
                        self.time_scale = 0.0
            else:
                self.delay_timer = 0.0
                if 'SCORES' in self.text.string:
                    self.reset_game()
                elif 'WINS' in self.text.string:
                    self.state = State.LEVEL_SELECT
                    for p in self.players.values():
                        p.reset(self.colliders)
                    self.level.delete()
                    self.level = None

                    self.delay_timer = 0
                    self.text.string = ''
                    self.camera.position[:] = self.level_menu.position
                    self.camera.zoom = self.camera.max_zoom
                    return
                self.text.string = ''
                self.time_scale = 1.0

            alive = {'blue': False, 'red': False}

            for player in self.players.values():
                player.update(self.level.gravity, self.time_scale * time_step, self.colliders)
                if not player.destroyed:
                    alive[player.team] = True

            self.level.update(self.time_scale * time_step, self.colliders)

            if self.delay_timer == 0:
                if len(self.players) > 1:
                    if not any(alive.values()):
                        self.reset_game()
                    elif alive['red'] and not alive['blue']:
                        self.level.scoreboard.scores['red'] += 1
                        self.text.string = 'RED SCORES'
                        self.time_scale = 0.5
                        self.delay_timer = self.delay
                    elif alive['blue'] and not alive['red']:
                        self.level.scoreboard.scores['blue'] += 1
                        self.text.string = 'BLUE SCORES'
                        self.time_scale = 0.5
                        self.delay_timer = self.delay

                for team, score in self.level.scoreboard.scores.items():
                    if score == self.score_limit:
                        self.text.string = f'{team} wins'.upper()
                        self.time_scale = 0.5
                        self.delay_timer = 2 * self.delay
                        break
                else:
                    for o in self.level.objects.values():
                        if type(o) is Ball and o.scored:
                            self.text.string = f'{o.scored} scores'.upper()
                            self.time_scale = 0.5
                            self.delay_timer = self.delay

                self.camera.set_target(self.players, self.level)
                self.text.position[:] = self.camera.position
        elif self.state is State.MENU:
            for p in self.players.values():
                p.delete()
            self.players.clear()

            self.camera.target_position[:] = self.menu.position
            self.menu.update(time_step)
            self.state = self.menu.target_state
            self.menu.target_state = State.MENU

            if self.state is State.OPTIONS:
                self.option_handler.load()
                self.options_menu.set_values(self.option_handler)
        elif self.state is State.CAMPAIGN:
            if self.level:
                self.delete_game()

            if not self.players:
                self.add_player(0)

            self.players[0].body_type = self.campaign_menu.body_slider.get_value()
            self.players[0].head_type = self.campaign_menu.head_slider.get_value()

            self.players[0].set_position(self.campaign_menu.position + 3 * basis(1))
            self.players[0].on_ground = True
            self.players[0].animate(0.0)

            self.state = self.campaign_menu.target_state
            self.campaign_menu.set_visible(self.state is State.SINGLEPLAYER)
            self.campaign_menu.target_state = State.CAMPAIGN

            if self.state is not State.CAMPAIGN:
                self.campaign_menu.save()

            if self.previous_state in {State.PAUSED, State.SINGLEPLAYER}:
                self.camera.set_position_zoom(self.campaign_menu.position, self.camera.max_zoom)
            else:
                self.camera.target_position[:] = self.campaign_menu.position
        elif self.state is State.PLAYER_SELECT:
            camera_pos = 0.5 * (self.player_menus[0].position + self.player_menus[-1].position)
            if self.previous_state in {State.PAUSED, State.MULTIPLAYER}:
                self.camera.set_position_zoom(camera_pos, self.camera.max_zoom)
            else:
                self.camera.target_position[:] = camera_pos

            for pm in self.player_menus:
                if pm.joined:
                    self.players[pm.controller_id].body_type = pm.body_slider.get_value()
                    self.players[pm.controller_id].head_type = pm.head_slider.get_value()
                    self.players[pm.controller_id].team = pm.team_slider.get_value()

                    self.players[pm.controller_id].set_position(pm.position + 3 * basis(1))
                    self.players[pm.controller_id].on_ground = True
                    self.players[pm.controller_id].animate(0.0)
                else:
                    if pm.controller_id is not None:
                        self.players[pm.controller_id].delete()
                        del self.players[pm.controller_id]
                        pm.controller_id = None
                        return

            if self.players and all(not pm.joined or pm.ready for pm in self.player_menus):
                self.state = State.LEVEL_SELECT
                for pm in self.player_menus:
                    pm.ready = False
        elif self.state is State.LEVEL_SELECT:
            if self.level:
                self.delete_game()
            self.camera.target_position[:] = self.level_menu.position
            self.state = self.level_menu.target_state
            self.level_menu.target_state = State.LEVEL_SELECT
        elif self.state is State.LAN:
            if self.network is None:
                self.menu.set_visible(False)

                self.network = Network()
                data = self.network.data

                if data is None:
                    print('Server can not be reached')
                    self.network = None
                    self.state = State.MENU
                    return

                self.network_id = data[0][0]

                self.add_player(self.controller_id, self.network_id)
                self.players[self.network_id].apply_data(data[0])

                self.level = Level()
                self.level.apply_data(data[1])

                self.colliders = [[[] for _ in range(int(self.level.height))] for _ in range(int(self.level.width))]

                for wall in self.level.walls:
                    wall.collider.update_occupied_squares(self.colliders)

                for goal in self.level.goals:
                    goal.collider.update_occupied_squares(self.colliders)

                for obj in self.level.objects.values():
                    obj.collider.update_occupied_squares(self.colliders)

                start_new_thread(self.network_thread, ())

            for i in list(self.level.objects.keys()):
                obj = self.level.objects[i]
                if isinstance(obj, Destroyable):
                    if obj.destroyed:
                        obj.update(self.level.gravity, self.time_scale * time_step, self.colliders)
                        if not obj.debris:
                            del self.level.objects[i]
                elif isinstance(obj, Bullet):
                    if obj.destroyed:
                        obj.update(self.level.gravity, self.time_scale * time_step, self.colliders)
                        if obj.destroyed and not obj.particle_clouds:
                            del self.level.objects[i]

            self.camera.target_position[:] = self.players[self.network_id].position
        elif self.state is State.OPTIONS:
            self.camera.target_position[:] = self.options_menu.position
            self.state = self.options_menu.target_state
            self.options_menu.target_state = State.OPTIONS

            if self.options_menu.options_changed:
                if self.options_menu.buttons[0].get_value() == 'windowed':
                    self.option_handler.fullscreen = False
                else:
                    self.option_handler.fullscreen = True

                self.camera.set_resolution(self.options_menu.buttons[1].get_value())

                self.option_handler.resolution = self.options_menu.buttons[1].get_value()

                self.option_handler.shadows = self.options_menu.buttons[4].get_value() == 'ON'
                self.option_handler.dust = self.options_menu.buttons[5].get_value() == 'ON'

                self.option_handler.save()
        elif self.state is State.PAUSED:
            self.state = self.pause_menu.target_state

            self.pause_menu.set_visible(self.state is State.PAUSED)
            self.text.set_visible(self.state is not State.PAUSED)

            self.pause_menu.target_state = State.PAUSED
        elif self.state is State.CONTROLS:
            self.camera.target_position[:] = self.controls_menu.position
            self.state = self.controls_menu.target_state
            self.controls_menu.target_state = State.CONTROLS

        self.camera.update(time_step)

        if self.state is not old_state:
            self.previous_state = old_state

    def input(self, input_handler):
        input_handler.update(self.camera)

        if self.state is State.SINGLEPLAYER:
            if self.controller_id == 0:
                input_handler.relative_mouse[:] = input_handler.mouse_position - self.players[0].shoulder

            if input_handler.keys_pressed.get(key.R):
                self.reset_game()
                for k, player in self.players.items():
                    if k == 0:
                        continue
                        
                    player.set_position(self.level.player_spawns[k].position)
                self.delay_timer = 0.0

            for i, c in enumerate(input_handler.controllers):
                self.players[0].controller_id = self.controller_id
                self.players[0].input(input_handler)
                if c.button_pressed['START']:
                    self.state = State.PAUSED
                    self.pause_menu.previous_state = State.SINGLEPLAYER
                    self.pause_menu.selection = 0
        elif self.state is State.MULTIPLAYER:
            if 0 in self.players:
                input_handler.relative_mouse[:] = input_handler.mouse_position - self.players[0].shoulder

            for player in self.players.values():
                player.input(input_handler)

            if input_handler.keys_pressed.get(key.R):
                self.reset_game()

            for c in input_handler.controllers:
                if c.button_pressed['START']:
                    self.state = State.PAUSED
                    self.pause_menu.previous_state = State.MULTIPLAYER
                    self.pause_menu.selection = 0
        elif self.state is State.MENU:
            self.menu.input(input_handler)
            for i in range(len(input_handler.controllers)):
                if self.menu.selection_moved[i]:
                    self.controller_id = i
                    self.controller = input_handler.controllers[self.controller_id]
                    break
        elif self.state is State.PLAYER_SELECT:
            for i, controller in enumerate(input_handler.controllers):
                for pm in self.player_menus:
                    if pm.controller_id == i:
                        pm.input(input_handler, i)
                        break
                else:
                    if controller.button_pressed['B']:
                        self.state = State.MENU
                        for p in self.players.values():
                            p.delete()
                        self.players.clear()
                        for pm in self.player_menus:
                            pm.joined = False
                            pm.controller_id = None
                        return

                    for pm in self.player_menus:
                        if pm.controller_id is None:
                            pm.input(input_handler, i)
                        if pm.controller_id == i:
                            self.add_player(i)
                            return
        elif self.state is State.LEVEL_SELECT:
            self.level_menu.input(input_handler)
        elif self.state is State.LAN:
            if self.network is not None:
                player = self.players[self.network_id]

                input_handler.relative_mouse[:] = input_handler.mouse_position - player.shoulder

                self.obj_id = player.object.id if player.object is not None else -1
        elif self.state is State.OPTIONS:
            self.options_menu.input(input_handler)
        elif self.state is State.PAUSED:
            self.pause_menu.input(input_handler)
        elif self.state is State.CONTROLS:
            self.controls_menu.input(input_handler)
        elif self.state is State.CAMPAIGN:
            self.campaign_menu.input(input_handler)

    def draw(self, batch, image_handler):
        self.text.draw(batch, self.camera, image_handler)
        if self.state in {State.SINGLEPLAYER, State.MULTIPLAYER, State.LAN}:
            image_handler.set_clear_color((113, 118, 131))

            if self.level:
                self.level.draw(batch, self.camera, image_handler)
                if self.option_handler.shadows:
                    self.level.draw_shadow(batch, self.camera, image_handler)

            for player in self.players.values():
                player.draw(batch, self.camera, image_handler)
                if self.level and self.option_handler.shadows:
                    player.draw_shadow(batch, self.camera, image_handler, self.level.light)

            if self.option_handler.debug_draw:
                self.debug_draw(batch, image_handler)
        elif self.state is State.PAUSED:
            self.pause_menu.draw(batch, self.camera, image_handler)
        else:
            image_handler.set_clear_color((50, 50, 50))

        if State.MENU in {self.state, self.previous_state}:
            self.menu.draw(batch, self.camera, image_handler)
        if State.OPTIONS in {self.state, self.previous_state}:
            self.options_menu.draw(batch, self.camera, image_handler)
        if State.PLAYER_SELECT in {self.state, self.previous_state}:
            for pm in self.player_menus:
                pm.draw(batch, self.camera, image_handler)
            for p in self.players.values():
                p.draw(batch, self.camera, image_handler)
        if State.LEVEL_SELECT in {self.state, self.previous_state}:
            self.level_menu.draw(batch, self.camera, image_handler)
        if State.CONTROLS in {self.state, self.previous_state}:
            self.controls_menu.draw(batch, self.camera, image_handler)
        if State.CAMPAIGN in {self.state, self.previous_state}:
            self.campaign_menu.draw(batch, self.camera, image_handler)
            for p in self.players.values():
                p.draw(batch, self.camera, image_handler)

        self.camera.draw(batch)

        if self.state is State.PAUSED:
            self.camera.sprite.opacity = 192
        elif self.delay_timer > 0:
            self.camera.sprite.opacity = 128
        else:
            self.camera.sprite.opacity = 0

    def debug_draw(self, batch, image_handler):
        for player in self.players.values():
            player.debug_draw(batch, self.camera, image_handler)

        if self.level:
            self.level.debug_draw(batch, self.camera, image_handler)

    def play_sounds(self, sound_handler):
        if self.state is State.PAUSED:
            sound_handler.pause()
        else:
            sound_handler.play()

        if self.state in {State.MENU, State.PLAYER_SELECT, State.LEVEL_SELECT}:
            sound_handler.set_music(0)

        if self.state in {State.SINGLEPLAYER, State.MULTIPLAYER}:
            for p in self.players.values():
                p.play_sounds(sound_handler)

            if self.level:
                if self.level.background:
                    sound_handler.set_music(1)
                else:
                    sound_handler.pause()
                self.level.play_sounds(sound_handler)
        elif self.state is State.OPTIONS:
            sound_handler.set_volume(self.options_menu.buttons[2].get_value())
            sound_handler.set_music_volume(self.options_menu.buttons[3].get_value())

            self.option_handler.sfx_volume = self.options_menu.buttons[2].get_value()
            self.option_handler.music_volume = self.options_menu.buttons[3].get_value()
            self.option_handler.save()
        else:
            for pm in self.player_menus:
                pm.play_sounds(sound_handler)
            self.controls_menu.play_sounds(sound_handler)

        self.menu.play_sounds(sound_handler)
        self.options_menu.play_sounds(sound_handler)
        self.level_menu.play_sounds(sound_handler)
        self.pause_menu.play_sounds(sound_handler)
        self.campaign_menu.play_sounds(sound_handler)

    def network_thread(self):
        while True:
            data = self.controller.get_data()

            data = self.network.send(data)

            for p in data[0]:
                if p[0] not in self.players:
                    self.add_player(-1, p[0])

                self.players[p[0]].apply_data(p)

            # kinda purkka
            ids = [p[0] for p in data[0]]
            for k in list(self.players.keys()):
                if k != self.network_id and k not in ids:
                    del self.players[k]

            for d in data[1]:
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
                if i not in ids:
                    if isinstance(obj, Destroyable):
                        obj.destroy(self.colliders)
                    elif isinstance(obj, Bullet):
                        obj.destroy()
