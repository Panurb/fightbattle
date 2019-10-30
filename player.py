import numpy as np
from numpy.linalg import norm
import pygame

from gameobject import GameObject, PhysicsObject, Pendulum
from collider import Rectangle, Circle, Group
from helpers import norm2, basis, perp, normalized
from particle import Cloud


class Player(PhysicsObject):
    def __init__(self, position, number=0):
        super().__init__(position)
        self.bounce = 0.0
        self.inertia = 0.0

        self.add_collider(Rectangle([0, 0], 1, 3, Group.PLAYERS))

        self.legs = GameObject(self.position - basis(1))
        self.legs.add_collider(Circle([0, 0], 0.5))

        self.body = GameObject(self.position)
        self.body.image_path = 'body'
        self.body.size = 0.75
        self.body.add_collider(Rectangle([0, 0], 1, 1))

        self.head = GameObject(self.position + basis(1))
        self.head.image_path = 'head'
        self.head.add_collider(Circle([0, 0], 0.5))
        self.head.size = 0.85

        self.back_foot = Foot(np.zeros(2))
        self.front_foot = Foot(np.zeros(2))

        self.max_speed = 0.25

        self.shoulder = self.position + 0.25 * 2 / 3 * self.collider.half_height
        self.hand_goal = basis(0)
        self.arm_length = 1.0
        self.hand = Hand(self.position)

        self.elbow = np.zeros(2)

        self.object = None

        self.crouched = 0
        self.crouch_speed = 0.25

        self.lt_pressed = False
        self.rt_pressed = False

        self.throw_speed = 1.0
        self.throw_charge = 0.0
        self.charge_speed = 0.05

        self.number = number

        self.blood = []

    def flip_horizontally(self):
        super().flip_horizontally()

        self.head.flip_horizontally()

        self.hand.flip_horizontally()
        self.hand.angle += np.sign(self.hand.position[1] - self.position[1]) * self.direction * np.pi

        self.body.flip_horizontally()
        self.back_foot.flip_horizontally()
        self.front_foot.flip_horizontally()

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        for b in self.blood:
            b.update(gravity, time_step)
            if not b.particles:
                self.blood.remove(b)

        if self.destroyed:
            if np.pi / 2 > self.angle > -np.pi / 2:
                self.angular_velocity = 0.125 * self.direction
            else:
                self.rotate(self.direction * np.pi / 2 - self.angle)
                self.angular_velocity = 0.0

            self.hand.support[:] = self.shoulder
            self.hand.update(gravity, time_step, colliders)

            #self.back_foot.update(gravity, time_step, colliders)
            #self.front_foot.update(gravity, time_step, colliders)

        h = normalized(self.collider.half_height)

        self.legs.set_position(self.position - h)

        self.body.set_position(self.position - 0.5 * self.crouched * h)
        self.body.collider.rotate(self.angle - self.body.angle)
        self.body.angle = self.angle

        self.head.set_position(self.position + (1 - self.crouched) * h)
        self.head.angle = self.angle

        self.shoulder = self.position + (0.15 - 0.75 * self.crouched) * h

        if self.destroyed:
            return

        self.back_foot.set_position(self.position - np.array([0.3 + 0.05 * self.direction, 1.5]))
        self.front_foot.set_position(self.position - np.array([0.3 + 0.25 * self.direction, 1.5]))
        self.back_foot.update(time_step)
        self.front_foot.update(time_step)

        self.body.collider.half_height = 0.5 * (1 - 0.5 * self.crouched) * basis(1)
        self.collider.position[1] = self.position[1] - 0.5 * self.crouched
        self.collider.half_height[1] = 1.5 - 0.5 * self.crouched

        d = self.hand_goal[0]
        if abs(d) > 0.1 and np.sign(d) != self.direction:
            self.flip_horizontally()

        if self.object:
            self.hand.set_position(self.shoulder + (1 - 0.5 * self.throw_charge) * self.hand_goal)

            if self.object.collider.group is Group.GUNS:
                if abs(d) > 0.1 and np.sign(d) != self.object.direction:
                    self.object.flip_horizontally()
                self.hand.angle = 0.0

            self.object.set_position(self.object.position + 0.25 * self.velocity)
            self.object.velocity = 0.5 * (self.hand.position - self.object.position) - 0.125 * gravity * basis(1)
            #self.object.angular_velocity = -0.25 * self.angle
            self.object.update(gravity, time_step, colliders)

            if norm(self.shoulder - self.object.position) > 1.5 * self.arm_length:
                self.throw_object(0.0)
            else:
                self.hand.set_position(self.object.position)
                self.hand.update(gravity, time_step, colliders)
        else:
            self.hand.set_position(self.hand.position + 0.25 * self.velocity)
            self.hand.velocity = self.shoulder + self.hand_goal - self.hand.position - 0.185 * gravity * basis(1)
            self.hand.update(gravity, time_step, colliders)
            self.hand.collider.update_collisions(colliders, [Group.PROPS, Group.GUNS])

        r = self.hand.position - self.shoulder

        if abs(r[0]) > 0.1:
            self.hand.angular_velocity = 0.5 * (np.arctan(r[1] / r[0]) - self.hand.angle)
        else:
            self.hand.angular_velocity = 0.0

        self.animate()

    def draw_limb(self, start, end, length, screen, camera, direction=1):
        color = pygame.Color('black')
        width = int(camera.zoom / 5)

        r = end - start
        r_norm = norm(r)
        joint = start + 0.5 * (r - direction * self.direction * np.sqrt(max(length - r_norm**2, 0)) * perp(r) / r_norm)

        a = camera.world_to_screen(start)
        b = camera.world_to_screen(joint)
        c = camera.world_to_screen(end)

        pygame.draw.line(screen, color, a, b, width)
        pygame.draw.line(screen, color, b, c, width)

        for x in (a, b):
            pygame.draw.circle(screen, color, x, width // 2)

    def animate(self):
        self.back_foot.animation_direction = np.sign(self.velocity[0])
        self.front_foot.animation_direction = np.sign(self.velocity[0])

        if self.on_ground:
            v = abs(self.velocity[0])
            if self.back_foot.animation != 'walk' and v > 0.1:
                self.back_foot.play_animation('walk', 3)
                self.front_foot.play_animation('walk')
            elif self.back_foot.animation != 'idle' and v < 0.1:
                self.back_foot.play_animation('idle')
                self.front_foot.play_animation('idle')
        else:
            self.back_foot.play_animation('jump')
            self.front_foot.play_animation('jump')

        if self.object:
            if self.object.collider.group is Group.GUNS:
                self.hand.image_path = 'hand_trigger'
                self.hand.image_position = self.direction * 0.1 * basis(0)
            else:
                self.hand.image_path = 'hand'
        else:
            self.hand.image_path = 'fist'
            self.hand.image_position = np.zeros(2)

    def draw(self, screen, camera, image_handler):
        self.back_foot.draw(screen, camera, image_handler)
        self.draw_limb(self.position + np.array([0.1 * self.direction, -0.5 * (1 + self.crouched)]),
                       self.back_foot.position, 1.0, screen, camera, -1)

        self.body.draw(screen, camera, image_handler)

        self.front_foot.draw(screen, camera, image_handler)
        self.draw_limb(self.position + np.array([-0.1 * self.direction, -0.5 * (1 + self.crouched)]),
                       self.front_foot.position, 1.0, screen, camera, -1)

        self.head.draw(screen, camera, image_handler)

        if self.object:
            self.object.draw(screen, camera, image_handler)

        self.draw_limb(self.shoulder, self.hand.position, 1.0, screen, camera)
        self.hand.draw(screen, camera, image_handler)

        for b in self.blood:
            b.draw(screen, camera, image_handler)

        #self.debug_draw(screen, camera, image_handler)

    def debug_draw(self, screen, camera, image_handler):
        self.collider.draw(screen, camera, image_handler)

        self.hand.debug_draw(screen, camera, image_handler)

        for part in (self.head, self.body, self.legs):
            part.debug_draw(screen, camera, image_handler)

        pygame.draw.circle(screen, image_handler.debug_color, camera.world_to_screen(self.shoulder + self.hand_goal), 2)

    def input(self, input_handler):
        if self.destroyed or self.number == -1:
            return

        controller = input_handler.controllers[self.number]

        if controller.button_pressed['A']:
            if self.on_ground:
                self.velocity[1] = 0.7
        elif controller.button_pressed['B']:
            if self.throw_charge:
                self.throw_charge = 0.0
                self.lt_pressed = True
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
            if self.object:
                if not self.rt_pressed:
                    self.attack()
                    self.rt_pressed = True
        else:
            self.rt_pressed = False

        if self.object:
            if controller.left_trigger > 0.5:
                if not self.lt_pressed:
                    self.throw_charge = min(1.0, self.throw_charge + self.charge_speed)
            else:
                self.lt_pressed = False
                if self.throw_charge:
                    self.throw_object(self.throw_charge)
                    self.throw_charge = 0.0
        else:
            self.throw_charge = 0.0

    def damage(self, amount, position, velocity):
        if self.health > 0:
            self.health -= amount
            self.blood.append(Cloud([self.position[0], position[1]], -velocity))

        if self.health <= 0:
            if not self.destroyed:
                r = self.hand.position - self.shoulder
                self.hand = Pendulum(self.shoulder, self.arm_length, np.arctan2(r[1], r[0]) + np.pi / 2)
                #self.front_foot = Pendulum(self.position - self.collider.half_height * 2 / 3, self.arm_length, 0.0)
                #self.back_foot = Pendulum(self.position - self.collider.half_height * 2 / 3, self.arm_length, 0.0)

                self.velocity += velocity + 0.5 * basis(1)
                self.head.collider.group = Group.NONE
                self.body.collider.group = Group.NONE
                self.legs.collider.group = Group.NONE
                self.bounce = 0.5
                self.destroyed = True

    def throw_object(self, velocity):
        if velocity:
            self.object.velocity[:] = normalized(self.hand_goal) * velocity * self.throw_speed

        self.object.gravity_scale = 1.0
        self.object.parent = None
        self.object = None

    def grab_object(self):
        for c in self.hand.collider.collisions:
            if c.collider.group is Group.PROPS or c.collider.group is Group.GUNS:
                if norm2(self.velocity - c.collider.parent.velocity) < 0.25:
                    self.object = c.collider.parent
                    self.object.on_ground = False
                    self.object.gravity_scale = 0.0
                    self.object.parent = self
                    break

    def attack(self):
        try:
            self.object.attack()
            #self.hand.angular_velocity = self.direction * 2
            #self.object.angular_velocity = self.direction * 2
        except AttributeError:
            pass


class Hand(PhysicsObject):
    def __init__(self, position):
        super().__init__(position)
        self.add_collider(Circle([0, 0], 0.2, Group.HANDS))
        self.gravity_scale = 0.0
        self.image_path = 'fist'
        self.size = 1.2


class Animation:
    def __init__(self, xs, ys, angles):
        self.xs = xs
        self.ys = ys
        self.angles = angles
        self.times = np.arange(len(xs))
        self.time = 0.0
        self.direction = 1

    def update(self, time_step):
        self.time += time_step
        if self.time < 0:
            self.time += self.times[-1]
        if self.time > self.times[-1]:
            self.time -= self.times[-1]

        x = np.interp(self.time, self.times, self.xs)
        y = np.interp(self.time, self.times, self.ys)

        position = np.array([x, y])
        angle = np.interp(self.time, self.times, self.angles)

        return position, angle


class Foot(GameObject):
    def __init__(self, position):
        super().__init__(position)
        self.image_path = 'foot'
        self.size = 0.8
        self.animations = dict()

        xs = 0.3 * np.ones(1)
        ys = np.zeros(1)
        angles = np.zeros(1)
        self.animations['idle'] = Animation(xs, ys, angles)

        xs = 0.3 * np.ones(1)
        ys = 0.3 * np.ones(1)
        angles = -0.25 * np.ones(1)
        self.animations['jump'] = Animation(xs, ys, angles)

        xs = 0.25 * np.array([3, 2, 1, 0, 0.5, 1, 2, 2.5])
        ys = 0.25 * np.array([0, 0, 0, 0, 0.5, 1, 1, 0.5])
        angles = 0.25 * np.array([0, 0, -1, -1, -1, -1, 0, 0])
        self.animations['walk'] = Animation(xs, ys, angles)

        self.animation = 'idle'
        self.animation_direction = 1

    def play_animation(self, name, time=0):
        self.animation = name
        self.animations[self.animation].time = time

    def update(self, time_step):
        self.image_position = np.array([self.direction * 0.15, 0])

        pos, angle = self.animations[self.animation].update(self.animation_direction * time_step)

        self.position += pos
        self.angle = self.direction * angle
