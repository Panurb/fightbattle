from enum import Enum

import numpy as np
import pygame

from collider import Rectangle
from gameobject import GameObject
from helpers import basis


class State(Enum):
    QUIT = 1
    PLAY = 2
    MENU = 3
    PLAYER_SELECT = 4
    LEVEL_SELECT = 5
    PAUSED = 6
    OPTIONS = 7
    LAN = 8


class Menu:
    def __init__(self):
        self.position = np.zeros(2)
        self.buttons = []
        self.target_state = State.MENU
        self.selection = 0
        self.selection_moved = dict()
        self.slider_moved = dict()
        self.sounds = []

    def update_buttons(self):
        for i, b in enumerate(self.buttons):
            b.set_position(self.position - 1.5 * i * basis(1))

    def input(self, input_handler, controller_id=0):
        controller = input_handler.controllers[controller_id]

        if controller_id == 0:
            for i, b in enumerate(self.buttons):
                if b.collider.point_inside(input_handler.mouse_position):
                    if self.selection is not i:
                        self.sounds.append('menu')
                    self.selection = i
                    self.selection_moved[controller_id] = True

                    if type(b) is Button:
                        if input_handler.mouse_pressed[0]:
                            self.target_state = self.buttons[self.selection].target_state
                            self.sounds.append('select')
                    elif type(b) is Slider:
                        if input_handler.mouse_pressed[0]:
                            b.move_right()
                            self.sounds.append('menu')
                        elif input_handler.mouse_pressed[2]:
                            b.move_left()
                            self.sounds.append('menu')

                    break
            else:
                self.selection_moved[controller_id] = False
        else:
            if controller_id not in self.selection_moved:
                self.selection_moved[controller_id] = False

            if controller.left_stick[1] < -0.5:
                if not self.selection_moved[controller_id]:
                    self.sounds.append('menu')
                    self.selection = (self.selection + 1) % len(self.buttons)
                    self.selection_moved[controller_id] = True
            elif controller.left_stick[1] > 0.5:
                if not self.selection_moved[controller_id]:
                    self.sounds.append('menu')
                    self.selection = (self.selection - 1) % len(self.buttons)
                    self.selection_moved[controller_id] = True
            else:
                self.selection_moved[controller_id] = False

            if type(self.buttons[self.selection]) is Slider:
                if controller.left_stick[0] < -0.5:
                    if not self.slider_moved[controller_id]:
                        self.buttons[self.selection].move_left()
                        self.slider_moved[controller_id] = True
                        self.sounds.append('menu')
                elif controller.left_stick[0] > 0.5:
                    if not self.slider_moved[controller_id]:
                        self.buttons[self.selection].move_right()
                        self.slider_moved[controller_id] = True
                        self.sounds.append('menu')
                else:
                    self.slider_moved[controller_id] = False

            if controller.button_pressed['A']:
                if type(self.buttons[self.selection]) is Button:
                    self.target_state = self.buttons[self.selection].target_state
                    self.sounds.append('select')

            if controller.button_pressed['B']:
                self.target_state = State.MENU
                self.sounds.append('cancel')

        for i, b in enumerate(self.buttons):
            b.selected = True if i == self.selection else False

    def draw(self, screen, camera, image_handler):
        for b in self.buttons:
            b.draw(screen, camera, image_handler)

    def play_sounds(self, sound_handler):
        for sound in self.sounds:
            sound_handler.sounds[sound].play()

        self.sounds.clear()


class Button(GameObject):
    def __init__(self, text, target_state):
        super().__init__([0, 0])
        self.add_collider(Rectangle([0, 0], 3, 1))
        self.text = text
        self.target_state = target_state
        self.color = (150, 150, 150)
        self.color_selected = (255, 255, 255)
        self.selected = False

    def draw(self, screen, camera, image_handler):
        color = self.color_selected if self.selected else self.color
        camera.draw_text(screen, self.text, self.position, 0.75, color=color, chromatic_aberration=self.selected)


class Slider(GameObject):
    def __init__(self, text, values, cyclic=True, selection=0):
        super().__init__([0, 0])
        self.add_collider(Rectangle([0, 0], 3, 1))
        self.text = text
        self.color = (150, 150, 150)
        self.color_selected = (255, 255, 255)
        self.selected = False
        self.selection = selection
        self.values = values
        self.cyclic = cyclic

    def get_value(self):
        return self.values[self.selection]

    def move_right(self):
        if self.cyclic:
            self.selection = (self.selection + 1) % len(self.values)
        else:
            self.selection = min(self.selection + 1, len(self.values) - 1)

    def move_left(self):
        if self.cyclic:
            self.selection = (self.selection - 1) % len(self.values)
        else:
            self.selection = max(self.selection - 1, 0)

    def draw(self, screen, camera, image_handler):
        color = self.color_selected if self.selected else self.color
        camera.draw_text(screen, self.text, self.position + 0.63 * basis(1), 0.75, color=color,
                         chromatic_aberration=self.selected)

        val_str = str(self.values[self.selection]).replace(', ', 'x').strip('()')
        camera.draw_text(screen, val_str, self.position, 0.75, color=color,
                         chromatic_aberration=self.selected)

        if self.selected:
            if self.cyclic or self.selection > 0:
                camera.draw_triangle(screen, self.position - 1.5 * basis(0), 0.75, chromatic_aberration=True)
            if self.cyclic or self.selection < len(self.values) - 1:
                camera.draw_triangle(screen, self.position + 1.5 * basis(0), 0.75, np.pi, chromatic_aberration=True)


class MainMenu(Menu):
    def __init__(self):
        super().__init__()
        self.buttons.append(Button('PLAY', State.PLAYER_SELECT))
        self.buttons.append(Button('LAN', State.LAN))
        self.buttons.append(Button('OPTIONS', State.OPTIONS))
        self.buttons.append(Button('QUIT', State.QUIT))
        self.update_buttons()
        self.timer = 40.0
        self.chromatic_aberration = False

    def update(self, time_step):
        self.timer -= time_step

        if self.timer <= 0:
            if self.chromatic_aberration:
                self.timer = 40 * np.random.random()
            else:
                self.timer = 5
                self.sounds.append('static')
            self.chromatic_aberration = not self.chromatic_aberration

    def input(self, input_handler, controller_id=0):
        for i in range(len(input_handler.controllers)):
            super().input(input_handler, i)

    def draw(self, screen, camera, image_handler):
        super().draw(screen, camera, image_handler)
        camera.draw_text(screen, 'FIGHTBATTLE', np.array([0, 3.5]), 3.2, 'CollegiateBlackFLF.ttf',
                         chromatic_aberration=self.chromatic_aberration)


class PlayerMenu(Menu):
    def __init__(self, position):
        super().__init__()
        self.target_state = State.PLAYER_SELECT
        self.position = np.array(position, dtype=float)
        self.controller_id = None

        self.buttons.append(Slider('Head', ['bald', 'goggles', 'clown']))
        self.buttons.append(Slider('Body', ['camo', 'suit', 'speedo', 'sporty']))
        self.buttons.append(Slider('Team', ['solo']))
        self.buttons.append(Button('Ready up', State.PLAY))

        self.update_buttons()

    def input(self, input_handler, controller_id=0):
        if self.controller_id is None:
            if input_handler.controllers[controller_id].button_pressed['START']:
                self.controller_id = controller_id
                self.sounds.append('select')

            if self.buttons[0].collider.point_inside(input_handler.mouse_position):
                if input_handler.mouse_pressed[1]:
                    self.controller_id = 0
                    self.target_state = State.PLAY
        else:
            if input_handler.controllers[controller_id].button_pressed['B']:
                if self.target_state is State.PLAY:
                    self.target_state = State.PLAYER_SELECT
                else:
                    self.controller_id = None
            else:
                super().input(input_handler, self.controller_id)

    def draw(self, screen, camera, image_handler):
        if self.controller_id is None:
            camera.draw_text(screen, 'Press START to join', self.buttons[0].position, 0.75, chromatic_aberration=True)
        elif self.target_state is State.PLAY:
            camera.draw_text(screen, 'READY', self.buttons[0].position, 0.75, chromatic_aberration=True)
        else:
            super().draw(screen, camera, image_handler)


class OptionsMenu(Menu):
    def __init__(self):
        super().__init__()
        self.position[1] = 3
        self.target_state = State.OPTIONS
        self.buttons.append(Slider('Mode', ['windowed', 'fullscreen']))
        self.buttons.append(Slider('Resolution', [(1280, 720), (1600, 900), (1920, 1080)], False))
        self.buttons.append(Slider('SFX volume', range(0, 110, 10), False))
        self.buttons.append(Slider('Music volume', range(0, 110, 10), False))
        self.buttons.append(Slider('Shadows', ['OFF', 'ON']))
        self.update_buttons()
        self.options_changed = False

        self.button_back = Button('(B) back', self.target_state)
        self.button_back.set_position(np.array([-10, -5]))

        self.button_apply = Button('(A) apply', self.target_state)
        self.button_apply.set_position(np.array([10, -5]))

    def set_values(self, option_handler):
        self.buttons[0].selection = 1 if option_handler.fullscreen else 0
        self.buttons[1].selection = self.buttons[1].values.index(option_handler.resolution)
        self.buttons[2].selection = self.buttons[2].values.index(option_handler.sfx_volume)
        self.buttons[3].selection = self.buttons[3].values.index(option_handler.music_volume)
        self.buttons[4].selection = 1 if option_handler.shadows else 0

    def input(self, input_handler, controller_id=0):
        for i in range(len(input_handler.controllers)):
            controller = input_handler.controllers[i]
            if controller.button_pressed['A']:
                self.options_changed = True
                self.sounds.append('select')
            if controller.button_pressed['B']:
                self.target_state = State.MENU
                self.sounds.append('cancel')
                return

            super().input(input_handler, i)

    def draw(self, screen, camera, image_handler):
        super().draw(screen, camera, image_handler)
        self.button_back.draw(screen, camera, image_handler)
        self.button_apply.draw(screen, camera, image_handler)
