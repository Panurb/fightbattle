import numpy as np
from numpy.linalg import norm

from gameobject import GameObject, PhysicsObject, Group
from collider import Rectangle, Circle


class Hand(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, group=Group.HANDS)
        self.add_collider(Circle([0, 0], 0.2))
        self.gravity_scale = 0.0


class Player(PhysicsObject):
    def __init__(self, position, number=0):
        super().__init__(position, group=Group.PLAYERS)
        self.bounce = 0.0
        self.inertia = 0.0

        self.add_collider(Rectangle([0, 0], 1, 3))

        self.legs = GameObject(self.position)
        self.legs.add_collider(Circle([0, -1], 0.5))
        self.body = GameObject(self.position)
        self.body.add_collider(Rectangle([0, 0], 1, 1))
        self.head = GameObject(self.position)
        self.head.add_collider(Circle([0, 1], 0.5))

        self.max_speed = 0.25

        self.shoulder = np.array([0.0, 0.25])
        self.hand_position = np.array([1.0, 0.0])
        self.hand_radius = 1.0
        self.hand = Hand(self.position)

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

        if self.destroyed:
            self.angular_velocity = -0.125 * np.sign(self.angle + np.pi / 2)

        self.legs.set_position(self.position)
        self.body.set_position(self.position)
        self.head.set_position(self.position + np.array([0, -self.crouched]))

        if self.object:
            self.hand.set_position(self.position + self.shoulder + self.hand_position)

            if self.hand_position[0] < 0:
                if not self.object.flipped:
                    self.object.flip_horizontally()
            else:
                if self.object.flipped:
                    self.object.flip_horizontally()

            self.object.velocity = 0.5 * (self.hand.position - self.object.position)

            self.object.update(gravity, time_step, colliders)
            if norm(self.position + self.shoulder - self.object.position) > 1.5 * self.hand_radius:
                self.throw_object(0)
            else:
                self.hand.set_position(self.object.position)
        else:
            self.hand.velocity = self.velocity + 1 * (self.position + self.shoulder
                                                        + self.hand_position - self.hand.position)
            self.hand.update(gravity, time_step, colliders)

    def draw(self, screen, camera):
        super().draw(screen, camera)

        self.hand.draw(screen, camera)
        #for part in (self.legs, self.body, self.head):
        #    part.draw(screen, camera)

    def input(self, input_handler):
        if self.destroyed:
            return

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

        if self.on_ground and controller.left_stick[1] < -0.5:
            self.crouched = min(1, self.crouched + self.crouch_speed)
        else:
            self.crouched = max(0, self.crouched - self.crouch_speed)

        self.head.position[1] = self.position[1] + 1 - self.crouched
        self.body.position[1] = self.position[1] - 0.5 * self.crouched
        self.collider.position[1] = self.position[1] - 0.5 * self.crouched
        self.collider.half_height[1] = 1.5 - 0.5 * self.crouched
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

    def damage(self, amount):
        if self.health > 0:
            self.health -= amount
        else:
            self.health = 0
            if not self.destroyed:
                self.velocity = np.array([0.5, 0.5])
                self.destroyed = True
                self.inertia = 1.0

    def throw_object(self, velocity):
        if velocity:
            self.object.velocity[:] = np.sign(self.hand_position[0]) * np.array([1.0, 0.0]) * velocity * self.throw_speed
        self.object = None

    def grab_object(self):
        for c in self.hand.collider.collisions:
            if c.collider.parent.group is Group.BOXES or c.collider.parent.group is Group.GUNS:
                if norm(c.collider.parent.velocity) < 0.5:
                    self.object = c.collider.parent
                    self.object.on_ground = False
                    break

    def attack(self):
        if self.object:
            try:
                self.object.attack()
            except:
                pass
