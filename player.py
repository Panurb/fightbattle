import numpy as np

import gameobject
from collider import Rectangle, Circle, Group


class Player(gameobject.PhysicsObject):
    def __init__(self, position, number=0):
        super().__init__(position)
        self.bounce = 0

        self.add_collider(Circle(self, position + np.array([0, -1]), 0.5, Group.PLAYERS))
        self.add_collider(Rectangle(self, self.position, 1, 2, Group.PLAYERS))
        self.add_collider(Circle(self, position + np.array([0, 1]), 0.5, Group.PLAYERS))
        self.max_speed = 0.5

        self.hand_position = np.array([1.0, 0.0])
        self.hand_radius = 1.0
        self.hand = Circle(self, position, 0.2, Group.HAND)
        self.gun = None

        self.number = number

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

    def draw(self, screen, camera):
        super().draw(screen, camera)

        self.hand.draw(screen, camera)

    def input(self, input_handler):
        if not input_handler.controllers:
            return

        if input_handler.controllers[self.number].buttons['A']:
            if self.on_ground:
                self.velocity[1] = 0.7
        elif input_handler.controllers[self.number].buttons['B']:
            self.set_position([-2, 0])
            self.velocity = np.zeros(2)

        acceleration = 0.5 * input_handler.controllers[self.number].left_stick[0]
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

        self.hand.position = self.position + self.hand_position
        stick_norm = np.linalg.norm(input_handler.controllers[self.number].right_stick)
        if stick_norm != 0:
            self.hand_position = self.hand_radius * input_handler.controllers[self.number].right_stick / stick_norm
