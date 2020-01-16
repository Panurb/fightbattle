import numpy as np
from numpy.linalg import norm
import pygame

from gameobject import GameObject, PhysicsObject, Destroyable, MAX_SPEED, AnimatedObject
from collider import Rectangle, Circle, Group
from helpers import norm2, basis, perp, normalized, rotate
from particle import BloodSplatter
from weapon import Shotgun


class Player(Destroyable):
    def __init__(self, position, number=0):
        super().__init__(position)
        self.goal_velocity = np.zeros(2)
        self.walk_acceleration = 0.5
        self.bounce = 0.0

        self.add_collider(Rectangle([0, 0], 0.8, 3, Group.PLAYERS))

        self.body = Body(self.position, self)
        self.head = Head(self.position + basis(1), self)

        self.back_hip = np.zeros(2)
        self.front_hip = np.zeros(2)
        self.back_foot = Foot(np.zeros(2))
        self.front_foot = Foot(np.zeros(2))
        self.leg_length = 1.0

        self.max_speed = 0.5

        self.shoulder = self.position + 0.25 * 2 / 3 * self.collider.half_height
        self.hand_goal = basis(0)
        self.arm_length = 1.0
        self.elbow = np.zeros(2)

        self.hand = Hand(self.position)
        self.hand.add_collider(Circle([0, 0], 0.2, Group.HANDS))
        self.hand.gravity_scale = 0.0

        self.back_hand = AnimatedObject(self.position, '', 1.0)

        self.object = None

        self.crouched = 0
        self.crouch_speed = 0.25

        self.lt_pressed = False
        self.rt_pressed = False

        self.throw_speed = 1.0
        self.throw_charge = 0.0
        self.charge_speed = 0.05

        self.number = number

    def flip_horizontally(self):
        super().flip_horizontally()

        self.head.flip_horizontally()

        self.hand.flip_horizontally()
        self.hand.angle += np.sign(self.hand.position[1] - self.position[1]) * self.direction * np.pi

        self.body.flip_horizontally()
        self.back_foot.flip_horizontally()
        self.front_foot.flip_horizontally()

    def update(self, gravity, time_step, colliders):
        for b in self.particle_clouds:
            b.update(gravity, time_step)
            if not b.active:
                self.particle_clouds.remove(b)

        if self.destroyed:
            PhysicsObject.update(self, gravity, time_step, colliders)
            self.head.update_active()
            if not self.head.active or not self.head.destroyed:
                self.update_active()

            if abs(self.angle) > np.pi / 2:
                self.rotate(np.sign(self.angular_velocity) * np.pi / 2 - self.angle)
                self.angular_velocity = 0.0

            if self.collider.group is Group.PLAYERS:
                colliders[Group.PLAYERS].remove(self.collider)
                self.collider.group = Group.DEBRIS
                colliders[Group.DEBRIS].append(self.collider)
                if not self.head.destroyed:
                    colliders[Group.HITBOXES].remove(self.head.collider)
                colliders[Group.HITBOXES].remove(self.body.collider)
                self.body.collider = None

            self.head.update(gravity, time_step, colliders)
        else:
            if self.velocity[1] > 0:
                self.on_ground = False

            delta_pos = self.velocity * time_step # + 0.5 * self.acceleration * time_step**2
            self.position += delta_pos

            self.collider.position += delta_pos

            self.collider.update_collisions(colliders)

            if not self.collision_enabled:
                return

            for collision in self.collider.collisions:
                if not collision.collider.parent.collision_enabled:
                    continue

                if collision.overlap[1] > 0:
                    self.on_ground = True
                    self.velocity[1] = 0.0

                self.position += collision.overlap

                self.collider.position += collision.overlap

                if not collision.overlap[1]:
                    self.velocity[0] = 0.0

            if not self.on_ground or np.any(self.goal_velocity):
                self.acceleration[:] = gravity
            else:
                self.acceleration[:] = 0.0

            if np.any(self.goal_velocity):
                self.acceleration[0] = (self.goal_velocity[0] - self.velocity[0]) * self.walk_acceleration
            else:
                self.velocity[0] *= 0.5

            self.velocity += self.acceleration * time_step

            self.speed = norm(self.velocity)
            if self.speed != 0:
                self.velocity *= min(self.speed, MAX_SPEED) / self.speed

        w = normalized(self.collider.half_width)
        h = normalized(self.collider.half_height)

        self.body.set_position(self.position - 0.5 * self.crouched * h)
        self.body.angle = self.angle

        self.shoulder = self.position + (0.15 - 0.75 * self.crouched) * h

        self.back_hip = self.position + self.direction * 0.1 * w - 0.5 * (1 + self.crouched) * h
        self.front_hip = self.position - self.direction * 0.1 * w - 0.5 * (1 + self.crouched) * h

        if not self.head.gravity_scale:
            self.head.set_position(self.position + (1 - self.crouched) * h)
            self.head.angle = self.angle

        if self.destroyed:
            for limb, joint, length in [(self.hand, self.shoulder, self.arm_length),
                                        (self.back_foot, self.back_hip, self.leg_length),
                                        (self.front_foot, self.front_hip, self.leg_length)]:
                limb.update(gravity, time_step, colliders)
                r = limb.position - joint
                r_norm = norm(r)
                if r_norm > length:
                    r *= length / r_norm
                GameObject.set_position(limb, joint + r)

            return

        self.back_foot.set_position(self.position - np.array([0.35 * self.direction, 1.5]))
        self.front_foot.set_position(self.position - np.array([0.55 * self.direction, 1.5]))
        self.back_foot.animate(time_step)
        self.front_foot.animate(time_step)

        self.collider.position[1] = self.position[1] - 0.5 * self.crouched
        self.collider.half_height[1] = 1.5 - 0.5 * self.crouched

        d = self.hand_goal[0]
        if abs(d) > 0.1 and np.sign(d) != self.direction:
            self.flip_horizontally()

        if self.object:
            self.object.set_position(self.object.position + time_step * self.velocity)
            hand_pos = self.shoulder + (1 - 0.5 * self.throw_charge) * self.hand_goal
            self.object.velocity = 0.5 * (hand_pos - self.object.position) - 0.125 * gravity * basis(1)
            self.object.update(gravity, time_step, colliders)

            if self.object.collider.group in [Group.GUNS, Group.SHIELDS, Group.SWORDS]:
                if abs(d) > 0.1 and np.sign(d) != self.object.direction:
                    self.object.flip_horizontally()
                self.hand.set_position(hand_pos)

            if self.object.collider.group in [Group.SWORDS, Group.GUNS, Group.SHIELDS]:
                if self.hand.animation is not 'idle':
                    if self.object.hit:
                        self.hand.play_animation('idle')
                    self.hand.animate(time_step)
                    self.object.set_position(self.hand.position)
                self.object.rotate(self.hand.angle - self.object.angle)

                if type(self.object) is Shotgun:
                    self.back_hand.set_position(self.object.get_grip_position())

            if norm(self.shoulder - self.object.position) > 1.5 * self.arm_length:
                self.throw_object(0.0)
            else:
                self.hand.set_position(self.object.position)
                self.hand.update(gravity, time_step, colliders)
        else:
            self.hand.set_position(self.hand.position + time_step * self.velocity)
            self.hand.velocity = self.shoulder + self.hand_goal - self.hand.position - 0.185 * gravity * basis(1)
            self.hand.update(gravity, time_step, colliders)
            self.hand.collider.update_collisions(colliders, [Group.PROPS, Group.GUNS, Group.SHIELDS, Group.SWORDS])

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
        length = np.sqrt(max(length - r_norm ** 2, 0))
        joint = start + 0.5 * r
        if r_norm != 0:
            joint -= 0.5 * direction * self.direction * length * perp(r) / r_norm

        a = camera.world_to_screen(start)
        b = camera.world_to_screen(joint)
        c = camera.world_to_screen(end)

        pygame.draw.line(screen, color, a, b, width)
        pygame.draw.line(screen, color, b, c, width)

        for x in (a, b):
            pygame.draw.circle(screen, color, x, width // 2)

    def animate(self):
        self.back_foot.animation_direction = self.direction * np.sign(self.velocity[0])
        self.front_foot.animation_direction = self.direction * np.sign(self.velocity[0])

        if self.on_ground:
            v = abs(self.goal_velocity[0])
            if self.back_foot.animation != 'walk' and v > 0:
                self.back_foot.loop_animation('walk', 3)
                self.front_foot.loop_animation('walk')
            elif self.back_foot.animation != 'idle' and v == 0:
                self.back_foot.loop_animation('idle')
                self.front_foot.loop_animation('idle')
        else:
            self.back_foot.loop_animation('jump')
            self.front_foot.loop_animation('jump')

        self.hand.image_position = np.zeros(2)

        if self.object:
            if self.object.collider.group is Group.GUNS:
                self.hand.image_path = 'hand_trigger'
                w = normalized(self.object.collider.half_width)
                self.hand.image_position = 0.08 * w * self.direction
            elif self.object.collider.group is Group.SWORDS:
                self.hand.image_path = 'fist'
            else:
                self.hand.image_path = 'hand'

            if self.hand.animation in ['attack', 'shoot', 'shotgun']:
                angle = np.arctan(self.hand_goal[1] / self.hand_goal[0])
                self.hand.animation_angle = angle

            if type(self.object) is Shotgun:
                self.back_hand.image_path = 'hand_grip'
        else:
            self.hand.image_path = 'fist'
            self.hand.loop_animation('idle')
            self.back_hand.image_path = ''

    def draw(self, screen, camera, image_handler):
        self.back_foot.draw(screen, camera, image_handler)
        self.draw_limb(self.back_hip, self.back_foot.position, 1.0, screen, camera, -1)

        if not self.destroyed and self.back_hand.image_path:
            self.draw_limb(self.shoulder + 0.25 * self.direction * basis(0), self.back_hand.position, 1.0,
                           screen, camera)

        self.body.draw(screen, camera, image_handler)

        self.front_foot.draw(screen, camera, image_handler)
        self.draw_limb(self.front_hip, self.front_foot.position, 1.0, screen, camera, -1)

        self.head.draw(screen, camera, image_handler)

        if self.object and self.object.collider:
            if self.object.collider.group is Group.SHIELDS:
                self.draw_limb(self.shoulder, self.hand.position, 1.0, screen, camera)
                self.object.draw(screen, camera, image_handler)
            elif type(self.object) is Shotgun:
                pos = self.object.get_hand_position()
                self.draw_limb(self.shoulder, pos, 1.0, screen, camera)
                self.object.draw(screen, camera, image_handler)
                self.hand.image_position = pos - self.object.position
                self.hand.draw(screen, camera, image_handler)

                self.back_hand.angle = self.object.angle
                self.back_hand.draw(screen, camera, image_handler)
            else:
                self.object.draw(screen, camera, image_handler)
                self.draw_limb(self.shoulder, self.hand.position, 1.0, screen, camera)
                self.hand.draw(screen, camera, image_handler)
        else:
            self.draw_limb(self.shoulder, self.hand.position, 1.0, screen, camera)
            self.hand.draw(screen, camera, image_handler)

        for b in self.particle_clouds:
            b.draw(screen, camera, image_handler)

    def debug_draw(self, screen, camera, image_handler):
        self.collider.draw(screen, camera, image_handler)

        self.hand.debug_draw(screen, camera, image_handler)

        self.back_foot.debug_draw(screen, camera, image_handler)
        self.front_foot.debug_draw(screen, camera, image_handler)

        pygame.draw.circle(screen, image_handler.debug_color, camera.world_to_screen(self.shoulder + self.hand_goal), 2)
        pygame.draw.circle(screen, image_handler.debug_color, camera.world_to_screen(self.shoulder), 2)

        self.head.debug_draw(screen, camera, image_handler)
        self.body.debug_draw(screen, camera, image_handler)

    def input(self, input_handler):
        if self.destroyed or self.number == -1 or self.number >= len(input_handler.controllers):
            return

        controller = input_handler.controllers[self.number]

        if controller.button_pressed['A']:
            if self.on_ground:
                self.velocity[1] = 0.5
        elif controller.button_pressed['B']:
            if self.throw_charge:
                self.throw_charge = 0.0
                self.lt_pressed = True

        self.goal_velocity[0] = (5 - 2 * self.crouched) / 5 * self.max_speed * controller.left_stick[0]

        if self.on_ground and controller.left_stick[1] < -0.5:
            self.crouched = min(1.0, self.crouched + self.crouch_speed)
        else:
            self.crouched = max(0.0, self.crouched - self.crouch_speed)

        stick_norm = norm(controller.right_stick)
        if stick_norm != 0 and self.hand.animation not in ['attack', 'shoot', 'shotgun']:
            self.hand_goal = self.arm_length * controller.right_stick / stick_norm

        if controller.right_trigger > 0.5:
            if self.object:
                if not self.rt_pressed:
                    self.attack()
                    self.rt_pressed = True
            else:
                self.grab_object()
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
                    if self.throw_charge > 0.5:
                        self.throw_object(self.throw_charge)
                    else:
                        self.throw_object(0.0)
                    self.throw_charge = 0.0
        else:
            self.throw_charge = 0.0

    def damage(self, amount, position, velocity):
        self.particle_clouds.append(BloodSplatter([self.position[0], position[1]], -0.25 * velocity, amount // 2))

        if self.health > 0:
            self.health -= amount

        if self.health <= 0 and not self.destroyed:
            self.destroy(velocity)

    def destroy(self, velocity):
        if self.destroyed:
            return

        self.hand.gravity_scale = 1.0
        self.back_foot.gravity_scale = 1.0
        self.front_foot.gravity_scale = 1.0

        self.velocity = 0.25 * velocity + 0.5 * basis(1)
        self.bounce = 0.5
        self.angular_velocity = -0.125 * np.sign(velocity[0])
        self.destroyed = True
        if self.object:
            self.throw_object(0)
        self.hand.image_path = 'hand'

    def throw_object(self, velocity):
        if velocity:
            self.object.velocity[:] = normalized(self.hand_goal) * velocity * self.throw_speed

        if self.object.collider.group is Group.SWORDS:
            self.object.rotate(-self.direction * np.pi / 2 - self.object.angle)
            self.object.timer = 0.0
        else:
            self.object.rotate(-self.object.angle)

        self.object.gravity_scale = 1.0
        self.object.parent = None
        self.object = None

    def grab_object(self):
        for c in self.hand.collider.collisions:
            if c.collider.group in [Group.PROPS, Group.GUNS, Group.SHIELDS, Group.SWORDS]:
                if norm2(self.velocity - c.collider.parent.velocity) < 0.25:
                    self.object = c.collider.parent
                    self.object.on_ground = False
                    self.object.gravity_scale = 0.0
                    self.object.parent = self
                    self.object.rotate(-self.object.angle)
                    break

    def attack(self):
        try:
            if self.hand.animation == 'idle':
                if self.object.collider.group is Group.SWORDS:
                    self.hand.play_animation('attack')
                elif self.object.collider.group is Group.GUNS:
                    if type(self.object) is Shotgun:
                        self.hand.play_animation('shotgun')
                    else:
                        self.hand.play_animation('shoot')
                self.object.attack()
        except AttributeError:
            print('Cannot attack with object', self.object)


class Head(Destroyable):
    def __init__(self, position, parent):
        super().__init__(position, image_path='head', debris_path='gib', size=0.85, debris_size=0.4, health=20,
                         parent=parent)
        self.gravity_scale = 0.0
        self.add_collider(Circle([0, 0], 0.5, Group.HITBOXES))

    def destroy(self, velocity):
        self.parent.destroy(velocity)
        super().destroy([0, -1])
        self.particle_clouds.append(BloodSplatter(self.position, [0, 0.4]))
        self.particle_clouds.append(BloodSplatter(self.position, [-0.2, 0.1], 5))
        self.particle_clouds.append(BloodSplatter(self.position, [0.2, 0.1], 5))


class Body(Destroyable):
    def __init__(self, position, parent):
        super().__init__(position, image_path='body', debris_path='gib', size=0.75, debris_size=0.5, health=100,
                         parent=parent)
        self.add_collider(Rectangle([0, -0.5], 0.8, 2, Group.HITBOXES))

    def damage(self, amount, position, velocity):
        self.parent.damage(amount, position, velocity)

    def destroy(self, velocity):
        self.parent.destroy(velocity)
        super().destroy(velocity)
        self.parent.particle_clouds.append(BloodSplatter(self.position, [0, -1]))


class Hand(PhysicsObject, AnimatedObject):
    def __init__(self, position):
        super().__init__(position, image_path='fist', size=1.2)
        self.add_collider(Circle([0, 0], 0.2, Group.HANDS))

        self.add_animation(np.zeros(1), np.zeros(1), np.zeros(1), 'idle')

        xs = np.array([-0.275, -0.125, 0.1, 0.0, -0.1, -0.2, -0.15, -0.2])
        ys = np.array([-0.05, -0.2, -0.4, -0.6, -0.55, -0.4, -0.3, -0.15])
        angles = np.pi * np.array([0.3, -0.25, -0.55, -0.5, -0.25, -0.125, 0.0, 0.125])
        self.add_animation(xs, ys, angles, 'attack')

        xs = 2 * np.array([-0.15, -0.25, -0.25, -0.25, -0.25, -0.25, -0.2, -0.1, -0.05])
        ys = 3 * np.array([0.1, 0.2, 0.18, 0.15, 0.125, 0.1, 0.15, 0.1, 0.05])
        angles = 0.5 * np.pi * np.array([0.3, 0.5, 0.55, 0.575, 0.6, 0.5, 0.45, 0.35, 0.2])
        self.add_animation(xs, ys, angles, 'shotgun')

        xs = np.array([-0.15, -0.25, -0.2, -0.1, -0.05])
        ys = np.array([0.1, 0.2, 0.15, 0.1, 0.05])
        angles = np.pi * np.array([0.3, 0.5, 0.45, 0.35, 0.2])
        self.add_animation(xs, ys, angles, 'shoot')


class Foot(PhysicsObject, AnimatedObject):
    def __init__(self, position):
        super().__init__(position, image_path='foot', size=0.8)
        self.image_position = 0.15 * basis(0)

        self.add_collider(Circle([0, 0], 0.1, Group.DEBRIS))
        self.gravity_scale = 0.0

        self.add_animation(0.3 * np.ones(1), np.zeros(1), np.zeros(1), 'idle')
        self.add_animation(0.3 * np.ones(1), 0.3 * np.ones(1), -0.25 * np.ones(1), 'jump')

        xs = 0.25 * np.array([3, 2, 1, 0, 0.5, 1, 2, 2.5])
        ys = 0.25 * np.array([0, 0, 0, 0, 0.5, 1, 1, 0.5])
        angles = 0.25 * np.array([0, 0, -1, -1, -1, -1, 0, 0])
        self.add_animation(xs, ys, angles, 'walk')
