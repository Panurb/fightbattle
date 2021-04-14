import os
from enum import Enum
import pickle

import numpy as np

from button import Button, Slider, RebindButton
from helpers import basis
from text import Text, TitleText


class State(Enum):
    QUIT = 1
    MULTIPLAYER = 2
    MENU = 3
    PLAYER_SELECT = 4
    LEVEL_SELECT = 5
    PAUSED = 6
    OPTIONS = 7
    LAN = 8
    CONTROLS = 9
    SINGLEPLAYER = 10
    CAMPAIGN = 11
    CREDITS = 12


class Menu:
    def __init__(self, position=(0, 0)):
        self.position = np.array(position, dtype=float)
        self.buttons = []
        self.target_state = State.MENU
        self.selection = 0
        self.selection_moved = dict()
        self.slider_moved = dict()
        self.sounds = set()
        self.previous_state = State.MENU
        self.visible = True
        self.button_offset = 0.0
        self.button_gap = 1.5

    def set_visible(self, visible):
        for b in self.buttons:
            b.set_visible(visible)

    def delete(self):
        for b in self.buttons:
            b.delete()

    def update_buttons(self):
        for i, b in enumerate(self.buttons):
            b.set_position(self.position + (0.5 * len(self.buttons)
                                            + self.button_offset - self.button_gap * i) * basis(1))

    def input(self, input_handler, controller_id=0):
        controller = input_handler.controllers[controller_id]

        if controller_id == 0:
            for i, b in enumerate(self.buttons):
                if b.collider.point_inside(input_handler.mouse_position):
                    if self.selection is not i:
                        self.sounds.add('menu')
                    self.selection = i
                    self.selection_moved[controller_id] = True

                    if type(b) is Button:
                        if input_handler.mouse_released[1]:
                            self.target_state = self.buttons[self.selection].target_state
                            self.sounds.add('select')
                    elif type(b) is Slider:
                        if input_handler.mouse_pressed[1]:
                            b.move_right()
                            self.sounds.add('menu')
                        elif input_handler.mouse_pressed[4]:
                            b.move_left()
                            self.sounds.add('menu')

                    break
            else:
                self.selection_moved[controller_id] = False
        else:
            if controller_id not in self.selection_moved:
                self.selection_moved[controller_id] = False

            if controller.left_stick[1] < -0.5:
                if not self.selection_moved[controller_id]:
                    self.sounds.add('menu')
                    self.selection = (self.selection + 1) % len(self.buttons)
                    self.selection_moved[controller_id] = True
            elif controller.left_stick[1] > 0.5:
                if not self.selection_moved[controller_id]:
                    self.sounds.add('menu')
                    self.selection = (self.selection - 1) % len(self.buttons)
                    self.selection_moved[controller_id] = True
            else:
                self.selection_moved[controller_id] = False

            if type(self.buttons[self.selection]) is Slider:
                if controller.left_stick[0] < -0.5:
                    if not self.slider_moved[controller_id]:
                        self.buttons[self.selection].move_left()
                        self.slider_moved[controller_id] = True
                        self.sounds.add('menu')
                elif controller.left_stick[0] > 0.5:
                    if not self.slider_moved[controller_id]:
                        self.buttons[self.selection].move_right()
                        self.slider_moved[controller_id] = True
                        self.sounds.add('menu')
                else:
                    self.slider_moved[controller_id] = False

        if controller.button_pressed['A']:
            if type(self.buttons[self.selection]) is Button:
                self.target_state = self.buttons[self.selection].target_state
                self.sounds.add('select')

        if controller.button_pressed['B']:
            self.target_state = self.previous_state
            self.sounds.add('cancel')

        for i, b in enumerate(self.buttons):
            b.selected = True if i == self.selection else False

    def draw(self, batch, camera, image_handler):
        for b in self.buttons:
            b.visible = self.visible
            b.draw(batch, camera, image_handler)

    def play_sounds(self, sound_handler):
        for sound in self.sounds:
            player = sound_handler.sounds[sound].play()
            player.volume = sound_handler.volume

        self.sounds.clear()


class MainMenu(Menu):
    def __init__(self):
        super().__init__()
        self.button_offset = -1.5
        self.buttons.append(Button('SINGLEPLAYER', State.CAMPAIGN))
        self.buttons.append(Button('MULTIPLAYER', State.PLAYER_SELECT))
        #self.buttons.append(Button('LAN', State.LAN))
        self.buttons.append(Button('OPTIONS', State.OPTIONS))
        self.buttons.append(Button('CREDITS', State.CREDITS))
        self.buttons.append(Button('QUIT', State.QUIT))
        self.update_buttons()
        self.timer = 40.0
        self.chromatic_aberration = 0
        self.title = TitleText('FIGHTBATTLE', np.array([0, 4.5]), 2.2, 'CollegiateBlackFLF')

    def set_visible(self, visible):
        super().set_visible(visible)
        self.title.set_visible(visible)

    def update(self, time_step):
        self.chromatic_aberration = max(0, self.chromatic_aberration - 5 * time_step)

    def input(self, input_handler, controller_id=0):
        selection = self.selection
        for i in range(len(input_handler.controllers)):
            super().input(input_handler, i)

        if self.selection != selection:
            self.sounds.add('static')
            self.chromatic_aberration = 2

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        self.title.chromatic_aberration = self.chromatic_aberration
        self.title.draw(batch, camera, image_handler)


class PlayerMenu(Menu):
    def __init__(self, position):
        super().__init__(position)
        self.target_state = State.PLAYER_SELECT
        self.controller_id = None
        self.button_offset = -2

        path = os.path.join('data', 'images', 'heads')
        heads = [x.split('.')[0] for x in os.listdir(path)]
        self.head_slider = Slider('Head', heads)
        self.buttons.append(self.head_slider)

        path = os.path.join('data', 'images', 'bodies')
        bodies = [x.split('.')[0] for x in os.listdir(path)]
        self.body_slider = Slider('Body', bodies)
        self.buttons.append(self.body_slider)

        self.team_slider = Slider('Team', ['blue', 'red'], False)
        self.buttons.append(self.team_slider)
        self.buttons.append(Button('Ready up', State.MULTIPLAYER))

        self.update_buttons()
        self.start_text = Text('Press (START) to join', self.buttons[0].position, 0.45)
        self.ready_text = Text('READY', self.buttons[0].position, 0.45)

        self.joined = False
        self.ready = False

    def delete(self):
        super().delete()
        self.text.delete()

    def input(self, input_handler, controller_id=0):
        if self.controller_id is None:
            if input_handler.controllers[controller_id].button_pressed['START']:
                self.controller_id = controller_id
                self.sounds.add('select')
                self.joined = True
                self.selection = 0
                self.head_slider.randomize()
                self.body_slider.randomize()

            if controller_id == 0:
                if self.buttons[0].collider.point_inside(input_handler.mouse_position):
                    if input_handler.mouse_pressed[1]:
                        self.controller_id = 0
                        self.sounds.add('select')
                        self.joined = True
                        self.head_slider.randomize()
                        self.body_slider.randomize()
        else:
            if input_handler.controllers[controller_id].button_pressed['B']:
                if self.ready:
                    self.sounds.add('cancel')
                    self.ready = False
                    self.target_state = State.PLAYER_SELECT
                else:
                    self.sounds.add('cancel')
                    self.joined = False
            else:
                super().input(input_handler, self.controller_id)
                if self.target_state is State.MULTIPLAYER:
                    self.ready = True
                    self.target_state = State.PLAYER_SELECT

    def draw(self, batch, camera, image_handler):
        if not self.joined:
            self.start_text.visible = True
            self.ready_text.visible = False
            self.visible = False
        elif self.ready:
            self.start_text.visible = False
            self.ready_text.visible = True
            self.visible = False
        else:
            self.start_text.visible = False
            self.ready_text.visible = False
            self.visible = True

        super().draw(batch, camera, image_handler)
        self.start_text.draw(batch, camera, image_handler)
        self.ready_text.draw(batch, camera, image_handler)


class OptionsMenu(Menu):
    def __init__(self):
        super().__init__()
        self.position[0] = 25
        self.position[1] = 0
        self.target_state = State.OPTIONS
        self.buttons.append(Slider('Mode', ['windowed', 'fullscreen']))
        self.buttons.append(Slider('Resolution', [(1280, 720), (1360, 768), (1366, 768), (1600, 900), (1920, 1080),
                                                  (2560, 1440), (3840, 2160)], False))
        self.buttons.append(Slider('SFX volume', range(0, 110, 10), False))
        self.buttons.append(Slider('Music volume', range(0, 110, 10), False))
        self.buttons.append(Slider('Shadows', ['OFF', 'ON']))
        self.buttons.append(Slider('Dust', ['OFF', 'ON']))
        self.buttons.append(Button('CONTROLS', State.CONTROLS))
        self.update_buttons()
        self.options_changed = False

        self.button_back = Button('(B) back', self.target_state)
        self.button_back.set_position(self.position + np.array([-10, -6]))

        self.button_apply = Button('(A) apply', self.target_state)
        self.button_apply.set_position(self.position + np.array([10, -6]))

    def set_values(self, option_handler):
        self.buttons[0].selection = 1 if option_handler.fullscreen else 0
        self.buttons[1].selection = self.buttons[1].values.index(option_handler.resolution)
        self.buttons[2].selection = self.buttons[2].values.index(option_handler.sfx_volume)
        self.buttons[3].selection = self.buttons[3].values.index(option_handler.music_volume)
        self.buttons[4].selection = 1 if option_handler.shadows else 0
        self.buttons[5].selection = 1 if option_handler.dust else 0

    def input(self, input_handler, controller_id=0):
        for i in range(len(input_handler.controllers)):
            controller = input_handler.controllers[i]
            if controller.button_pressed['A']:
                self.options_changed = True
                self.sounds.add('select')
            if controller.button_pressed['B']:
                self.target_state = State.MENU
                self.sounds.add('cancel')
                return

            super().input(input_handler, i)

    def draw(self, screen, camera, image_handler):
        super().draw(screen, camera, image_handler)
        self.button_back.draw(screen, camera, image_handler)
        self.button_apply.draw(screen, camera, image_handler)


class PauseMenu(Menu):
    def __init__(self):
        super().__init__()
        self.target_state = State.PAUSED
        self.buttons.append(Button('Resume', State.MULTIPLAYER))
        self.buttons.append(Button('Quit', State.LEVEL_SELECT))
        self.update_buttons()
        self.previous_state = State.MULTIPLAYER

    def input(self, input_handler, controller_id=0):
        self.buttons[0].target_state = self.previous_state
        if self.previous_state is State.SINGLEPLAYER:
            self.buttons[1].target_state = State.CAMPAIGN
        else:
            self.buttons[1].target_state = State.LEVEL_SELECT
        for i in range(len(input_handler.controllers)):
            super().input(input_handler, i)

    def draw(self, screen, camera, image_handler):
        self.position[:] = camera.position
        self.update_buttons()
        for b in self.buttons:
            b.text.size = 0.45 * camera.max_zoom / camera.zoom
        super().draw(screen, camera, image_handler)


class LevelMenu(Menu):
    def __init__(self):
        super().__init__([25, -16])
        path = os.path.join('data', 'levels', 'multiplayer')
        levels = [x.split('.')[0] for x in os.listdir(path)]
        self.level_slider = Slider('Level', levels, cyclic=False)
        self.buttons.append(self.level_slider)
        self.score_slider = Slider('Score limit', range(1, 11), cyclic=False, selection=2)
        self.buttons.append(self.score_slider)
        self.buttons.append(Button('Start', State.MULTIPLAYER))
        self.update_buttons()
        self.target_state = State.LEVEL_SELECT
        self.previous_state = State.PLAYER_SELECT

    def input(self, input_handler, controller_id=0):
        for i in range(len(input_handler.controllers)):
            super().input(input_handler, i)


class CampaignMenu(Menu):
    def __init__(self):
        super().__init__([-25, 0])
        self.target_state = State.CAMPAIGN
        self.previous_state = State.MENU
        self.button_offset = -2

        path = os.path.join('data', 'images', 'heads')
        heads = [x.split('.')[0] for x in os.listdir(path)]
        self.head_slider = Slider('Head', heads)
        self.buttons.append(self.head_slider)

        path = os.path.join('data', 'images', 'bodies')
        bodies = [x.split('.')[0] for x in os.listdir(path)]
        self.body_slider = Slider('Body', bodies)
        self.buttons.append(self.body_slider)

        levels = ['prologue', 'level1', 'level2', 'level3', 'level4', 'level5', 'level6', 'level7']
        self.level_slider = Slider('Level', levels, cyclic=False)
        self.buttons.append(self.level_slider)
        self.times = {l: np.inf for l in levels}

        self.buttons.append(Button('Start', State.SINGLEPLAYER))

        self.update_buttons()

        self.time_text = Text('-', self.level_slider.position - 0.65 * basis(1), 0.45, color=(150, 150, 150))

        self.load()

    def load(self):
        try:
            with open('save.pickle', 'rb') as f:
                data = pickle.load(f)
                for l, t in data[0].items():
                    self.times[l] = t
                self.body_slider.selection = data[1]
                self.head_slider.selection = data[2]
        except FileNotFoundError:
            pass

    def save(self):
        with open('save.pickle', 'wb') as f:
            data = [self.times, self.body_slider.selection, self.head_slider.selection]
            pickle.dump(data, f)

    def set_visible(self, visible):
        super().set_visible(visible)
        self.time_text.set_visible(visible)

    def input(self, input_handler, controller_id=0):
        for i in range(len(input_handler.controllers)):
            super().input(input_handler, i)

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        val = self.times[self.level_slider.get_value()]
        self.time_text.string = '-' if np.isinf(val) else f'{val:.2f}'
        self.time_text.visible = self.level_slider.get_value() not in ['prologue']
        self.time_text.draw(batch, camera, image_handler)


class ControlsMenu(Menu):
    def __init__(self):
        super().__init__([50, 0])
        self.target_state = State.CONTROLS
        self.previous_state = State.OPTIONS
        self.button_gap = 1.0

        self.text = []
        self.text.append(Text('(L)     move ', self.position + np.array([0, 5]), 0.45))
        self.text.append(Text('(R)     aim  ', self.position + np.array([0, 4]), 0.45))
        self.text.append(Text('(A)     jump ', self.position + np.array([0, 3]), 0.45))
        self.text.append(Text('(X)     run  ', self.position + np.array([0, 2]), 0.45))
        self.text.append(Text('(B)    cancel', self.position + np.array([0, 1]), 0.45))
        self.text.append(Text('(RT)    attack', self.position + np.array([0, 0]), 0.45))
        self.text.append(Text('(LT)    throw ', self.position + np.array([0, -1]), 0.45))
        self.text.append(Text('(START)   pause ', self.position + np.array([0, -2]), 0.45))

        self.buttons.append(Button('(B) back', self.target_state))
        self.buttons[0].set_position(self.position + np.array([-10, -6]))

    def input(self, input_handler, controller_id=0):
        for i in range(len(input_handler.controllers)):
            super().input(input_handler, i)

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        for text in self.text:
            text.draw(batch, camera, image_handler)


class CreditsMenu(Menu):
    def __init__(self):
        super().__init__([0, 10])
        self.target_state = State.CREDITS
        self.text = []
        self.text.append(Text('Programming, art, music', self.position + np.array([0, 6]), 0.5, None))
        self.text.append(Text('Panu Keskinen', self.position + np.array([0, 5]), 0.4, None))

        self.text.append(Text('Made with', self.position + np.array([0, 3]), 0.5, None))
        self.text.append(Text('Python', self.position + np.array([0, 2]), 0.4, None))
        self.text.append(Text('Inkscape', self.position + np.array([0, 1]), 0.4, None))
        self.text.append(Text('Ableton Live Lite', self.position + np.array([0, 0]), 0.4, None))
        self.text.append(Text('Audacity', self.position + np.array([0, -1]), 0.4, None))

        self.buttons.append(Button('(B) back', self.target_state))

        self.buttons[0].set_position(self.position + np.array([-10, 6]))

    def input(self, input_handler, controller_id=0):
        for i in range(len(input_handler.controllers)):
            super().input(input_handler, i)

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        for text in self.text:
            text.draw(batch, camera, image_handler)
