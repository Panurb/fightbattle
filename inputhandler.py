import numpy as np
import pygame


class Controller:
    def __init__(self, index):
        self.joystick = pygame.joystick.Joystick(index)
        self.joystick.init()

        self.left_stick = np.zeros(2)
        self.right_stick = np.zeros(2)

        self.left_trigger = 0.0
        self.right_trigger = 0.0

        self.buttons = {'A': False, 'B': False}

        self.deadzone = 0.3

    def update(self):
        self.left_stick[0] = self.joystick.get_axis(0)
        self.left_stick[1] = -self.joystick.get_axis(1)

        self.right_stick[0] = self.joystick.get_axis(4)
        self.right_stick[1] = -self.joystick.get_axis(3)

        for stick in [self.left_stick, self.right_stick]:
            if np.linalg.norm(stick) < self.deadzone:
                stick[:] = np.zeros(2)

        trigger = self.joystick.get_axis(2)
        if trigger > 0:
            self.left_trigger = trigger
        else:
            self.right_trigger = -trigger

        self.buttons['A'] = self.joystick.get_button(0)
        self.buttons['B'] = self.joystick.get_button(1)


class InputHandler:
    def __init__(self):
        self.controllers = []
        for i in range(pygame.joystick.get_count()):
            self.controllers.append(Controller(i))

        self.keys_down = {}
        self.keys_pressed = {}
        for i in range(len(pygame.key.get_pressed())):
            self.keys_pressed[i] = False
        self.mouse_position = [0, 0]
        self.mouse_down = []
        self.mouse_pressed = []
        self.mouse_released = []

        self.quit = False

    def update(self):
        for c in self.controllers:
            c.update()

        for key in self.keys_pressed:
            self.keys_pressed[key] = False
        self.mouse_pressed = [False] * 6
        self.mouse_released = [False] * 6

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit = True
            else:
                if event.type == pygame.KEYDOWN:
                    self.keys_pressed[event.key] = True
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.mouse_pressed[event.button] = True
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.mouse_released[event.button] = True

                self.mouse_position = pygame.mouse.get_pos()

        self.keys_down = pygame.key.get_pressed()
        self.mouse_down = pygame.mouse.get_pressed()
