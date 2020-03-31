from enum import Enum

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


class Menu:
    def __init__(self):
        self.buttons = []
        self.target_state = State.MENU
        self.selection = 0
        self.selection_moved = dict()

        self.font = pygame.font.Font(None, 30)

    def input(self, input_handler, controller_id=0):
        controller = input_handler.controllers[controller_id]

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

        if controller.button_pressed['A']:
            self.target_state = self.buttons[self.selection].target_state

    def draw(self, screen, camera, image_handler):
        for i, b in enumerate(self.buttons):
            b.draw(screen, camera, image_handler)

            color = (255, 255, 0) if i == self.selection else (255, 255, 255)

            text = self.font.render(b.text, True, color)
            screen.blit(text, camera.world_to_screen(b.position))


class Button(GameObject):
    def __init__(self, text, target_state):
        super().__init__([0, 0])
        self.add_collider(Rectangle([0, 0], 3, 1))
        self.text = text
        self.target_state = target_state

    def draw(self, screen, camera, image_handler):
        super().draw(screen, camera, image_handler)


class MainMenu(Menu):
    def __init__(self):
        super().__init__()
        self.buttons.append(Button('PLAY', State.PLAYER_SELECT))
        self.buttons.append(Button('OPTIONS', State.OPTIONS))
        self.buttons.append(Button('QUIT', State.QUIT))

        for i, b in enumerate(self.buttons):
            b.set_position([0, -2 * i])

    def input(self, input_handler, controller_id=0):
        for i in range(len(input_handler.controllers)):
            super().input(input_handler, i)


class PlayerMenu(Menu):
    def __init__(self, position):
        super().__init__()
        self.position = position
        self.controller_id = None
        self.buttons.append(Button('Ready up', State.PLAY))

        for i, b in enumerate(self.buttons):
            b.set_position(self.position - 2 * i * basis(1))

    def input(self, input_handler, controller_id=0):
        if self.controller_id is None:
            if input_handler.controllers[controller_id].button_pressed['START']:
                self.controller_id = controller_id
        else:
            super().input(input_handler, self.controller_id)

    def draw(self, screen, camera, image_handler):
        if self.controller_id is None:
            text = self.font.render('Press START to join', True, (255, 255, 255))
            screen.blit(text, camera.world_to_screen(self.buttons[0].position))
        elif self.target_state is State.PLAY:
            text = self.font.render('READY', True, (255, 255, 255))
            screen.blit(text, camera.world_to_screen(self.buttons[0].position))
        else:
            super().draw(screen, camera, image_handler)
