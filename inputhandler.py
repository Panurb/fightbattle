import numpy as np
from numpy.linalg import norm
import pygame
from pyglet.window import key


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

        self.buttons = {'A': key.SPACE,
                        'B': key.ESCAPE,
                        'X': key.Q,
                        'Y': key.F,
                        'LB': key.C,
                        'RB': key.E,
                        'SELECT': key.RSHIFT,
                        'START': key.RETURN}

        self.input_handler = input_handler

    def update(self):
        self.left_stick[0] = 0
        if key.A in self.input_handler.keys_down and self.input_handler.keys_down[key.A]:
            self.left_stick[0] = -1
        elif key.D in self.input_handler.keys_down and self.input_handler.keys_down[key.D]:
            self.left_stick[0] = 1

        self.left_stick[1] = 0
        if key.W in self.input_handler.keys_down and self.input_handler.keys_down[key.W]:
            self.left_stick[1] = 1
        elif key.S in self.input_handler.keys_down and self.input_handler.keys_down[key.S]:
            self.left_stick[1] = -1

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

            self.button_pressed[b] = self.input_handler.key_pressed(self.buttons[b])
            self.button_down[b] = self.input_handler.key_down(self.buttons[b])
            self.button_released[b] = self.input_handler.key_released(self.buttons[b])


class InputHandler:
    def __init__(self):
        self.controllers = []
        self.controllers.append(Keyboard(self))
        '''
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
        '''

        self.keys_down = dict()
        self.keys_pressed = dict()
        self.keys_released = dict()

        self.mouse_position = np.zeros(2)
        self.relative_mouse = np.zeros(2)
        self.mouse_down = [False] * 8
        self.mouse_pressed = [False] * 8
        self.mouse_released = [False] * 8

        self.mouse_screen = np.zeros(2)
        self.mouse_change = np.zeros(2)

        self.quit = False

    def key_pressed(self, k):
        return k in self.keys_pressed and self.keys_pressed[k]

    def key_released(self, k):
        return k in self.keys_released and self.keys_released[k]

    def key_down(self, k):
        return k in self.keys_down and self.keys_down[k]

    def update(self):
        for c in self.controllers:
            c.update()

        for k in self.keys_pressed:
            if self.keys_pressed[k]:
                if k in self.keys_down and self.keys_down[k]:
                    self.keys_pressed[k] = False
                self.keys_down[k] = True

        for b in range(len(self.mouse_pressed)):
            if self.mouse_pressed[b]:
                if self.mouse_down[b]:
                    self.mouse_pressed[b] = False
                self.mouse_down[b] = True
