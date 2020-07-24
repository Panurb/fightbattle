import numpy as np
from numpy.linalg import norm

from drawable import Drawable
from gameobject import PhysicsObject, Destroyable, MAX_SPEED, AnimatedObject
from collider import Rectangle, Circle, Group
from helpers import norm2, basis, perp, normalized, polar_angle, random_unit, polar_to_cartesian
from particle import BloodSplatter, Dust
from weapon import Shotgun, Bow, Axe, Weapon, Grenade


class Player(Destroyable):
    def __init__(self, position=(0, 0), controller_id=0, network_id=0):
        super().__init__(position)
        self.goal_crouched = 0.0
        self.goal_velocity = np.zeros(2)
        self.walk_acceleration = 3.5
        self.air_acceleration = 2.0
        self.bounce = 0.0
        self.friction = 7.0

        self.add_collider(Rectangle([0, 0], 0.8, 3, Group.PLAYERS))

        self.body_type = 'speedo'
        self.head_type = 'bald'
        self.team = ''

        self.body = Body(self.position, self)
        self.head = Head(self.position + basis(1), self)

        self.back_hip = self.position + np.array([0.1, -0.5])
        self.front_hip = self.position + np.array([-0.1, -0.5])
        self.back_foot = Foot(self.position - np.array([0.35, 1.4]), self)
        self.front_foot = Foot(self.position - np.array([0.55, 1.4]), self, True)

        self.walk_speed = 5.0
        self.run_speed = 8.0
        self.running = False

        self.shoulder = self.position + 0.25 * 2 / 3 * self.collider.half_height \
            - 0.1 * self.direction * self.collider.half_width
        self.hand_goal = basis(0)
        self.elbow = np.zeros(2)

        self.hand = Hand(self.position, self, True)
        self.back_hand = Hand(self.position, self, False)

        self.object = None

        self.crouched = 0
        self.crouch_speed = 10.0

        self.lt_pressed = False
        self.rt_pressed = False

        self.attack_charge = 0.0

        self.throw_speed = 15.0
        self.throw_charge = 0.0
        self.charge_speed = 3.0

        self.controller_id = controller_id
        self.network_id = network_id
        self.timer = 0.0

        self.grabbing = False
        self.grab_delay = 0.5
        self.grab_timer = 0.0

        self.jump_speed = 16.0
        self.fall_damage = 10
        self.fall_damage_speed = 20.0

        self.charging_attack = False
        self.charging_throw = False

    def delete(self):
        super().delete()
        self.head.delete()
        self.body.delete()
        self.hand.delete()
        self.front_foot.delete()
        self.back_foot.delete()

    def get_data(self):
        return (self.network_id, ) + super().get_data()[1:] + (self.hand.position[0], self.hand.position[1],
                                                               self.crouched)

    def apply_data(self, data):
        super().apply_data(data)
        self.hand.set_position(np.array(data[-3:-1]))
        self.crouched = data[-1]

        self.hand_goal[:] = self.hand.position - self.shoulder

        self.body.rotate(-0.05 * self.velocity[0] - 0.5 * self.direction * self.crouched - self.body.angle)
        self.update_joints()

        self.animate(0.0)

    def set_position(self, position):
        super().set_position(position)
        self.update_joints()
        if not self.destroyed:
            self.hand.set_position(position)
            self.back_foot.set_position(self.position - np.array([0.35 * self.direction, 1.4]))
            self.front_foot.set_position(self.position - np.array([0.55 * self.direction, 1.4]))

    def reset(self, colliders):
        self.collider.clear_occupied_squares(colliders)

        self.collider.group = Group.PLAYERS
        self.head.reset(colliders)
        self.body.reset(colliders)
        self.hand.reset(colliders)
        self.front_foot.reset(colliders)
        self.back_foot.reset(colliders)
        self.hand.set_position(self.position)

        self.destroyed = False
        self.health = 100
        self.rotate(-self.angle)
        self.collider.half_width = np.round(self.collider.half_width, 3)
        self.collider.half_height = np.round(self.collider.half_height, 3)
        self.bounce = 0.0
        self.active = True
        self.drop_object()

        for p in self.particle_clouds:
            p.delete()
        self.particle_clouds.clear()

    def set_spawn(self, level, players):
        i = 0
        max_dist = 0.0
        for j, s in enumerate([s for s in level.player_spawns]):
            if len(players) == 1:
                break

            if s.team != self.team:
                continue

            min_dist = np.inf
            for p in players.values():
                min_dist = min(min_dist, norm2(s.position - p.position))
            if min_dist > max_dist:
                max_dist = min_dist
                i = j

        self.set_position(level.player_spawns[i].position)

    def flip_horizontally(self):
        super().flip_horizontally()

        self.head.flip_horizontally()

        self.back_hand.flip_horizontally()

        self.hand.flip_horizontally()
        self.hand.angle += np.sign(self.hand.position[1] - self.position[1]) * self.direction * np.pi

        self.body.flip_horizontally()
        self.back_foot.flip_horizontally()
        self.front_foot.flip_horizontally()

    def get_acceleration(self, gravity):
        acceleration = min(2, max(1, abs(2 * self.velocity[1]))) * self.gravity_scale * gravity

        if self.on_ground:
            if np.any(self.goal_velocity[0]):
                acceleration[0] = (self.goal_velocity[0] - self.velocity[0]) * self.walk_acceleration
            else:
                acceleration[0] = (self.goal_velocity[0] - self.velocity[0]) * self.friction
        else:
            if np.any(self.goal_velocity[0]):
                acceleration[0] = (self.goal_velocity[0] - self.velocity[0]) * self.air_acceleration

        return acceleration

    def update(self, gravity, time_step, colliders):
        if self.health <= 0:
            self.destroy(colliders)

        for p in self.particle_clouds:
            p.update(gravity, time_step)
            if not p.active:
                self.particle_clouds.remove(p)

        if self.destroyed:
            self.update_ragdoll(gravity, time_step, colliders)
            self.update_joints()
            return

        self.grab_timer = max(0, self.grab_timer - time_step)

        if self.velocity[1] != 0:
            self.on_ground = False

        self.speed = norm(self.velocity)
        if self.speed > MAX_SPEED:
            self.velocity *= MAX_SPEED / self.speed

        delta_pos = self.velocity * time_step + 0.5 * self.acceleration * time_step**2
        self.position += delta_pos
        self.collider.position += delta_pos

        self.collider.update_occupied_squares(colliders)

        self.collider.update_collisions(colliders)

        if not self.collision_enabled:
            return

        for collision in self.collider.collisions:
            collider = collision.collider

            if collider.group in {Group.PLATFORMS, Group.PROPS}:
                if type(collider) is Circle:
                    continue

                bottom = self.collider.position[1] - delta_pos[1] - self.collider.half_height[1]
                platform_top = collider.position[1] + collider.axis_half_width(basis(1))
                if bottom < platform_top - 0.05:
                    continue

            if collision.overlap[1] > 0:
                if self.velocity[1] < -5:
                    self.goal_crouched = -0.005 * self.velocity[1] / time_step
                    self.sounds.add('bump')
                    self.sounds.add('walk')
                    if self.dust:
                        self.particle_clouds.append(Dust(self.position - self.collider.half_height,
                                                         -0.2 * self.velocity, 5))

                    if self.velocity[1] < -self.fall_damage_speed:
                        self.sounds.add('hit')
                        self.damage(self.fall_damage * self.velocity[1], colliders)

                self.on_ground = True
                if type(collision.collider) is not Circle:
                    self.velocity[1] = 0.0
            elif collision.overlap[1] < 0:
                if self.velocity[1] > 0.1:
                    self.sounds.add('bump')
                self.velocity[1] *= -1

            self.position += collision.overlap
            self.collider.position += collision.overlap

            if not collision.overlap[1]:
                self.velocity[0] = 0.0

        acc_old = self.acceleration.copy()
        self.acceleration[:] = self.get_acceleration(gravity)
        self.velocity += 0.5 * (acc_old + self.acceleration) * time_step

        self.crouched += (self.goal_crouched - self.crouched) * self.crouch_speed * time_step
        self.crouched = min(1, self.crouched)

        self.body.rotate(-0.05 * self.velocity[0] - 0.5 * self.direction * self.crouched - self.body.angle)

        self.update_joints()

        self.collider.position[1] = self.position[1] - 0.5 * self.crouched
        self.collider.half_height[1] = 1.5 - 0.5 * self.crouched

        d = self.hand_goal[0]
        if abs(d) > 0.1 and np.sign(d) != self.direction:
            self.flip_horizontally()

        self.animate(time_step)

        if self.object:
            if not self.object.collider:
                self.drop_object()
                return

            if self.back_hand.image_path:
                self.back_hand.set_position(self.object.get_grip_position())

            if self.charging_throw:
                self.throw_charge = min(1.0, self.throw_charge + self.charge_speed * time_step)

            self.object.set_position(self.object.position + delta_pos)
            hand_pos = self.shoulder + (1 - 0.5 * self.throw_charge) * self.hand_goal
            self.object.acceleration = 100 / self.mass * (hand_pos - self.object.position) \
                - 20 * self.object.velocity

            r = self.object.position - self.shoulder
            goal_angle = np.arctan(r[1] / r[0]) + self.direction * self.throw_charge
            self.object.angular_acceleration = 100 / self.mass * (goal_angle - self.object.angle) \
                - 10 * self.object.angular_velocity

            if self.object.direction != self.direction:
                self.object.flip_horizontally()
                self.object.rotate(np.sign(self.hand_goal[1]) * self.direction * np.pi)

            if self.object.group is not Group.PROPS:
                if type(self.object) is Bow:
                    if self.charging_attack:
                        self.attack_charge = min(1.0, self.attack_charge + time_step * self.object.charge_speed)
                        self.object.attack_charge = self.attack_charge

            if norm2(self.shoulder - self.object.position) > (1.6 * self.hand.length)**2:
                if isinstance(self.object, Weapon):
                    self.object.set_position(self.position)
                    self.object.collider.update_occupied_squares(colliders)
                else:
                    self.drop_object()
                    return
            else:
                self.hand.rotate(self.object.angle - self.hand.angle)

            self.object.update(gravity, time_step, colliders)

            self.hand.set_position(self.object.position)
        else:
            self.hand.set_position(self.hand.position + delta_pos)
            self.hand.velocity = 10 * (self.shoulder + self.hand_goal - self.hand.position)
            self.hand.velocity -= 0.008 * gravity * basis(1)

            r = self.hand.position - self.shoulder
            goal_angle = np.arctan(r[1] / r[0])
            if abs(r[0]) > 0.1:
                self.hand.angular_velocity = 5 * (goal_angle - self.hand.angle)
            else:
                self.hand.angular_velocity = 0.0

            self.hand.update(gravity, time_step, colliders)
            self.hand.collider.update_occupied_squares(colliders)
            if self.grabbing:
                self.hand.collider.update_collisions(colliders, {Group.PROPS, Group.WEAPONS, Group.SHIELDS})
                self.grab_object()

    def update_joints(self):
        w = polar_to_cartesian(1, self.body.angle)
        h = perp(w)
        w *= self.direction

        if self.on_ground:
            foot_offset = 0.5**self.running * 0.3 * (self.front_foot.relative_position[1]
                                                     + self.back_foot.relative_position[1]) * basis(1)
        else:
            foot_offset = 0.0

        self.body.set_position(self.position - 0.5 * self.crouched * basis(1) + foot_offset)

        self.shoulder = self.body.position + 0.15 * (1 - self.crouched) * h - 0.2 * w

        self.back_hip = self.body.position + 0.1 * w - 0.45 * h
        self.front_hip = self.body.position - 0.1 * w - 0.45 * h

        if self.destroyed:
            angle_goal = self.body.angle
        else:
            angle_goal = np.arctan(self.hand_goal[1] / (self.hand_goal[0] + 1e-6))

        angle_goal = max(self.body.angle - 0.25, min(self.body.angle + 0.25, angle_goal))
        self.head.angle += 0.1 * (angle_goal - self.head.angle)
        self.head.set_position(self.body.position
                               - (1 - self.crouched) * 0.35 * (self.head.angle - self.body.angle) * w * self.direction
                               + 0.2 * self.crouched * w + (1 - 0.5 * self.crouched) * h)

    def update_ragdoll(self, gravity, time_step, colliders):
        self.timer += time_step

        PhysicsObject.update(self, gravity, time_step, colliders)

        self.head.update_active()
        if not self.head.active or not self.head.destroyed:
            if self.on_ground and self.speed < 0.1:
                self.active = False

        self.body.rotate(self.angle - self.body.angle)
        self.head.update(gravity, time_step, colliders)

        self.update_limb(gravity, time_step, colliders, self.hand, self.shoulder, self.hand.length)
        self.update_limb(gravity, time_step, colliders, self.back_foot, self.back_hip, self.back_foot.length)
        self.update_limb(gravity, time_step, colliders, self.front_foot, self.front_hip, self.front_foot.length)

        angle = np.round(polar_angle(self.velocity), 2) + 0.5 * (1 + self.direction) * np.pi
        self.hand.rotate(angle - self.hand.angle)
        self.front_foot.rotate(angle - self.front_foot.angle)
        self.back_foot.rotate(angle - self.back_foot.angle)

    def update_limb(self, gravity, time_step, colliders, limb, joint, length):
        limb.update(gravity, time_step, colliders)
        r = limb.position - joint
        r_norm = norm(r)
        if r_norm > length:
            r *= length / r_norm
        limb.set_position(joint + r)

    def animate(self, time_step):
        self.back_foot.set_position(self.position - np.array([0.35 * self.direction + 0.05 * self.velocity[0]
                                                              + 0.1 * self.direction * self.crouched, 1.4]))
        self.front_foot.set_position(self.position - np.array([0.55 * self.direction + 0.05 * self.velocity[0]
                                                               + 0.1 * self.direction * self.crouched, 1.4]))
        self.back_foot.animate(time_step)
        self.front_foot.animate(time_step)

        self.back_foot.animation_direction = 0.5**self.running * 0.25 * self.direction * self.velocity[0] if self.on_ground else 1
        self.front_foot.animation_direction = 0.5**self.running * 0.25 * self.direction * self.velocity[0] if self.on_ground else 1

        self.hand.image_position = np.zeros(2)
        if isinstance(self.object, Weapon):
            self.hand.image_position[:] = self.object.hand_position
            self.hand.image_position[0] *= self.direction

        if self.on_ground:
            if abs(self.goal_velocity[0]) > 0:
                if self.running and abs(self.velocity[0]) > self.walk_speed:
                    self.back_foot.loop_animation('run', 3.5)
                    self.front_foot.loop_animation('run')
                else:
                    self.back_foot.loop_animation('walk', 3.5)
                    self.front_foot.loop_animation('walk')

                anim = self.back_foot.current_animation()
                if anim.time - self.back_foot.animation_direction * time_step < 0.3 < anim.time:
                    self.sounds.add('walk')
                elif anim.time - self.back_foot.animation_direction * time_step > 0.3 > anim.time:
                    self.sounds.add('walk')

                anim = self.front_foot.current_animation()
                if anim.time - self.front_foot.animation_direction * time_step < 0.25 < anim.time:
                    self.sounds.add('walk')
                elif anim.time - self.front_foot.animation_direction * time_step > 0.25 > anim.time:
                    self.sounds.add('walk')
            else:
                self.back_foot.loop_animation('idle')
                self.front_foot.loop_animation('idle')
        else:
            if self.back_foot.animation != 'jump':
                self.back_foot.play_animation('jump')
                self.front_foot.play_animation('jump')

        if self.object:
            if isinstance(self.object, Destroyable):
                if self.object.destroyed:
                    return

            if type(self.object) is Bow:
                if self.attack_charge > 0.0:
                    self.hand.image_path = 'hand_arrow'
                else:
                    self.hand.image_path = 'hand'
                self.back_hand.image_path = 'fist_front'
            elif type(self.object) is Grenade:
                self.hand.image_path = 'fist'
            elif self.object.collider.group is Group.WEAPONS:
                self.hand.image_path = 'hand_trigger'
            elif self.object.collider.group in {Group.SHIELDS}:
                self.hand.image_path = 'fist'
            else:
                self.hand.image_path = 'hand'

            if type(self.object) is Shotgun:
                self.back_hand.image_path = 'hand_grip'
        else:
            self.hand.image_path = 'hand' if self.grabbing else 'fist'
            self.back_hand.image_path = ''
            self.back_hand.set_visibility(False)

    def draw(self, batch, camera, image_handler):
        self.back_foot.draw(batch, camera, image_handler)
        self.body.draw(batch, camera, image_handler)
        self.front_foot.draw(batch, camera, image_handler)
        self.head.draw(batch, camera, image_handler)
        self.hand.draw(batch, camera, image_handler)

        if self.object and self.object.collider:
            self.object.draw(batch, camera, image_handler)

            if self.back_hand.image_path:
                self.back_hand.set_visibility(True)
                if type(self.object) is Bow:
                    if self.attack_charge:
                        self.object.arrow.draw(batch, camera, image_handler)

                self.back_hand.angle = self.object.angle
                self.back_hand.draw(batch, camera, image_handler)

        for b in self.particle_clouds:
            b.draw(batch, camera, image_handler)

    def draw_shadow(self, batch, camera, image_handler, light):
        self.head.draw_shadow(batch, camera, image_handler, light)
        self.body.draw_shadow(batch, camera, image_handler, light)
        self.hand.draw_shadow(batch, camera, image_handler, light)
        self.front_foot.draw_shadow(batch, camera, image_handler, light)
        self.back_foot.draw_shadow(batch, camera, image_handler, light)

    def debug_draw(self, batch, camera, image_handler):
        self.collider.draw(batch, camera, image_handler)

        self.hand.debug_draw(batch, camera, image_handler)

        self.back_foot.debug_draw(batch, camera, image_handler)
        self.front_foot.debug_draw(batch, camera, image_handler)

        self.head.debug_draw(batch, camera, image_handler)
        self.body.debug_draw(batch, camera, image_handler)

    def input(self, input_handler):
        if self.destroyed:
            return

        controller = input_handler.controllers[self.controller_id]

        if controller.button_pressed['A']:
            if self.on_ground:
                self.velocity[1] = self.jump_speed
                self.sounds.add('jump')
        if controller.button_pressed['B']:
            self.charging_throw = False
            if self.throw_charge:
                self.throw_charge = 0.0
                self.lt_pressed = True
            self.charging_attack = False
            if self.attack_charge:
                self.object.attack_charge = 0.0
                self.attack_charge = 0.0
                self.rt_pressed = True

        stick_norm = norm(controller.right_stick)
        if stick_norm != 0:
            self.hand_goal = self.hand.length * controller.right_stick / stick_norm

        if controller.button_down['X'] and not self.attack_charge and controller.left_stick[0]:
            self.goal_velocity[0] = self.run_speed * np.sign(controller.left_stick[0])
            self.goal_crouched = 0.0
            self.running = True
            if self.direction != np.sign(controller.left_stick[0]) != 0:
                self.flip_horizontally()
            self.hand_goal[:] = [self.direction * 0.7, 0.0]
        else:
            self.running = False
            self.goal_velocity[0] = (5 - 2 * self.crouched) / 5 * self.walk_speed * controller.left_stick[0]
            if self.on_ground and controller.left_stick[1] < -0.5:
                self.goal_crouched = 1.0
            else:
                self.goal_crouched = 0.0

            if controller.right_trigger > 0.5:
                if self.object:
                    if not self.rt_pressed:
                        if type(self.object) is Bow:
                            if self.object.timer == 0.0:
                                if self.attack_charge == 0:
                                    self.sounds.add('bow_pull')
                                self.charging_attack = True
                        else:
                            self.attack()
                            if not self.object.automatic:
                                self.rt_pressed = True
                else:
                    self.charging_attack = False
                    self.attack_charge = 0.0
                    self.grabbing = True
                    self.rt_pressed = True
            else:
                self.rt_pressed = False
                self.charging_attack = False
                if self.attack_charge:
                    self.attack()
                    self.attack_charge = 0.0
                self.grabbing = False

        if self.object:
            if controller.left_trigger > 0.5:
                if not self.lt_pressed:
                    self.charging_throw = True
            else:
                self.lt_pressed = False
                self.charging_throw = False
                if self.throw_charge:
                    if self.throw_charge > 0.5:
                        self.throw_object()
                    else:
                        self.drop_object()
                    self.throw_charge = 0.0
        else:
            self.throw_charge = 0.0

    def damage(self, amount, colliders):
        self.sounds.add('hit')

        self.health -= amount

        if self.health <= 0:
            self.destroy(colliders)

        return BloodSplatter

    def destroy(self, colliders):
        if self.destroyed:
            return

        self.hand.gravity_scale = 1.0
        self.back_foot.gravity_scale = 1.0
        self.front_foot.gravity_scale = 1.0

        self.velocity += 0.5 * basis(1)
        self.bounce = 0.5
        self.angular_velocity = -0.125 * np.sign(self.velocity[0])
        self.destroyed = True
        if self.object:
            self.drop_object()
        self.hand.image_path = 'hand'
        self.hand.image_position[:] = np.zeros(2)
        self.back_hand.image_path = ''
        self.back_hand.set_visibility(False)
        self.timer = 0.0

        self.collider.group = Group.DEBRIS

        if not self.head.destroyed:
            self.head.collision_enabled = False

        self.body.collision_enabled = False
        self.collider.half_height[1] = 0.75
        self.goal_velocity[0] = 0.0

    def throw_object(self):
        if not self.object:
            return

        self.object.velocity[:] = normalized(self.hand_goal) * self.throw_charge * self.throw_speed / self.object.mass
        self.object.angular_velocity = -10.0 * self.direction * self.throw_charge

        self.object.gravity_scale = 1.0
        self.object.layer = 4
        if self.object.collider:
            self.object.collider.group = Group.THROWN
        #self.object.parent = None
        self.object.grabbed = False
        self.object = None

        self.grab_timer = self.grab_delay
        self.sounds.add('swing')

    def drop_object(self):
        if not self.object:
            return

        self.object.gravity_scale = 1.0
        self.object.layer = 4
        self.object.parent = None
        self.object.grabbed = False
        self.object = None

        self.grab_timer = self.grab_delay

    def grab_object(self):
        if self.grab_timer > 0:
            return

        if self.object:
            return

        for c in self.hand.collider.collisions:
            if c.collider.group in {Group.THROWN, Group.PROPS, Group.WEAPONS, Group.SHIELDS}:
                if norm2(self.shoulder - c.collider.position) > 1.5**2:
                    continue

                self.object = c.collider.parent
                self.object.on_ground = False
                self.object.gravity_scale = 0.0
                if self.object.parent:
                    self.object.parent.drop_object()
                self.object.parent = self
                self.object.set_position(self.hand.position)
                self.object.rotate(polar_angle(self.hand_goal) - self.object.angle)
                self.object.angular_velocity = 0.0
                self.object.layer = 6 if self.object.group is Group.SHIELDS else 5
                self.object.grabbed = True
                self.sounds.add('wear')
                break

    def attack(self):
        if not isinstance(self.object, Weapon) and type(self.object) is not Grenade:
            return

        if self.object.timer == 0:
            self.object.attacked = True
            if type(self.object) not in {Axe, Bow, Grenade}:
                self.camera_shake = 20 * random_unit()


class Head(Destroyable):
    def __init__(self, position, parent):
        super().__init__(position, image_path='bald', debris_path='gib', size=0.9, debris_size=0.5, health=20,
                         parent=parent)
        self.layer = 5

    def reset(self, colliders):
        for d in self.debris:
            d.delete()
        self.debris.clear()
        for p in self.particle_clouds:
            p.delete()
        self.particle_clouds.clear()
        self.destroyed = False
        self.health = 20
        self.active = True
        self.rotate(-self.angle)
        if self.shadow_sprite:
            self.shadow_sprite.delete()
            self.shadow_sprite = None
        self.collision_enabled = True

    def damage(self, amount, colliders):
        super().damage(amount, colliders)
        self.parent.damage(5 * amount, colliders)

        return BloodSplatter

    def destroy(self, colliders):
        self.parent.destroy(colliders)
        super().destroy(colliders)
        self.particle_clouds.append(BloodSplatter(self.position, [0, 0.4], 5))

    def draw(self, batch, camera, image_handler):
        self.image_path = f'{self.parent.head_type}'
        super().draw(batch, camera, image_handler)


class Body(Destroyable):
    def __init__(self, position, parent):
        super().__init__(position, debris_path='gib', size=0.75, debris_size=0.5, parent=parent)
        self.layer = 5

    def reset(self, colliders):
        for p in self.particle_clouds:
            p.delete()
        self.particle_clouds.clear()
        self.destroyed = False
        self.rotate(-self.angle)
        if self.shadow_sprite:
            self.shadow_sprite.delete()
            self.shadow_sprite = None
        self.collision_enabled = True

    def damage(self, amount, colliders):
        self.parent.damage(amount, colliders)

        return BloodSplatter

    def destroy(self, colliders):
        self.parent.destroy(colliders)

    def draw(self, batch, camera, image_handler):
        self.image_path = f'body_{self.parent.body_type}'
        super().draw(batch, camera, image_handler)


class Limb(PhysicsObject, AnimatedObject):
    def __init__(self, position, image_path, size, parent, front, layer, shaft_layer=None, length=1.0,
                 joint_direction=1):
        super().__init__(position, image_path=image_path, size=size)
        self.layer = layer
        self.parent = parent
        self.front = front
        self.shaft_layer = layer if shaft_layer is None else shaft_layer
        self.length = length
        self.joint_direction = joint_direction

        self.dust = False
        self.gravity_scale = 0.0
        self.length = 1.0

        self.start = np.zeros(2)
        self.end = None

        self.upper = Drawable(self.position, '', size=0.85, layer=self.shaft_layer)
        self.lower = Drawable(self.position, '', size=0.85, layer=self.shaft_layer)

    def reset(self, colliders):
        self.collider.clear_occupied_squares(colliders)
        for p in self.particle_clouds:
            p.delete()
        self.particle_clouds.clear()
        if self.shadow_sprite:
            self.shadow_sprite.delete()
            self.shadow_sprite = None
        for part in [self.upper, self.lower]:
            if part.shadow_sprite:
                part.shadow_sprite.delete()
                part.shadow_sprite = None
        self.gravity_scale = 0.0
        self.active = True

    def delete(self):
        super().delete()
        self.upper.delete()
        self.lower.delete()

    def set_visibility(self, visible):
        if self.sprite:
            self.sprite.visible = visible
            self.upper.sprite.visible = visible
            self.lower.sprite.visible = visible

    def draw(self, batch, camera, image_handler):
        start = self.start.copy()
        end = self.end.copy() if self.end is not None else self.position

        r = end - start
        r_norm = norm(r)

        length = np.sqrt(max(self.length - r_norm**2, 0))
        joint = start + 0.5 * r
        if r_norm != 0:
            joint -= self.joint_direction * 0.5 * self.parent.direction * length * perp(r) / r_norm

        pos = start + 0.7 * (joint - start)
        angle = polar_angle(joint - start)

        self.upper.position[:] = pos
        self.upper.angle = angle
        self.upper.draw(batch, camera, image_handler)
        self.upper.sprite.scale_x = norm(joint - start) / self.length

        pos = 0.5 * (joint + end)
        angle = polar_angle(end - joint)
        self.lower.position[:] = pos
        self.lower.angle = angle
        self.lower.draw(batch, camera, image_handler)
        self.lower.sprite.scale_x = norm(joint - end) / self.length

        super().draw(batch, camera, image_handler)

    def draw_shadow(self, batch, camera, image_handler, light):
        super().draw_shadow(batch, camera, image_handler, light)
        self.upper.draw_shadow(batch, camera, image_handler, light)
        self.lower.draw_shadow(batch, camera, image_handler, light)


class Hand(Limb):
    def __init__(self, position, parent, front):
        shaft_layer = 6 if front else 3
        super().__init__(position, image_path='', size=1.2, parent=parent, front=front, layer=7,
                         shaft_layer=shaft_layer)

        if self.front:
            self.add_collider(Circle([0, 0], 0.3, Group.HANDS))
            self.lower.layer += 1

        self.band = None

    def delete(self):
        super().delete()
        if self.band:
            self.band.delete()

    def draw(self, batch, camera, image_handler):
        self.start = self.parent.shoulder
        self.end = self.position
        if not self.front:
            self.start = self.parent.shoulder + 0.25 * self.parent.direction * basis(0)
        else:
            if self.parent.object and self.parent.object.collider:
                if self.parent.back_hand.image_path:
                    self.end = self.parent.object.get_hand_position()

        self.upper.image_path = f'upper_arm_{self.parent.body_type}'
        self.lower.image_path = f'lower_arm_{self.parent.body_type}'

        if self.front and not not self.band and self.parent.team:
            self.band = Drawable(self.position, '', layer=self.shaft_layer+1)

        if self.band:
            self.band.image_path = f'{self.parent.team}_band'
            self.band.position = self.upper.position
            self.band.angle = self.upper.angle
            self.band.draw(batch, camera, image_handler)

        super().draw(batch, camera, image_handler)


class Foot(Limb):
    def __init__(self, position, parent, front=False):
        super().__init__(position, image_path='', size=0.8, parent=parent, front=front, layer=5, length=0.95,
                         joint_direction=-1)
        self.image_position = 0.15 * basis(0)

        self.add_collider(Circle([0, 0], 0.1, Group.DEBRIS))

        self.add_animation(0.3 * np.ones(1), np.zeros(1), np.zeros(1), 'idle')

        xs = 0.3 * np.ones(4)
        ys = np.array([0, 0.25, 0.3, 0.32])
        angles = np.array([0, -0.25, -0.25, -0.25])
        self.add_animation(xs, ys, angles, 'jump')

        xs = 0.25 * np.array([3, 2, 1, 0, 0.5, 1, 2, 2.5, 3])
        ys = 0.4 * np.array([0, 0, 0, 0, 0.5, 1, 1, 0.5, 0])
        angles = 0.5 * np.array([0, 0, 0, 0, -1, -1, -1, 0, 0])
        self.add_animation(xs, ys, angles, 'walk')

        xs = 0.25 * np.array([4, 3.5, 2, -0.5, -1, -0.5, 0, 3.5, 4]) + 0.15
        ys = 0.25 * np.array([3, 2, 0, 1, 3, 3.5, 2.5, 2.75, 3])
        angles = np.array([0.5, 0.25, 0, -0.5, -2, -1.5, -1, 0.25, 0.5])
        self.add_animation(xs, ys, angles, 'run')

        self.loop_animation('idle')

    def draw(self, batch, camera, image_handler):
        self.start = self.parent.front_hip if self.front else self.parent.back_hip
        self.image_path = f'foot_{self.parent.body_type}'
        self.upper.image_path = f'upper_leg_{self.parent.body_type}'
        self.lower.image_path = f'lower_leg_{self.parent.body_type}'

        super().draw(batch, camera, image_handler)

    def draw_shadow(self, batch, camera, image_handler, light):
        self.start = self.parent.front_hip if self.front else self.parent.back_hip
        self.image_path = f'foot_{self.parent.body_type}'
        self.upper.image_path = f'upper_leg_{self.parent.body_type}'
        self.lower.image_path = f'lower_leg_{self.parent.body_type}'

        super().draw_shadow(batch, camera, image_handler, light)
