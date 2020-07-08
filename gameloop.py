from _thread import *

import numpy as np
from pyglet.window import key

from camera import Camera
from gameobject import Destroyable
from helpers import basis
from level import Level
from menu import State, PlayerMenu, MainMenu, OptionsMenu, PauseMenu, LevelMenu, ControlsMenu
from player import Player
from network import Network
from prop import Ball
from text import Text
from weapon import Bullet


class GameLoop:
    def __init__(self, option_handler):
        self.option_handler = option_handler
        self.state = State.MENU

        self.level = None
        self.players = dict()
        self.colliders = []

        self.time_scale = 1.0

        self.camera = Camera([0, 0], self.option_handler.resolution)

        self.respawn_time = 50.0

        self.menu = MainMenu()
        self.player_menus = [PlayerMenu(np.array([6 * i - 9, -16])) for i in range(4)]
        self.options_menu = OptionsMenu()
        self.options_menu.set_values(self.option_handler)
        self.pause_menu = PauseMenu()
        self.level_menu = LevelMenu()
        self.controls_menu = ControlsMenu()

        self.network = None
        self.network_id = -1
        self.obj_id = -1

        self.controller_id = 0

        self.score_limit = 0
        self.text = Text('', np.zeros(2), 2.0)
        self.timer = 0.0
        self.delay = 0.0

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
            p.reset(self.colliders)
            p.set_spawn(self.level, self.players)
            p.collider.update_occupied_squares(self.colliders)

        self.timer = self.delay

    def reset_game(self):
        for o in self.level.objects.values():
            if o.collider:
                o.collider.clear_occupied_squares(self.colliders)

        self.level.reset()

        for p in self.players.values():
            p.reset(self.colliders)
            p.set_spawn(self.level, self.players)

        self.timer = self.delay
        self.time_scale = 1.0

        zoom = min(self.camera.resolution[0] / self.level.width, self.camera.resolution[1] / self.level.height)
        self.camera.set_position_zoom(0.5 * np.array([self.level.width, self.level.height]), zoom)

    def add_player(self, controller_id, network_id=-1):
        if network_id == -1:
            network_id = controller_id
        player = Player([0, 0], controller_id, network_id)
        self.players[network_id] = player

    def update(self, time_step):
        if self.state is State.PLAY:
            if not self.level:
                self.load_level(self.level_menu.level_slider.get_value())
                self.level_menu.set_visible(False)
                self.score_limit = int(self.level_menu.score_slider.get_value())
                zoom = min(self.camera.resolution[0] / self.level.width, self.camera.resolution[1] / self.level.height)
                self.camera.set_position_zoom(0.5 * np.array([self.level.width, self.level.height]), zoom)

            self.text.position[:] = self.camera.position

            if self.timer > 0:
                if self.level.background:
                    self.timer -= time_step
                    if not self.text.string:
                        self.text.string = 'GET READY'
                        self.time_scale = 0.0
            else:
                self.timer = 0.0
                if 'SCORES' in self.text.string:
                    self.reset_game()
                elif 'WINS' in self.text.string:
                    self.state = State.LEVEL_SELECT
                    for p in self.players.values():
                        p.reset(self.colliders)
                    self.level.delete()
                    self.level = None

                    self.timer = 0
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

            if self.timer == 0:
                if len(self.players) > 1:
                    if not any(alive.values()):
                        self.reset_game()
                    elif alive['red'] and not alive['blue']:
                        self.level.scoreboard.scores['red'] += 1
                        self.text.string = 'RED SCORES'
                        self.time_scale = 0.5
                        self.timer = self.delay
                    elif alive['blue'] and not alive['red']:
                        self.level.scoreboard.scores['blue'] += 1
                        self.text.string = 'BLUE SCORES'
                        self.time_scale = 0.5
                        self.timer = self.delay

                for team, score in self.level.scoreboard.scores.items():
                    if score == self.score_limit:
                        self.text.string = f'{team} wins'.upper()
                        self.time_scale = 0.5
                        self.timer = 2 * self.delay
                        break
                else:
                    for o in self.level.objects.values():
                        if type(o) is Ball and o.scored:
                            self.text.string = f'{o.scored} scores'.upper()
                            self.time_scale = 0.5
                            self.timer = self.delay

                self.camera.set_target(self.players, self.level)
                self.text.position[:] = self.camera.position
        elif self.state is State.MENU:
            self.camera.target_position[:] = self.menu.position
            self.menu.update(time_step)
            self.state = self.menu.target_state
            self.menu.target_state = State.MENU

            if self.state is State.OPTIONS:
                self.option_handler.load()
                self.options_menu.set_values(self.option_handler)
        elif self.state is State.PLAYER_SELECT:
            self.camera.target_position[:] = 0.5 * (self.player_menus[0].position + self.player_menus[-1].position)

            for pm in self.player_menus:
                if pm.joined:
                    self.players[pm.controller_id].body_type = pm.body_slider.get_value()
                    self.players[pm.controller_id].head_type = pm.head_slider.get_value()
                    self.players[pm.controller_id].team = pm.team_slider.get_value()
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

            player = self.players[self.network_id]
            player.update(self.level.gravity, self.time_scale * time_step, self.colliders)

            if player.object:
                player.object.update(self.level.gravity, self.time_scale * time_step, self.colliders)

            for i, obj in self.level.objects.items():
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

            self.camera.target_position[:] = player.position
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

            if self.state is State.LEVEL_SELECT:
                for p in self.players.values():
                    p.reset(self.colliders)
                self.level.delete()
                self.level = None

                self.timer = 0
                self.text.string = ''
                self.camera.set_position_zoom(self.level_menu.position, self.camera.max_zoom)

            self.pause_menu.target_state = State.PAUSED
        elif self.state is State.CONTROLS:
            self.camera.target_position[:] = self.controls_menu.position
            self.state = self.controls_menu.target_state
            self.controls_menu.target_state = State.CONTROLS

        self.camera.update(time_step)

    def input(self, input_handler):
        input_handler.update(self.camera)

        if self.state is State.PLAY:
            if 0 in self.players:
                input_handler.relative_mouse[:] = input_handler.mouse_position - self.players[0].shoulder

            for player in self.players.values():
                player.input(input_handler)

            if input_handler.keys_pressed.get(key.R):
                self.reset_game()

            for c in input_handler.controllers:
                if c.button_pressed['START']:
                    self.state = State.PAUSED
                    self.pause_menu.selection = 0
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

                player.input(input_handler)
        elif self.state is State.OPTIONS:
            self.options_menu.input(input_handler)
        elif self.state is State.PAUSED:
            self.pause_menu.input(input_handler)
        elif self.state is State.CONTROLS:
            self.controls_menu.input(input_handler)

    def draw(self, batch, image_handler):
        self.text.draw(batch, self.camera)
        if self.state in {State.PLAY, State.LAN}:
            image_handler.set_clear_color((113, 118, 131))

            if self.option_handler.shadows:
                if self.level:
                    self.level.draw_shadow(batch, self.camera, image_handler)
                    for p in self.players.values():
                        p.draw_shadow(batch, self.camera, image_handler, self.level.light)

            if self.level:
                self.level.draw(batch, self.camera, image_handler)

            for player in self.players.values():
                player.draw(batch, self.camera, image_handler)

            if self.option_handler.debug_draw:
                self.debug_draw(batch, image_handler)
        elif self.state in {State.MENU, State.OPTIONS, State.PLAYER_SELECT, State.LEVEL_SELECT, State.CONTROLS}:
            image_handler.set_clear_color((50, 50, 50))

            self.menu.draw(batch, self.camera, image_handler)
            self.options_menu.draw(batch, self.camera, image_handler)
            for pm in self.player_menus:
                pm.draw(batch, self.camera, image_handler)
                if pm.controller_id in self.players:
                    self.players[pm.controller_id].set_position(pm.position + 3 * basis(1))
                    self.players[pm.controller_id].on_ground = True
                    self.players[pm.controller_id].animate(0.0)
                    self.players[pm.controller_id].draw(batch, self.camera, image_handler)
            self.level_menu.draw(batch, self.camera, image_handler)
            self.controls_menu.draw(batch, self.camera, image_handler)
        elif self.state is State.PAUSED:
            self.pause_menu.draw(batch, self.camera, image_handler)

        self.camera.draw(batch)

        if self.state is State.PAUSED:
            self.camera.sprite.opacity = 192
        elif self.timer > 0:
            self.camera.sprite.opacity = 128
        else:
            self.camera.sprite.opacity = 0

    def debug_draw(self, screen, image_handler):
        for player in self.players.values():
            player.debug_draw(screen, self.camera, image_handler)

        #self.level.debug_draw(screen, self.camera, image_handler)

    def play_sounds(self, sound_handler):
        if self.state is State.PAUSED:
            sound_handler.pause()
        else:
            sound_handler.play()

        if self.state in {State.MENU, State.PLAYER_SELECT, State.LEVEL_SELECT}:
            sound_handler.set_music(0)

        if self.state in {State.PLAY, State.LAN}:
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

            self.menu.play_sounds(sound_handler)
            self.options_menu.play_sounds(sound_handler)
        else:
            self.menu.play_sounds(sound_handler)
            self.options_menu.play_sounds(sound_handler)
            for pm in self.player_menus:
                pm.play_sounds(sound_handler)
            self.level_menu.play_sounds(sound_handler)
            self.controls_menu.play_sounds(sound_handler)
        self.pause_menu.play_sounds(sound_handler)

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
            for k in self.players.keys():
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
