import numpy as np
from numpy.linalg import norm
import pygame

from gameobject import GameObject, PhysicsObject, Destroyable, MAX_SPEED, AnimatedObject
from collider import Rectangle, Circle, Group
from helpers import norm2, basis, perp, normalized, rotate, polar_angle, random_unit
from particle import BloodSplatter
from weapon import Shotgun, Shield, Bow, Sword, Revolver


class Player(Destroyable):
    def __init__(self, position, controller_id=0):
        super().__init__(position)
        self.goal_velocity = np.zeros(2)
        self.walk_acceleration = 0.5
        self.bounce = 0.0

        self.add_collider(Rectangle([0, 0], 0.8, 3, Group.PLAYERS))

        self.body = Body(self.position, self)
        self.head = Head(self.position + basis(1), self)

        self.back_hip = self.position + np.array([0.1, -0.5])
        self.front_hip = self.position + np.array([-0.1, -0.5])
        self.back_foot = Foot(self.position + np.array([0.1, -1.5]))
        self.front_foot = Foot(self.position + np.array([-0.1, -1.5]))
        self.leg_length = 0.8

        self.max_speed = 0.5

        self.shoulder = self.position + 0.25 * 2 / 3 * self.collider.half_height
        self.hand_goal = basis(0)
        self.arm_length = 1.0
        self.elbow = np.zeros(2)

        self.hand = Hand(self.position)
        self.hand.add_collider(Circle([0, 0], 0.2, Group.HANDS))
        self.hand.gravity_scale = 0.0

        self.back_hand = AnimatedObject(self.position, '', 1.2)

        self.object = None

        self.crouched = 0
        self.crouch_speed = 0.25

        self.lt_pressed = False
        self.rt_pressed = False

        self.attack_charge = 0.0

        self.throw_speed = 1.0
        self.throw_charge = 0.0
        self.charge_speed = 0.05

        self.controller_id = controller_id
        self.timer = 0.0

        self.walking = False

        self.channel = pygame.mixer.Channel(self.controller_id + 1)
        self.camera_shake = np.zeros(2)

    def set_position(self, position):
        super().set_position(position)
        self.update_joints()
        self.hand.set_position(position)
        self.back_foot.set_position(self.position - np.array([0.35 * self.direction, 1.4]))
        self.front_foot.set_position(self.position - np.array([0.55 * self.direction, 1.4]))

    def reset(self, colliders):
        colliders[Group.DEBRIS].remove(self.collider)
        self.collider.group = Group.PLAYERS
        colliders[Group.PLAYERS].append(self.collider)
        self.head.reset()
        colliders[Group.HITBOXES].append(self.head.collider)
        self.body.reset()
        colliders[Group.HITBOXES].append(self.body.collider)

        self.destroyed = False
        self.health = 100
        self.rotate(-self.angle)
        self.bounce = 0.0
        self.front_foot.reset()
        self.back_foot.reset()
        self.active = True

    def flip_horizontally(self):
        super().flip_horizontally()

        self.head.flip_horizontally()

        self.back_hand.flip_horizontally()

        self.hand.flip_horizontally()
        self.hand.angle += np.sign(self.hand.position[1] - self.position[1]) * self.direction * np.pi

        self.body.flip_horizontally()
        self.back_foot.flip_horizontally()
        self.front_foot.flip_horizontally()

    def update(self, gravity, time_step, colliders):
        if norm2(self.camera_shake) < 0.1:
            self.camera_shake = np.zeros(2)
        else:
            self.camera_shake = -0.5 * self.camera_shake

        for b in self.particle_clouds:
            b.update(gravity, time_step)
            if not b.active:
                self.particle_clouds.remove(b)

        if self.destroyed:
            self.update_ragdoll(gravity, time_step, colliders)
            self.update_joints()
            return

        if self.velocity[1] != 0:
            self.on_ground = False

        delta_pos = self.velocity * time_step # + 0.5 * self.acceleration * time_step**2
        self.position += delta_pos

        self.collider.position += delta_pos

        self.collider.update_collisions(colliders)

        if not self.collision_enabled:
            return

        for collision in self.collider.collisions:
            obj = collision.collider.parent
            if not obj.collision_enabled:
                continue

            if obj.collider.group is Group.PLATFORMS:
                if self.position[1] - self.collider.half_height[1] - delta_pos[1] \
                        < obj.position[1] + obj.collider.half_height[1] + 0.5 * gravity[1] * time_step**2:
                    continue

            if abs(self.velocity[1]) > 0.1:
                self.sounds.append('bump')

            if collision.overlap[1] > 0:
                self.on_ground = True
                self.velocity[1] = 0.0
            elif collision.overlap[1] < 0:
                self.velocity[1] *= -1

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

        self.angle = -0.5 * self.velocity[0]

        self.update_joints()

        self.back_foot.set_position(self.position - np.array([0.35 * self.direction, 1.4]))
        self.front_foot.set_position(self.position - np.array([0.55 * self.direction, 1.4]))
        self.back_foot.animate(time_step)
        self.front_foot.animate(time_step)

        self.collider.position[1] = self.position[1] - 0.5 * self.crouched
        self.collider.half_height[1] = 1.5 - 0.5 * self.crouched

        d = self.hand_goal[0]
        if abs(d) > 0.1 and np.sign(d) != self.direction:
            self.flip_horizontally()

        r = self.hand.position - self.shoulder

        if abs(r[0]) > 0.1:
            self.hand.angular_velocity = 0.5 * (np.arctan(r[1] / r[0]) - self.hand.angle)
        else:
            self.hand.angular_velocity = 0.0

        self.animate()

        if self.object:
            self.grab_object()

            self.object.set_position(self.object.position + time_step * self.velocity)
            hand_pos = self.shoulder + (1 - 0.5 * self.throw_charge) * self.hand_goal
            self.object.velocity = 0.5 * (hand_pos - self.object.position) - 0.125 * gravity * basis(1)

            if not self.object.collider:
                self.throw_object()
                return

            if self.object.collider.group in [Group.GUNS, Group.SHIELDS, Group.SWORDS]:
                if abs(d) > 0.1 and np.sign(d) != self.object.direction:
                    self.object.flip_horizontally()
                self.hand.set_position(hand_pos)

                if self.hand.animation is not 'idle':
                    if self.object.hit:
                        self.hand.play_animation('idle')
                    self.hand.animate(time_step)
                    self.object.set_position(self.hand.position)

                    # experimental
                    PhysicsObject.update(self.object, gravity, time_step, colliders)
                    self.hand.set_position(self.object.position)

                self.object.rotate(self.hand.angle - self.object.angle)

                if self.back_hand.image_path:
                    self.back_hand.set_position(self.object.get_grip_position())

            if norm(self.shoulder - self.object.position) > 1.6 * self.arm_length:
                self.throw_object(0.0)
            else:
                self.hand.set_position(self.object.position)
                self.hand.update(gravity, time_step, colliders)
        else:
            self.hand.set_position(self.hand.position + time_step * self.velocity)
            self.hand.velocity = self.shoulder + self.hand_goal - self.hand.position - 0.185 * gravity * basis(1)
            self.hand.update(gravity, time_step, colliders)
            self.hand.collider.update_collisions(colliders, [Group.PROPS, Group.GUNS, Group.SHIELDS, Group.SWORDS])

    def update_joints(self):
        w = normalized(self.collider.half_width)
        h = normalized(self.collider.half_height)

        offset = -0.5 * self.angle * w if not self.destroyed else 0.0

        self.body.set_position(self.position + offset - 0.5 * self.crouched * h)
        self.body.angle = self.angle

        self.shoulder = self.position + offset + (0.15 - 0.75 * self.crouched) * h

        self.back_hip = self.position + self.direction * 0.1 * w - 0.5 * (1 + self.crouched) * h
        self.front_hip = self.position - self.direction * 0.1 * w - 0.5 * (1 + self.crouched) * h

        if self.destroyed:
            angle_goal = self.angle
        else:
            angle_goal = np.arctan(self.hand_goal[1] / (self.hand_goal[0] + 1e-6))

        angle_goal = max(self.angle - 0.25, min(self.angle + 0.25, angle_goal))
        self.head.angle += 0.1 * (angle_goal - self.head.angle)
        self.head.set_position(self.position + 3 * offset - 0.35 * (self.head.angle - self.angle) * w + (1 - self.crouched) * h)

    def update_ragdoll(self, gravity, time_step, colliders):
        self.timer += time_step

        PhysicsObject.update(self, gravity, time_step, colliders)
        if self.collider.collisions and self.speed > 0.1:
            self.sounds.append('bump')
        self.head.update_active()
        if not self.head.active or not self.head.destroyed:
            #self.update_active()
            if self.on_ground and self.speed < 0.1:
                self.active = False

        if abs(self.angle) > np.pi / 2:
            self.rotate(np.sign(self.angular_velocity) * np.pi / 2 - self.angle)
            self.angular_velocity = 0.0

        self.head.update(gravity, time_step, colliders)

        for limb, joint, length in [(self.hand, self.shoulder, self.arm_length),
                                    (self.back_foot, self.back_hip, self.leg_length),
                                    (self.front_foot, self.front_hip, self.leg_length)]:
            limb.update(gravity, time_step, colliders)
            r = limb.position - joint
            r_norm = norm(r)
            if r_norm > length:
                r *= length / r_norm
            GameObject.set_position(limb, joint + r)

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
            if isinstance(self.object, Destroyable):
                if self.object.destroyed:
                    return

            if type(self.object) is Bow:
                if self.attack_charge > 0.0:
                    self.hand.image_path = 'hand_arrow'
                else:
                    self.hand.image_path = 'hand'
                self.hand.image_position = self.object.hand_position.copy()
                self.hand.image_position[0] *= self.direction
                self.back_hand.image_path = 'fist_front'
            elif self.object.collider.group is Group.GUNS:
                self.hand.image_path = 'hand_trigger'
                self.hand.image_position = self.object.hand_position.copy()
                self.hand.image_position[0] *= self.direction
            elif self.object.collider.group is Group.SWORDS:
                self.hand.image_path = 'fist'
            else:
                self.hand.image_path = 'hand'

            if self.hand.animation in ['sword', 'pistol', 'shotgun']:
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
        self.draw_limb(self.back_hip, self.back_foot.position, self.leg_length, screen, camera, -1)

        if not self.destroyed and self.back_hand.image_path:
            self.draw_limb(self.shoulder + 0.25 * self.direction * basis(0), self.back_hand.position, 1.0,
                           screen, camera)

        self.body.draw(screen, camera, image_handler)

        self.front_foot.draw(screen, camera, image_handler)
        self.draw_limb(self.front_hip, self.front_foot.position, self.leg_length, screen, camera, -1)

        self.head.draw(screen, camera, image_handler)

        if self.object and self.object.collider:
            if self.object.collider.group is Group.SHIELDS:
                self.draw_limb(self.shoulder, self.hand.position, self.arm_length, screen, camera)
                self.object.draw(screen, camera, image_handler)
            elif self.back_hand.image_path:
                pos = self.object.get_hand_position()
                self.draw_limb(self.shoulder, pos, self.arm_length, screen, camera)

                if type(self.object) is Bow and self.attack_charge:
                    self.object.arrow.draw(screen, camera, image_handler)

                self.object.draw(screen, camera, image_handler)

                self.back_hand.angle = self.object.angle
                self.back_hand.draw(screen, camera, image_handler)

                self.hand.draw(screen, camera, image_handler)
            else:
                self.object.draw(screen, camera, image_handler)
                self.draw_limb(self.shoulder, self.hand.position, self.arm_length, screen, camera)
                self.hand.draw(screen, camera, image_handler)
        else:
            self.draw_limb(self.shoulder, self.hand.position, self.arm_length, screen, camera)
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
        if self.destroyed or self.controller_id == -1 or self.controller_id >= len(input_handler.controllers):
            return

        controller = input_handler.controllers[self.controller_id]

        if controller.button_pressed['A']:
            if self.on_ground:
                self.velocity[1] = 0.65
                self.sounds.append('jump')
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
        if stick_norm != 0 and self.hand.animation not in ['sword', 'pistol', 'shotgun']:
            self.hand_goal = self.arm_length * controller.right_stick / stick_norm

        if controller.right_trigger > 0.5:
            if self.object:
                if not self.rt_pressed:
                    if type(self.object) is Bow:
                        # FIXME
                        if self.object.timer == 0.0:
                            if self.attack_charge == 0:
                                self.sounds.append('bow_pull')
                            self.attack_charge = min(1.0, self.attack_charge + self.charge_speed)
                    else:
                        self.attack()
                        self.rt_pressed = True
            else:
                self.attack_charge = 0.0
                self.grab_object()
                self.rt_pressed = True
        else:
            self.rt_pressed = False
            if self.attack_charge:
                self.attack()
                self.attack_charge = 0.0

        if self.object:
            if controller.left_trigger > 0.5:
                if not self.lt_pressed:
                    # FIXME
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

    def damage(self, amount, position, velocity, colliders, player=None):
        self.sounds.append('hit')

        n = max(amount // 4, 1)
        self.particle_clouds.append(BloodSplatter([self.position[0], position[1]], -0.1 * velocity, n))

        if self.health > 0:
            self.health -= amount

        if self.health <= 0 and not self.destroyed:
            self.destroy(velocity, colliders)

    def destroy(self, velocity, colliders):
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
        self.timer = 0.0

        colliders[Group.PLAYERS].remove(self.collider)
        self.collider.group = Group.DEBRIS
        colliders[Group.DEBRIS].append(self.collider)
        if not self.head.destroyed:
            colliders[Group.HITBOXES].remove(self.head.collider)
            self.head.collider = None
        colliders[Group.HITBOXES].remove(self.body.collider)
        self.body.collider = None

    def throw_object(self, velocity=0.0):
        self.object.velocity[:] = normalized(self.hand_goal) * velocity * self.throw_speed

        # TODO: purk fix
        if self.object.collider:
            if type(self.object) in [Sword, Bow]:
                self.object.rotate(-self.direction * np.pi / 2 - self.object.angle)
                self.object.timer = 0.0
            elif type(self.object) is Shield:
                self.object.rotate(-self.direction * np.pi / 2 - self.object.angle)
            else:
                self.object.rotate(-self.object.angle)

        self.object.gravity_scale = 1.0
        self.object.parent = None
        self.object = None

    def grab_object(self):
        for c in self.hand.collider.collisions:
            if c.collider.group in [Group.PROPS, Group.GUNS, Group.SHIELDS, Group.SWORDS]:
                if norm2(self.shoulder - c.collider.position) > 1.5**2:
                    continue

                if abs(self.speed - c.collider.parent.speed) < 0.25:
                    self.object = c.collider.parent
                    self.object.on_ground = False
                    self.object.gravity_scale = 0.0
                    if self.object.parent and self.object.parent is not self:
                        self.object.parent.throw_object()
                    self.object.parent = self
                    self.object.rotate(-self.object.angle)
                    break

    def attack(self):
        try:
            if self.hand.animation == 'idle':
                t = type(self.object)
                if t is Sword:
                    self.hand.play_animation('sword')
                elif t is Shotgun:
                    self.hand.play_animation('shotgun')
                    self.sounds.append('shotgun')
                elif t is Revolver:
                    self.hand.play_animation('pistol')
                self.object.attack()
                if t is not Sword:
                    self.camera_shake = 20 * random_unit()
        except AttributeError:
            print('Cannot attack with object', self.object)

    def play_sounds(self, sound_handler):
        '''
        if not self.destroyed:
            if self.on_ground and abs(self.velocity[0]) > 0.1:
                if not self.walking:
                    self.channel.play(sound_handler.sounds['walk'], -1)
                    self.walking = True
            else:
                self.channel.stop()
                self.walking = False
        else:
            self.channel.stop()
        '''

        super().play_sounds(sound_handler)


class Head(Destroyable):
    def __init__(self, position, parent):
        super().__init__(position, image_path='head', debris_path='gib', size=0.85, debris_size=0.4, health=20,
                         parent=parent)
        self.reset()

    def reset(self):
        self.gravity_scale = 0.0
        self.add_collider(Circle([0, 0], 0.5, Group.HITBOXES))
        self.destroyed = False
        self.health = 20
        self.active = True

    def damage(self, amount, position, velocity, colliders):
        super().damage(amount, position, velocity, colliders)
        self.parent.damage(amount, position, velocity, colliders)

    def destroy(self, velocity, colliders):
        self.parent.destroy(velocity, colliders)
        super().destroy([0, -1], colliders)
        self.particle_clouds.append(BloodSplatter(self.position, [0, 0.4], 5))


class Body(Destroyable):
    def __init__(self, position, parent):
        super().__init__(position, image_path='body', debris_path='gib', size=0.75, debris_size=0.5, health=100,
                         parent=parent)
        self.reset()

    def reset(self):
        self.add_collider(Rectangle([0, -0.5], 0.8, 2, Group.HITBOXES))
        self.destroyed = False
        self.health = 100

    def damage(self, amount, position, velocity, colliders):
        self.parent.damage(amount, position, velocity, colliders)

    def destroy(self, velocity, colliders):
        self.parent.destroy(velocity)
        super().destroy(velocity, colliders)


class Hand(PhysicsObject, AnimatedObject):
    def __init__(self, position):
        super().__init__(position, image_path='fist', size=1.2)
        self.add_collider(Circle([0, 0], 0.2, Group.HANDS))

        self.add_animation(np.zeros(1), np.zeros(1), np.zeros(1), 'idle')

        xs = np.array([-0.125, 0.1, 0.0, -0.1, -0.2, -0.15, -0.2])
        ys = np.array([-0.2, -0.4, -0.6, -0.55, -0.4, -0.3, -0.15])
        angles = np.pi * np.array([-0.25, -0.55, -0.5, -0.25, -0.125, 0.0, 0.125])
        self.add_animation(xs, ys, angles, 'sword')

        xs = 2 * np.array([-0.15, -0.25, -0.25, -0.25, -0.25, -0.25, -0.2, -0.1, -0.05])
        ys = 3 * np.array([0.1, 0.2, 0.18, 0.15, 0.125, 0.1, 0.15, 0.1, 0.05])
        angles = 0.5 * np.pi * np.array([0.3, 0.5, 0.55, 0.575, 0.6, 0.5, 0.45, 0.35, 0.2])
        self.add_animation(xs, ys, angles, 'shotgun', image='hand_trigger')

        xs = np.array([-0.15, -0.25, -0.2, -0.1, -0.05])
        ys = np.array([0.1, 0.2, 0.15, 0.1, 0.05])
        angles = np.pi * np.array([0.3, 0.5, 0.45, 0.35, 0.2])
        self.add_animation(xs, ys, angles, 'pistol', image='hand_trigger')


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

    def reset(self):
        self.gravity_scale = 0.0
        self.active = True
