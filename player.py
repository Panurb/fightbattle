import numpy as np
from numpy.linalg import norm

from gameobject import GameObject, PhysicsObject, Group
from collider import Rectangle, Circle


class Player(PhysicsObject):
    def __init__(self, position, number=0):
        super().__init__(position, group=Group.PLAYERS)
        self.bounce = 0.0
        self.inertia = 0.0

        self.legs = Circle(position + np.array([0, -1]), 0.5)
        self.body = Rectangle(self.position, 0.5, 2)
        self.head = Circle(position + np.array([0, 1]), 0.5)

        self.add_collider(self.head)
        self.add_collider(self.body)
        self.add_collider(self.legs)

        self.max_speed = 0.25

        self.shoulder = np.array([0.0, 0.25])
        self.hand_position = np.array([1.0, 0.0])
        self.hand_radius = 1.0
        self.hand = GameObject(self.position, group=Group.HAND)
        self.hand.add_collider(Circle(position, 0.2))

        self.object = None

        self.number = number
        self.crouched = 0
        self.crouch_speed = 0.25

        self.trigger_pressed = False

        self.throw_speed = 2
        self.throw_charge = 0
        self.charge_speed = 0.05

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        self.hand.set_position(self.position + self.shoulder + self.hand_position)
        self.hand.colliders[0].update_collisions(colliders)

        if self.object:
            self.object.set_position(self.position + self.shoulder + self.hand_position)
            if self.hand_position[0] < 0:
                if not self.object.flipped:
                    self.object.flip_horizontally()
            else:
                if self.object.flipped:
                    self.object.flip_horizontally()

    def draw(self, screen, camera):
        super().draw(screen, camera)
        self.hand.draw(screen, camera)

    def input(self, input_handler):
        controller = input_handler.controllers[self.number]

        if controller.button_pressed['A']:
            if self.on_ground:
                self.velocity[1] = 0.7
        elif controller.button_pressed['START']:
            self.set_position([-2, 0])
            self.velocity = np.zeros(2)

        acceleration = 5 * controller.left_stick[0]
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

        if controller.left_stick[1] < -0.5:
            self.crouched = min(1, self.crouched + self.crouch_speed)
        else:
            self.crouched = max(0, self.crouched - self.crouch_speed)

        self.head.position[1] = self.position[1] + 1 - self.crouched
        self.body.position[1] = self.position[1] - 0.5 * self.crouched
        self.body.half_height[1] = 1 - 0.5 * self.crouched
        self.shoulder[1] = 0.15 - 0.5 * self.crouched

        stick_norm = norm(controller.right_stick)
        if stick_norm != 0:
            self.hand_position = self.shoulder + self.hand_radius * controller.right_stick / stick_norm

        if controller.button_pressed['RB']:
            if self.object:
                self.throw_object(0)
            else:
                self.grab_object()

        if controller.right_trigger > 0.5:
            if not self.trigger_pressed:
                self.attack()
                self.trigger_pressed = True
        else:
            self.trigger_pressed = False

        if self.object:
            if controller.left_trigger > 0.5:
                self.throw_charge = min(1, self.throw_charge + self.charge_speed)
            elif self.throw_charge:
                self.throw_object(self.throw_charge)
                self.throw_charge = 0
        else:
            self.throw_charge = 0

    def throw_object(self, velocity):
        for col in self.object.colliders:
            for c in col.collisions:
                if self.object.collides_with(c.collider.parent):
                    return

        self.object.collision = True
        self.object.velocity[:] = np.sign(self.hand_position[0]) * np.array([1.0, 0.0]) * velocity * self.throw_speed
        self.object = None

    def grab_object(self):
        for c in self.hand.colliders[0].collisions:
            if c.collider.parent.group is Group.BOXES or c.collider.parent.group is Group.GUNS:
                if norm(c.collider.parent.velocity) < 0.5:
                    self.object = c.collider.parent
                    self.object.collision = False

    def attack(self):
        if self.object:
            try:
                self.object.attack()
            except:
                pass
