import numpy as np
from numpy.linalg import norm
import pygame

from gameobject import GameObject, PhysicsObject, Group
from collider import Rectangle, Circle


class Player(PhysicsObject):
    def __init__(self, position, number=0):
        super().__init__(position, group=Group.PLAYERS)
        self.bounce = 0.0
        self.inertia = 0.0

        self.add_collider(Circle(position + np.array([0, -1]), 0.5))
        self.add_collider(Rectangle(self.position, 1, 2))
        self.add_collider(Circle(position + np.array([0, 1]), 0.5))

        self.max_speed = 0.5

        self.shoulder = np.array([0.0, 0.25])
        self.hand_position = np.array([1.0, 0.0])
        self.hand_radius = 1.0
        self.hand = GameObject(self.position, group=Group.HAND)
        self.hand.add_collider(Circle(position, 0.2))

        self.object = None
        self.object_group = None
        self.object_flipped = False

        self.number = number
        self.crouched = 0
        self.crouch_speed = 1

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        self.hand.set_position(self.position + self.hand_position)
        self.hand.colliders[0].update_collisions(colliders)

        if self.object:
            self.object.set_position(self.position + self.hand_position)
            if self.hand_position[0] < 0:
                if not self.object_flipped:
                    self.object.flip_horizontally()
                    self.object_flipped = True
            else:
                if self.object_flipped:
                    self.object.flip_horizontally()
                    self.object_flipped = False

    def draw(self, screen, camera):
        super().draw(screen, camera)
        self.hand.draw(screen, camera)

    def keyboard_input(self, input_handler):
        if input_handler.keys_pressed[pygame.K_r]:
            self.set_position([-2, 0])
            self.velocity = np.zeros(2)

        if input_handler.keys_pressed[pygame.K_w]:
            if self.on_ground:
                self.velocity[1] = 0.7

        if input_handler.keys_down[pygame.K_s]:
            if not self.crouched:
                self.colliders[2].position[1] -= 1
                self.colliders[1].position[1] -= 0.5
                self.colliders[1].half_height[1] = 0.5
                self.crouched = True
        elif self.crouched:
            self.colliders[2].position[1] += 1
            self.colliders[1].position[1] += 0.5
            self.colliders[1].half_height[1] = 1
            self.crouched = False

        if input_handler.keys_down[pygame.K_d]:
            if self.velocity[0] < self.max_speed:
                self.acceleration[0] = 5
        elif input_handler.keys_down[pygame.K_a]:
            if self.velocity[0] > -self.max_speed:
                self.acceleration[0] = -5
        else:
            self.acceleration[0] = 0.0

        if abs(self.velocity[0]) > self.max_speed:
            self.velocity[0] *= self.max_speed / abs(self.velocity[0])

        pos = input_handler.mouse_position
        self.hand_position = self.shoulder + self.hand_radius * pos / norm(pos)

        if input_handler.keys_pressed[pygame.K_e]:
            if self.object:
                for c in self.object.colliders:
                    if c.collisions:
                        break
                else:
                    self.object.group = self.object_group
                    self.object.velocity[:] = np.sign(self.hand_position[0]) * np.array([1.0, 0.0])
                    self.object = None
            else:
                for c in self.hand.colliders[0].collisions:
                    if norm(c.collider.parent.velocity) < 0.5:
                        self.object = c.collider.parent
                        self.object_group = c.collider.parent.group
                        c.collider.parent.group = Group.NONE
                        if self.hand_position[0] < 0:
                            self.object_flipped = True
                        else:
                            self.object_flipped = False

    def input(self, input_handler):
        controller = input_handler.controllers[self.number]

        if controller.button_pressed['A']:
            if self.on_ground:
                self.velocity[1] = 0.7
        elif controller.button_pressed['START']:
            self.set_position([-2, 0])
            self.velocity = np.zeros(2)

        acceleration = 5 * input_handler.controllers[self.number].left_stick[0]
        if acceleration > 0:
            if self.velocity[0] < self.max_speed:
                self.acceleration[0] = acceleration
        elif acceleration < 0:
            if self.velocity[0] > -self.max_speed:
                self.acceleration[0] = acceleration
        else:
            self.acceleration[0] = 0.0

        if abs(self.velocity[0]) > self.max_speed:
            self.velocity[0] *= self.max_speed / abs(self.velocity[0])

        stick_norm = np.linalg.norm(input_handler.controllers[self.number].right_stick)
        if stick_norm != 0:
            self.hand_position = self.shoulder + self.hand_radius * input_handler.controllers[self.number].right_stick / stick_norm

        if controller.button_pressed['RB']:
            if self.object:
                self.object.group = self.object_group
                self.object.velocity[:] = np.sign(self.hand_position[0]) * np.array([1.0, 0.0])
                self.object = None
            else:
                for c in self.hand.colliders[0].collisions:
                    if c.collider.parent.group is Group.BOXES or c.collider.parent.group is Group.GUNS:
                        if norm(c.collider.parent.velocity) < 0.5:
                            self.object = c.collider.parent
                            self.object_group = c.collider.parent.group
                            c.collider.parent.group = Group.NONE
                            if self.hand_position[0] < 0:
                                self.object_flipped = True
                            else:
                                self.object_flipped = False
