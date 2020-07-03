import os

import numpy as np
from numpy.linalg import norm
import pygame
from pyglet.window import key, mouse


class Controller:
    def __init__(self, index):
        if index != -1:
            self.joystick = pygame.joystick.Joystick(index)
            self.joystick.init()

        if os.name == 'nt':
            self.sticks = [0, 1, 4, 3, 2, 2]
            self.buttons = ['A', 'B', 'X', 'Y', 'LB', 'RB', 'SELECT', 'START']
        else:
            self.sticks = [0, 1, 3, 4, 2, 5]
            self.buttons = ['A', 'B', 'X', 'Y', 'LB', 'RB', 'SELECT', 'START']

        self.left_stick = np.zeros(2)
        self.right_stick = np.zeros(2)

        self.left_trigger = 0.0
        self.right_trigger = 0.0

        self.button_down = {}
        self.button_pressed = {}
        self.button_released = {}
        for b in self.buttons:
            self.button_down[b] = False
            self.button_pressed[b] = False
            self.button_released[b] = False

        self.stick_deadzone = 0.3
        self.trigger_deadzone = 0.01

    def update(self):
        self.left_stick[0] = self.joystick.get_axis(self.sticks[0])
        self.left_stick[1] = -self.joystick.get_axis(self.sticks[1])

        self.right_stick[0] = self.joystick.get_axis(self.sticks[2])
        self.right_stick[1] = -self.joystick.get_axis(self.sticks[3])

        for stick in [self.left_stick, self.right_stick]:
            n = norm(stick)
            if n < self.stick_deadzone:
                stick[:] = np.zeros(2)
            elif n > 0.9:
                stick[:] /= n

        if self.sticks[4] == self.sticks[5]:
            trigger = self.joystick.get_axis(self.sticks[4])
            if abs(trigger) < self.trigger_deadzone:
                trigger = 0

            if trigger > 0:
                self.left_trigger = trigger
            elif trigger < 0:
                self.right_trigger = -trigger
            else:
                self.left_trigger = 0
                self.right_trigger = 0
        else:
            self.left_trigger = (self.joystick.get_axis(self.sticks[4]) + 1) / 2
            if abs(self.left_trigger) < self.trigger_deadzone:
                self.left_trigger = 0

            self.right_trigger = (self.joystick.get_axis(self.sticks[5]) + 1) / 2
            if abs(self.right_trigger) < self.trigger_deadzone:
                self.right_trigger = 0

        for i, b in enumerate(self.buttons):
            if b == '':
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


class DualShock4(Controller):
    def __init__(self, index):
        super().__init__(index)
        if os.name == 'nt':
            self.buttons = ['X', 'A', 'B', 'Y', 'LB', 'RB', '', '', 'SELECT', 'START']
            self.sticks = [0, 1, 2, 3, 5, 4]
        else:
            self.sticks = [0, 1, 3, 4, 2, 5]
            self.buttons = ['A', 'B', 'Y', 'X', 'LB', 'RB', '', '', 'SELECT', 'START']


class Keyboard(Controller):
    def __init__(self, input_handler):
        super().__init__(-1)

        self.buttons = {'A': key.SPACE,
                        'B': key.ESCAPE,
                        'X': key.LSHIFT,
                        'Y': key.F,
                        'LB': key.C,
                        'RB': key.E,
                        'SELECT': key.RSHIFT,
                        'START': key.RETURN}

        self.input_handler = input_handler

    def update(self):
        self.left_stick[0] = 0
        if self.input_handler.keys_down.get(key.A):
            self.left_stick[0] = -1
        elif self.input_handler.keys_down.get(key.D):
            self.left_stick[0] = 1

        self.left_stick[1] = 0
        if self.input_handler.keys_down.get(key.W):
            self.left_stick[1] = 1
        elif self.input_handler.keys_down.get(key.S):
            self.left_stick[1] = -1

        self.right_stick += 2 * self.input_handler.mouse_change
        n = norm(self.right_stick)
        if n > 1:
            self.right_stick /= n

        if self.input_handler.mouse_down[mouse.RIGHT]:
            self.left_trigger = 1
        else:
            self.left_trigger = 0

        if self.input_handler.mouse_down[mouse.LEFT]:
            self.right_trigger = 1
        else:
            self.right_trigger = 0

        for i, b in enumerate(['A', 'B', 'X', 'Y', 'LB', 'RB', 'SELECT', 'START']):
            self.button_pressed[b] = self.input_handler.keys_pressed.get(self.buttons[b])
            self.button_down[b] = self.input_handler.keys_down.get(self.buttons[b])
            self.button_released[b] = self.input_handler.keys_released.get(self.buttons[b])


class InputHandler:
    def __init__(self):
        self.controllers = []
        self.controllers.append(Keyboard(self))
        for i in range(pygame.joystick.get_count()):
            name = pygame.joystick.Joystick(i).get_name().lower()
            if 'xbox' in name or 'xinput' in name:
                self.controllers.append(Controller(i))
            else:
                self.controllers.append(DualShock4(i))

        self.keys_down = {}
        self.keys_pressed = {}
        self.keys_released = {}

        self.mouse_position = np.zeros(2)
        self.relative_mouse = np.zeros(2)
        self.mouse_down = [False] * 8
        self.mouse_pressed = [False] * 8
        self.mouse_released = [False] * 8

        self.mouse_screen = np.zeros(2)
        self.mouse_change = np.zeros(2)

    def update(self, camera):
        pygame.event.get()

        for k in self.keys_pressed:
            if self.keys_pressed[k]:
                if self.keys_down.get(k):
                    self.keys_pressed[k] = False
                self.keys_down[k] = True
            elif self.keys_released.get(k):
                if not self.keys_down.get(k):
                    self.keys_released[k] = False
                self.keys_down[k] = False

        self.mouse_position = camera.screen_to_world(self.mouse_screen)
        self.mouse_change /= camera.zoom

        for b in range(len(self.mouse_pressed)):
            if self.mouse_pressed[b]:
                if self.mouse_down[b]:
                    self.mouse_pressed[b] = False
                self.mouse_down[b] = True
            elif self.mouse_released[b]:
                if not self.mouse_down[b]:
                    self.mouse_released[b] = False
                self.mouse_down[b] = False

        for c in self.controllers:
            c.update()

    def on_key_press(self, symbol, modifiers):
        self.keys_pressed[symbol] = True
        if symbol == key.ESCAPE:
            return True

    def on_key_release(self, symbol, modifiers):
        self.keys_released[symbol] = True
        self.keys_down[symbol] = False

    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse_screen[:] = [x, y]
        self.mouse_change[:] = [dx, dy]

    def on_mouse_drag(self, x, y, dx, dy, button, modifiers):
        self.mouse_screen[:] = [x, y]
        self.mouse_change[:] = [dx, dy]

    def on_mouse_press(self, x, y, button, modifiers):
        self.mouse_pressed[button] = True

    def on_mouse_release(self, x, y, button, modifiers):
        self.mouse_released[button] = True
