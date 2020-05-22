import numpy as np
from numpy.linalg import norm
import pygame
import pyglet


class Controller:
    def __init__(self, index):
        if index != -1:
            self.joystick = pygame.joystick.Joystick(index)
            self.joystick.init()

        self.left_stick = np.zeros(2)
        self.right_stick = np.zeros(2)

        self.left_trigger = 0.0
        self.right_trigger = 0.0

        self.button_down = {}
        self.button_pressed = {}
        self.button_released = {}
        for b in ['A', 'B', 'X', 'Y', 'LB', 'RB', 'SELECT', 'START']:
            self.button_down[b] = False
            self.button_pressed[b] = False
            self.button_released[b] = False

        self.stick_deadzone = 0.3
        self.trigger_deadzone = 0.01

    def update(self):
        self.left_stick[0] = self.joystick.get_axis(0)
        self.left_stick[1] = -self.joystick.get_axis(1)

        self.right_stick[0] = self.joystick.get_axis(4)
        self.right_stick[1] = -self.joystick.get_axis(3)

        for stick in [self.left_stick, self.right_stick]:
            n = norm(stick)
            if n < self.stick_deadzone:
                stick[:] = np.zeros(2)
            elif n > 0.9:
                stick[:] /= n

        trigger = self.joystick.get_axis(2)
        if abs(trigger) < self.trigger_deadzone:
            trigger = 0

        if trigger > 0:
            self.left_trigger = trigger
        elif trigger < 0:
            self.right_trigger = -trigger
        else:
            self.left_trigger = 0
            self.right_trigger = 0

        for i, b in enumerate(['A', 'B', 'X', 'Y', 'LB', 'RB', 'SELECT', 'START']):
            self.button_pressed[b] = False
            self.button_released[b] = False

            if self.joystick.get_button(i):
                if not self.button_down[b]:
                    self.button_pressed[b] = True
            else:
                if self.button_down[b]:
                    self.button_released[b] = True

            self.button_down[b] = self.joystick.get_button(i)


class DualShock4(Controller):
    def update(self):
        self.left_stick[0] = self.joystick.get_axis(0)
        self.left_stick[1] = -self.joystick.get_axis(1)

        self.right_stick[0] = self.joystick.get_axis(2)
        self.right_stick[1] = -self.joystick.get_axis(3)

        for stick in [self.left_stick, self.right_stick]:
            n = norm(stick)
            if n < self.stick_deadzone:
                stick[:] = np.zeros(2)
            elif n > 0.9:
                stick[:] /= n

        self.left_trigger = (self.joystick.get_axis(5) + 1) / 2
        if abs(self.left_trigger) < self.trigger_deadzone:
            self.left_trigger = 0

        self.right_trigger = (self.joystick.get_axis(4) + 1) / 2
        if abs(self.right_trigger) < self.trigger_deadzone:
            self.right_trigger = 0

        for i, b in enumerate(['X', 'A', 'B', 'Y', 'LB', 'RB', '', '', 'SELECT', 'START']):
            if not b:
                continue

            self.button_pressed[b] = False
            self.button_released[b] = False

            if self.joystick.get_button(i):
                if not self.button_down[b]:
                    self.button_pressed[b] = True
            else:
                if self.button_down[b]:
                    self.button_released[b] = True

            self.button_down[b] = self.joystick.get_button(i)


class Keyboard(Controller):
    def __init__(self, input_handler):
        super().__init__(-1)

        self.buttons = {'A': pygame.K_SPACE,
                        'B': pygame.K_ESCAPE,
                        'X': pygame.K_q,
                        'Y': pygame.K_f,
                        'LB': pygame.K_c,
                        'RB': pygame.K_e,
                        'SELECT': pygame.K_RSHIFT,
                        'START': pygame.K_RETURN}

        self.input_handler = input_handler

    def update(self):
        if self.input_handler.keys_down[pygame.K_a]:
            self.left_stick[0] = -1
        elif self.input_handler.keys_down[pygame.K_d]:
            self.left_stick[0] = 1
        else:
            self.left_stick[0] = 0

        if self.input_handler.keys_down[pygame.K_w]:
            self.left_stick[1] = 1
        elif self.input_handler.keys_down[pygame.K_s]:
            self.left_stick[1] = -1
        else:
            self.left_stick[1] = 0

        n = norm(self.input_handler.mouse_position)
        if n != 0:
            self.right_stick[:] = self.input_handler.relative_mouse / n

        if self.input_handler.mouse_down[2]:
            self.left_trigger = 1
        else:
            self.left_trigger = 0

        if self.input_handler.mouse_down[0]:
            self.right_trigger = 1
        else:
            self.right_trigger = 0

        for i, b in enumerate(['A', 'B', 'X', 'Y', 'LB', 'RB', 'SELECT', 'START']):
            self.button_pressed[b] = False
            self.button_released[b] = False

            self.button_pressed[b] = self.input_handler.keys_pressed[self.buttons[b]]
            self.button_down[b] = self.input_handler.keys_down[self.buttons[b]]
            self.button_released[b] = self.input_handler.keys_released[self.buttons[b]]


class InputHandler:
    def __init__(self):
        self.controllers = []
        self.controllers.append(Keyboard(self))
        for i in range(pygame.joystick.get_count()):
            name = pygame.joystick.Joystick(i).get_name().lower()
            if 'xbox' in name:
                self.controllers.append(Controller(i))
            elif 'xinput' in name:
                self.controllers.append(Controller(i))
            else:
                try:
                    self.controllers.append(DualShock4(i))
                except:
                    pass

        self.keys_down = {}
        self.keys_pressed = {}
        self.keys_released = {}
        for i in range(len(pygame.key.get_pressed())):
            self.keys_down[i] = False
            self.keys_pressed[i] = False
            self.keys_released[i] = False
        self.mouse_position = np.zeros(2)
        self.relative_mouse = np.zeros(2)
        self.mouse_down = [False] * 6
        self.mouse_pressed = [False] * 6
        self.mouse_released = [False] * 6

        self.mouse_screen = np.zeros(2)
        self.mouse_change = np.zeros(2)

        self.quit = False

    def update(self, camera):
        for c in self.controllers:
            c.update()

        for key in self.keys_pressed:
            self.keys_pressed[key] = False
        self.mouse_pressed = [False] * 8
        self.mouse_released = [False] * 8

        for event in pygame.event.get():
            if event.type == pygame.QUIT or self.keys_down[pygame.K_END]:
                self.quit = True
            else:
                if event.type == pygame.KEYDOWN:
                    self.keys_pressed[event.key] = True
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.mouse_pressed[event.button - 1] = True
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.mouse_released[event.button - 1] = True

        mouse_pos = camera.screen_to_world(pygame.mouse.get_pos())
        self.mouse_position[:] = mouse_pos

        mouse_screen = pygame.mouse.get_pos()
        self.mouse_change = (mouse_screen - self.mouse_screen) / camera.zoom
        self.mouse_change[1] *= -1
        self.mouse_screen[:] = mouse_screen

        for key in self.keys_down:
            if self.keys_down[key] and not pygame.key.get_pressed()[key]:
                self.keys_released[key] = True
            else:
                self.keys_released[key] = False

        self.keys_down = pygame.key.get_pressed()
        self.mouse_down = pygame.mouse.get_pressed()
