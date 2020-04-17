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

    def update_buttons(self):
        for i, b in enumerate(self.buttons):
            b.set_position(self.position - 1.5 * i * basis(1))

    def input(self, input_handler, controller_id=0):
        controller = input_handler.controllers[controller_id]

        if controller_id == 0:
            for i, b in enumerate(self.buttons):
                if b.collider.point_inside(input_handler.mouse_position):
                    self.selection = i
                    self.selection_moved[controller_id] = True

                    if type(b) is Button:
                        if input_handler.mouse_pressed[0]:
                            self.target_state = self.buttons[self.selection].target_state
                    elif type(b) is Slider:
                        if input_handler.mouse_pressed[0]:
                            b.move_right()
                        elif input_handler.mouse_pressed[2]:
                            b.move_left()

                    break
            else:
                self.selection_moved[controller_id] = False
        else:
            if controller_id not in self.selection_moved:
                self.selection_moved[controller_id] = False

            if controller.left_stick[1] < -0.5:
                if not self.selection_moved[controller_id]:
                    self.selection = (self.selection + 1) % len(self.buttons)
                    self.selection_moved[controller_id] = True
            elif controller.left_stick[1] > 0.5:
                if not self.selection_moved[controller_id]:
                    self.selection = (self.selection - 1) % len(self.buttons)
                    self.selection_moved[controller_id] = True
            else:
                self.selection_moved[controller_id] = False

            if type(self.buttons[self.selection]) is Slider:
                if controller.left_stick[0] < -0.5:
                    if not self.slider_moved[controller_id]:
                        self.buttons[self.selection].move_left()
                        self.slider_moved[controller_id] = True
                elif controller.left_stick[0] > 0.5:
                    if not self.slider_moved[controller_id]:
                        self.buttons[self.selection].move_right()
                        self.slider_moved[controller_id] = True
                else:
                    self.slider_moved[controller_id] = False

            if controller.button_pressed['A']:
                if type(self.buttons[self.selection]) is Button:
                    self.target_state = self.buttons[self.selection].target_state

            if controller.button_pressed['B']:
                self.target_state = State.MENU

        for i, b in enumerate(self.buttons):
            b.selected = True if i == self.selection else False

    def draw(self, screen, camera, image_handler):
        for b in self.buttons:
            b.draw(screen, camera, image_handler)


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
        font = pygame.font.Font(None, int(0.75 * camera.zoom))
        text = font.render(self.text, True, color)
        pos = camera.world_to_screen(self.position)

        w = text.get_width() // 2

        pos[0] -= w
        pos[1] -= 8
        screen.blit(text, pos)


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

    def draw_text(self, text, y_offset, screen, camera):
        color = self.color_selected if self.selected else self.color
        font = pygame.font.Font(None, int(0.75 * camera.zoom))
        text = font.render(text, True, color)
        pos = camera.world_to_screen(self.position)
        pos[0] -= text.get_width() // 2
        pos[1] += y_offset - text.get_height() // 2
        screen.blit(text, pos)

        return text.get_width() // 2, text.get_height() // 2

    def draw(self, screen, camera, image_handler):
        self.draw_text(self.text, -32, screen, camera)
        val_str = str(self.values[self.selection]).replace(', ', 'x').strip('()')

        w, h = self.draw_text(val_str, 0, screen, camera)

        if self.selected:
            a = np.array([0, 0.5])
            b = np.array([0, -0.5])
            c = np.array([np.sqrt(3) / 2, 0])

            points = [camera.world_to_screen(-camera.zoom / 100 * p + self.position) for p in [a, b, c]]
            points = [[p[0] - w - camera.zoom // 2, p[1]] for p in points]
            pygame.draw.polygon(screen, self.color_selected, points)

            points = [camera.world_to_screen(camera.zoom / 100 * p + self.position) for p in [a, b, c]]
            points = [[p[0] + w + camera.zoom // 2, p[1]] for p in points]
            pygame.draw.polygon(screen, self.color_selected, points)


class MainMenu(Menu):
    def __init__(self):
        super().__init__()
        self.buttons.append(Button('PLAY', State.PLAYER_SELECT))
        self.buttons.append(Button('LAN', State.LAN))
        self.buttons.append(Button('OPTIONS', State.OPTIONS))
        self.buttons.append(Button('QUIT', State.QUIT))
        self.update_buttons()
        title_font = pygame.font.Font('data/fonts/CollegiateBlackFLF.ttf', 160)
        self.title = title_font.render('FIGHTBATTLE', True, (255, 255, 255))

    def input(self, input_handler, controller_id=0):
        for i in range(len(input_handler.controllers)):
            super().input(input_handler, i)

    def draw(self, screen, camera, image_handler):
        super().draw(screen, camera, image_handler)
        screen.blit(self.title, [screen.get_width() // 2 - self.title.get_width() // 2, 100])


class PlayerMenu(Menu):
    def __init__(self, position):
        super().__init__()
        self.target_state = State.PLAYER_SELECT
        self.position = np.array(position, dtype=float)
        self.controller_id = None

        self.buttons.append(Slider('Head', ['default']))
        self.buttons.append(Slider('Body', ['suit', 'speedo']))
        self.buttons.append(Slider('Team', ['solo']))
        self.buttons.append(Button('Ready up', State.PLAY))

        self.update_buttons()

    def input(self, input_handler, controller_id=0):
        if self.controller_id is None:
            if input_handler.controllers[controller_id].button_pressed['START']:
                self.controller_id = controller_id

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
        font = pygame.font.Font(None, int(0.75 * camera.zoom))

        if self.controller_id is None:
            text = font.render('Press START to join', True, (255, 255, 255))
            pos = camera.world_to_screen(self.buttons[0].position)
            screen.blit(text, [pos[0] - text.get_width() // 2, pos[1] - text.get_height() // 2])
        elif self.target_state is State.PLAY:
            text = font.render('READY', True, (255, 255, 255))
            pos = camera.world_to_screen(self.buttons[0].position)
            screen.blit(text, [pos[0] - text.get_width() // 2, pos[1] - text.get_height() // 2])
        else:
            super().draw(screen, camera, image_handler)


class OptionsMenu(Menu):
    def __init__(self):
        super().__init__()
        self.target_state = State.OPTIONS
        self.buttons.append(Slider('Mode', ['windowed', 'fullscreen']))
        self.buttons.append(Slider('Resolution', [(1280, 720), (1600, 900), (1920, 1080)], False))
        self.buttons.append(Slider('Sound volume', range(0, 110, 10), False, 10))
        self.buttons.append(Slider('Music volume', range(0, 110, 10), False, 10))
        self.update_buttons()

    def input(self, input_handler, controller_id=0):
        for i in range(len(input_handler.controllers)):
            controller = input_handler.controllers[i]
            if controller.button_pressed['A']:
                if self.buttons[0].get_value() == 'windowed':
                    pygame.display.set_mode(self.buttons[1].get_value())
                else:
                    pygame.display.set_mode(self.buttons[1].get_value(), pygame.FULLSCREEN)

            if controller.button_pressed['B']:
                self.target_state = State.MENU
                return

            super().input(input_handler, i)
