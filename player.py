import numpy as np
from numpy.linalg import norm
import pygame

from gameobject import GameObject, PhysicsObject, Group
from collider import Rectangle, Circle
from helpers import norm2, basis, perp


class Hand(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, group=Group.HANDS)
        self.add_collider(Circle([0, 0], 0.2))
        self.gravity_scale = 0.0
        self.image_path = 'hand'
        self.size = 0.7


class Player(PhysicsObject):
    def __init__(self, position, number=0):
        super().__init__(position, group=Group.PLAYERS)
        self.image_path = 'body'
        self.size = 0.75
        self.bounce = 0.0
        self.inertia = 0.0

        self.add_collider(Rectangle([0, 0], 1, 3))

        self.legs = GameObject(self.position - basis(1))
        self.legs.add_collider(Circle([0, 0], 0.5))

        self.body = GameObject(self.position)
        self.body.add_collider(Rectangle([0, 0], 1, 1))

        self.head = GameObject(self.position + basis(1))
        self.head.image_path = 'head'
        self.head.add_collider(Circle([0, 0], 0.5))
        self.head.size = 0.85

        self.foot_1 = np.zeros(2)
        self.foot_2 = np.zeros(2)

        self.max_speed = 0.25

        self.shoulder = self.position + 0.25 * basis(1)
        self.hand_goal = basis(0)
        self.arm_length = 1.0
        self.hand = Hand(self.position)

        self.elbow = np.zeros(2)

        self.object = None

        self.crouched = 0
        self.crouch_speed = 0.25

        self.trigger_pressed = False

        self.throw_speed = 2
        self.throw_charge = 0
        self.charge_speed = 0.05

        self.number = number

    def flip_horizontally(self):
        super().flip_horizontally()

        self.head.flip_horizontally()
        self.hand.flip_horizontally()

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if self.destroyed:
            if self.angle > -np.pi / 2:
                self.angular_velocity = -0.125
            else:
                self.rotate(-np.pi / 2 - self.angle)
                self.angular_velocity = 0.0

            return

        self.legs.set_position(self.position - basis(1))
        self.body.set_position(self.position - 0.5 * self.crouched * basis(1))
        self.body.collider.half_height = 0.5 * (1 - 0.5 * self.crouched) * basis(1)
        self.head.set_position(self.position + (1 - self.crouched) * basis(1))

        self.collider.position[1] = self.position[1] - 0.5 * self.crouched
        self.collider.half_height[1] = 1.5 - 0.5 * self.crouched
        self.shoulder = self.position + (0.15 - 0.5 * self.crouched) * basis(1)

        d = self.hand.position[0] - self.position[0]
        if abs(d) > 0.1 and np.sign(d) != self.direction:
            self.flip_horizontally()

        if self.object:
            self.hand.set_position(self.shoulder + self.hand_goal)

            if self.object.group is Group.GUNS:
                d = self.hand.position[0] - self.position[0]
                if abs(d) > 0.1 and np.sign(d) != self.direction:
                    self.object.flip_horizontally()

            self.object.velocity = 0.5 * (self.hand.position - self.object.position)

            self.object.update(gravity, time_step, colliders)
            if norm(self.shoulder - self.object.position) > 1.5 * self.arm_length:
                self.throw_object(0.0)
            else:
                self.hand.set_position(self.object.position)
                self.hand.update(gravity, time_step, colliders)
        else:
            self.hand.velocity = self.velocity[0] * basis(0) + self.shoulder + self.hand_goal - self.hand.position
            self.hand.update(gravity, time_step, colliders)
            self.hand.collider.update_collisions(colliders, [Group.BOXES, Group.GUNS])

        r = self.hand.position - self.shoulder

        angle = np.arctan(r[1] / r[0])
        delta_angle = angle - self.hand.angle
        self.hand.angular_velocity = 0.5 * delta_angle

        #angle = np.arctan2(r[1], r[0])
        #if self.direction == -1:
        #    angle += np.pi
        #self.hand.angle = angle
        #self.hand.update_image = True

        r = self.hand.position - self.shoulder
        r_norm = norm(r)
        self.elbow = self.shoulder + 0.5 * r - 0.5 * self.direction * np.sqrt(max(1 - r_norm**2, 0)) * perp(r) / r_norm

    def draw(self, screen, camera, image_handler):
        super().draw(screen, camera, image_handler)

        self.head.draw(screen, camera, image_handler)

        if self.object:
            self.object.draw(screen, camera, image_handler)

        a = camera.world_to_screen(self.shoulder)
        b = camera.world_to_screen(self.elbow)
        c = camera.world_to_screen(self.hand.position)

        color = pygame.Color('black')
        width = int(camera.zoom / 10)

        pygame.draw.line(screen, color, a, b, width)
        pygame.draw.line(screen, color, b, c, width)

        self.hand.draw(screen, camera, image_handler)

        #self.debug_draw(screen, camera, image_handler)

    def debug_draw(self, screen, camera, image_handler):
        #self.collider.draw(screen, camera)

        self.hand.debug_draw(screen, camera, image_handler)

        for part in (self.head, self.body, self.legs):
            part.debug_draw(screen, camera, image_handler)

        pygame.draw.circle(screen, image_handler.debug_color, camera.world_to_screen(self.shoulder + self.hand_goal), 2)

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

        acceleration = controller.left_stick[0]
        if acceleration > 0:
            if self.velocity[0] < self.max_speed:
                self.acceleration[0] = (5 - 2 * self.crouched) * acceleration
        elif acceleration < 0:
            if self.velocity[0] > -self.max_speed:
                self.acceleration[0] = (5 - 2 * self.crouched) * acceleration
        else:
            self.acceleration[0] = 0.0

        if abs(self.velocity[0]) > self.max_speed:
            self.velocity[0] *= self.max_speed / abs(self.velocity[0])

        if self.on_ground and controller.left_stick[1] < -0.5:
            self.crouched = min(1.0, self.crouched + self.crouch_speed)
        else:
            self.crouched = max(0.0, self.crouched - self.crouch_speed)

        stick_norm = norm(controller.right_stick)
        if stick_norm != 0:
            self.hand_goal = self.arm_length * controller.right_stick / stick_norm

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
                self.throw_charge = min(1.0, self.throw_charge + self.charge_speed)
            elif self.throw_charge:
                self.throw_object(self.throw_charge)
                self.throw_charge = 0
        else:
            self.throw_charge = 0

    def damage(self, amount):
        if self.health > 0:
            self.health -= amount

        if self.health <= 0:
            if not self.destroyed:
                self.velocity = np.array([0.5, 0.5])
                self.destroyed = True
                self.inertia = 1.0

    def throw_object(self, velocity):
        if velocity:
            self.object.velocity[:] = np.sign(self.hand_goal[0]) * np.array([1.0, 0.0]) * velocity * self.throw_speed
        self.object = None

    def grab_object(self):
        for c in self.hand.collider.collisions:
            if c.collider.parent.group is Group.BOXES or c.collider.parent.group is Group.GUNS:
                if norm2(self.velocity - c.collider.parent.velocity) < 0.25:
                    self.object = c.collider.parent
                    self.object.on_ground = False
                    break

    def attack(self):
        if self.object:
            self.object.attack()
