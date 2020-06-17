import numpy as np
import pyglet
from numpy.linalg import norm
from pyglet.window import key, mouse


class Controller:
    def __init__(self, joystick):
        self.joystick = joystick

        self.left_stick = np.zeros(2)
        self.right_stick = np.zeros(2)

        self.left_trigger = 0.0
        self.right_trigger = 0.0

        self.buttons = ['A', 'B', 'X', 'Y', 'LB', 'RB', 'SELECT', 'START']

        self.button_down = {}
        self.button_pressed = {}
        self.button_released = {}
        for b in self.buttons:
            self.button_down[b] = False
            self.button_pressed[b] = False
            self.button_released[b] = False

        self.stick_deadzone = 0.3
        self.trigger_deadzone = 0.01

    def on_joybutton_press(self, joystick, button):
        if button < len(self.buttons):
            self.button_pressed[self.buttons[button]] = True

    def on_joybutton_release(self, joystick, button):
        if button < len(self.buttons):
            self.button_released[self.buttons[button]] = True
            self.button_down[self.buttons[button]] = False

    def update(self):
        for b in self.buttons:
            if self.button_pressed[b]:
                if self.button_down[b]:
                    self.button_pressed[b] = False
                self.button_down[b] = True

        self.left_stick[0] = self.joystick.x
        self.left_stick[1] = -self.joystick.y

        self.right_stick[0] = self.joystick.rx
        self.right_stick[1] = -self.joystick.ry

        for stick in [self.left_stick, self.right_stick]:
            n = norm(stick)
            if n < self.stick_deadzone:
                stick[:] = np.zeros(2)
            elif n > 0.85:
                stick[:] /= n

        trigger = self.joystick.z
        if abs(trigger) < self.trigger_deadzone:
            trigger = 0

        if trigger > 0:
            self.left_trigger = trigger
        elif trigger < 0:
            self.right_trigger = -trigger
        else:
            self.left_trigger = 0
            self.right_trigger = 0


class DualShock4(Controller):
    def __init__(self, joystick):
        super().__init__(joystick=joystick)
        self.buttons = ['X', 'A', 'B', 'Y', 'LB', 'RB', '', '', 'SELECT', 'START']

        self.button_down = {}
        self.button_pressed = {}
        self.button_released = {}
        for b in self.buttons:
            self.button_down[b] = False
            self.button_pressed[b] = False
            self.button_released[b] = False

    def update(self):
        for b in self.buttons:
            if self.button_pressed[b]:
                if self.button_down[b]:
                    self.button_pressed[b] = False
                self.button_down[b] = True

        self.left_stick[0] = self.joystick.x
        self.left_stick[1] = -self.joystick.y

        self.right_stick[0] = self.joystick.z
        self.right_stick[1] = -self.joystick.rz

        for stick in [self.left_stick, self.right_stick]:
            n = norm(stick)
            if n < self.stick_deadzone:
                stick[:] = np.zeros(2)
            elif n > 0.85:
                stick[:] /= n

        left_trigger = self.joystick.rx
        if abs(left_trigger) < self.trigger_deadzone:
            left_trigger = 0

        if left_trigger > 0:
            self.left_trigger = left_trigger
        else:
            self.left_trigger = 0

        right_trigger = self.joystick.ry
        if abs(right_trigger) < self.trigger_deadzone:
            right_trigger = 0

        if right_trigger > 0:
            self.right_trigger = right_trigger
        else:
            self.right_trigger = 0


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
        if self.input_handler.keys_down.get(key.A):
            self.left_stick[0] = -1
        elif self.input_handler.keys_down.get(key.D):
            self.left_stick[0] = 1

        self.left_stick[1] = 0
        if self.input_handler.keys_down.get(key.W):
            self.left_stick[1] = 1
        elif self.input_handler.keys_down.get(key.S):
            self.left_stick[1] = -1

        n = norm(self.input_handler.mouse_position)
        if n != 0:
            self.right_stick[:] = self.input_handler.relative_mouse / n

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

        for joystick in pyglet.input.get_joysticks():
            name = joystick.device.name.lower()
            if 'xbox' in name or 'xinput' in name:
                controller = Controller(joystick)
            else:
                try:
                    controller = DualShock4(joystick)
                except:
                    continue

            joystick.open()
            joystick.push_handlers(controller)
            self.controllers.append(controller)

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

    def update(self, camera):
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
