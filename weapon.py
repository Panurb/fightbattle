import pygame

import numpy as np
from numpy.linalg import norm

from bullet import Pellet, Bullet, Arrow
from gameobject import PhysicsObject, Destroyable, GameObject
from collider import Rectangle, Circle, Group
from helpers import basis, polar_to_cartesian, polar_angle, rotate, random_unit, norm2
from particle import MuzzleFlash, Explosion, Sparks, BloodSplatter


class Weapon(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, bump_sound='gun')
        self.hand_position = np.zeros(2)
        self.attacked = False
        self.hit = False
        self.attack_delay = 5.0
        self.timer = 0.0

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)
        self.timer = max(0.0, self.timer - time_step)

    def attack(self):
        self.attacked = False
        self.timer = self.attack_delay


class Gun(Weapon):
    def __init__(self, position):
        super().__init__(position)
        self.barrel_position = np.array([1.0, 0.3])
        self.grip_position = None
        self.bullet_speed = 3.0

    def get_data(self):
        return super().get_data() + (self.attacked, )

    def apply_data(self, data):
        super().apply_data(data)
        self.attacked = data[9]

    def get_hand_position(self):
        v = self.hand_position.copy()
        v[0] *= self.direction
        return self.position + rotate(v, self.angle)

    def get_grip_position(self):
        v = self.grip_position.copy()
        v[0] *= self.direction
        return self.position + rotate(v, self.angle)

    def get_barrel_position(self):
        v = self.barrel_position.copy()
        v[0] *= self.direction
        return self.position + rotate(v, self.angle)

    def debug_draw(self, screen, camera, image_handler):
        super().debug_draw(screen, camera, image_handler)

        pygame.draw.circle(screen, image_handler.debug_color, camera.world_to_screen(self.get_hand_position()), 2)

    def attack(self):
        super().attack()
        v = 0.1 * self.direction * polar_to_cartesian(1, self.angle)
        self.particle_clouds.append(MuzzleFlash(self.get_barrel_position(), v, self.parent.velocity))
        self.particle_clouds.append(
            MuzzleFlash(self.get_barrel_position(), rotate(0.5 * v, 0.5 * np.pi), self.parent.velocity))
        self.particle_clouds.append(
            MuzzleFlash(self.get_barrel_position(), rotate(0.5 * v, -0.5 * np.pi), self.parent.velocity))

        return []

    def play_sounds(self, sound_handler):
        super().play_sounds(sound_handler)


class Revolver(Gun):
    def __init__(self, position):
        super().__init__(position)
        self.image_path = 'revolver'
        self.image_position = np.array([0.35, 0.15])
        self.add_collider(Rectangle([0.35, 0.29], 1.1, 0.3, Group.GUNS))

    def attack(self):
        bs = super().attack()
        self.sounds.add('revolver')
        v = self.direction * self.bullet_speed * polar_to_cartesian(1, self.angle)
        bs.append(Bullet(self.get_barrel_position(), v, self.parent))
        return bs


class Shotgun(Gun):
    def __init__(self, position):
        super().__init__(position)
        self.size = 0.9
        self.image_path = 'shotgun'
        self.image_position = np.array([0, -0.1])
        self.add_collider(Rectangle([0, 0.08], 1.8, 0.3, Group.GUNS))
        self.bullet_speed = 2.0
        self.hand_position = np.array([-0.7, -0.2])
        self.grip_position = np.array([0.45, -0.05])

    def attack(self):
        bs = super().attack()
        self.sounds.add('shotgun')
        theta = self.angle - 0.1
        for _ in range(3):
            theta += 0.1
            v = self.direction * np.random.normal(self.bullet_speed, 0.05) * polar_to_cartesian(1, theta)
            bs.append(Pellet(self.get_barrel_position(), v, self.parent))

        return bs


class Sword(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, image_path='sword', size=1.0, bump_sound='gun')
        self.add_collider(Rectangle([0.0, 0.8], 0.25, 2.25, Group.SWORDS))
        self.image_position = np.array([0.0, 0.8])
        self.rotate(np.pi / 2)
        self.hit = False
        self.timer = 0.0
        self.parent = None
        self.rest_angle = 0.5 * np.pi

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if self.collider.collisions:
            if self.parent is not None and self.timer > 0:
                self.sounds.add('sword')
                self.parent.camera_shake = 10 * random_unit()
                self.particle_clouds.append(Sparks(self.position + self.collider.half_height, np.zeros(2)))
            self.hit = True
            self.timer = 0.0
            return

        self.collider.update_collisions(colliders, [Group.HITBOXES, Group.PROPS, Group.SHIELDS])

        if self.parent is not None:
            if self.timer > 0:
                for c in self.collider.collisions:
                    obj = c.collider.parent
                    if obj not in [self.parent.body, self.parent.head]:
                        obj.damage(50, self.position, self.direction * basis(0), colliders)
                        self.hit = True
                        self.timer = 0.0
                        self.parent.camera_shake = 10 * random_unit()
                        break
                else:
                    self.timer = max(0.0, self.timer - time_step)

    def attack(self):
        self.hit = False
        self.timer = 5.0
        self.sounds.add('sword_swing')


class Shield(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, image_path='shield', size=0.85, bump_sound='gun')
        self.add_collider(Rectangle([0.0, 0.0], 0.25, 2.0, Group.SHIELDS))
        self.rest_angle = 0.5 * np.pi


class Grenade(Destroyable):
    def __init__(self, position):
        super().__init__(position, bump_sound='gun', health=1)
        self.image_path = 'grenade'
        self.size = 1.1
        self.add_collider(Circle([0, 0], 0.25, Group.PROPS))
        self.timer = 0.0
        self.primed = False
        self.pin = PhysicsObject(self.position, image_path='grenade_pin')
        self.pin.rest_angle = None
        self.pin.add_collider(Circle([0, 0], 0.25, Group.DEBRIS))
        self.rest_angle = None
        self.destroyed = False
        self.attacked = False
        self.camera_shake = np.zeros(2)

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if norm(self.camera_shake) < time_step:
            self.camera_shake = np.zeros(2)
        else:
            self.camera_shake *= -0.5

        if self.primed:
            if self.pin:
                self.pin.update(gravity, time_step, colliders)
            self.timer -= time_step

            if self.timer <= 0.0:
                self.destroy(colliders)
        else:
            self.pin.set_position(self.position + 0.15 * rotate(basis(0), self.angle))
            self.pin.rotate(self.angle - self.pin.angle)

    def destroy(self, colliders):
        if not self.destroyed:
            self.sprite.delete()
            self.sprite = None
            self.destroyed = True
            
            self.pin.sprite.delete()
            self.pin = None

            explosion_collider = Circle(self.position, 3.0)
            explosion_collider.update_occupied_squares(colliders)
            explosion_collider.update_collisions(colliders, {Group.HITBOXES, Group.PROPS})

            for c in explosion_collider.collisions:
                obj = c.collider.parent
                if obj is self:
                    continue

                r = obj.position - self.position
                r_norm = norm(r)

                if obj.parent:
                    obj.parent.velocity += 0.5 * r / r_norm
                else:
                    obj.velocity += 0.5 * r / r_norm

                if isinstance(obj, Destroyable):
                    obj.damage(int(abs(30 * (5 - r_norm))), colliders)

            self.particle_clouds.append(Explosion(self.position))
            self.sounds.add('grenade')

            self.collider.clear_occupied_squares(colliders)
            self.collider = None

            self.camera_shake = 100 * random_unit()

    def attack(self):
        if not self.primed:
            self.pin.velocity[0] = self.velocity[0] - self.direction * 0.25
            self.pin.velocity[1] = 0.5
            self.primed = True
            self.timer = 50.0
            self.sounds.add('sword')

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        if self.pin:
            self.pin.draw(batch, camera, image_handler)


class Bow(Gun):
    def __init__(self, position):
        super().__init__(position)
        self.bump_sound = 'bump'
        self.image_path = 'bow'
        self.add_collider(Rectangle([0, 0], 0.5, 1.9, Group.GUNS))
        self.bullet_speed = 2.0
        self.rotate(np.pi / 2)
        self.hand_position = -0.2 * basis(0)
        self.barrel_position = 0.5 * basis(0)
        self.grip_position = 0.2 * basis(0)
        self.string_upper = np.array([-0.22, 1.0])
        self.string_lower = np.array([-0.22, -1.0])
        self.timer = 0.0
        self.string_color = [50, 50, 50]
        self.arrow = GameObject(self.position, 'arrow', size=1.2, layer=2)
        self.arrow.image_position = 0.5 * basis(0)
        self.attack_charge = 0.0
        self.rest_angle = -0.5 * np.pi
        self.strings = [None, None]
        self.layer = 3

    def get_data(self):
        return super().get_data() + (self.attack_charge, )

    def apply_data(self, data):
        super().apply_data(data)
        self.attack_charge = data[-1]

    def flip_horizontally(self):
        super().flip_horizontally()
        self.arrow.flip_horizontally()

    def update(self, gravity, time_step, colliders):
        Weapon.update(self, gravity, time_step, colliders)

        if self.parent:
            if self.timer == 0.0 and self.parent.attack_charge > 0.0:
                self.hand_position[0] = -(0.2 + 0.6 * self.parent.attack_charge)
                self.arrow.set_position(self.get_hand_position())
                self.arrow.angle = self.parent.hand.angle
            else:
                self.hand_position[0] = -0.8
                self.timer = max(0.0, self.timer - time_step)
        else:
            self.hand_position[0] = -0.2
            self.timer = 0.0

    def attack(self):
        if self.timer == 0.0:
            self.attacked = False
            self.sounds.add('bow_release')
            v = self.direction * self.attack_charge * self.bullet_speed * polar_to_cartesian(1, self.angle)
            self.timer = 10.0
            self.attack_charge = 0.0

            return [Arrow(self.get_barrel_position(), v, self.parent)]

        return []

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        
        if self.arrow.sprite:
            if self.attack_charge:
                self.arrow.sprite.visible = True
            else:
                self.arrow.sprite.visible = False


        a = self.position + self.direction * rotate(self.string_upper, self.angle)
        c = self.position + self.direction * rotate(self.string_lower, self.angle)
        if self.attack_charge:
            b = self.get_hand_position()
            self.strings[0] = camera.draw_line(a, b, batch=batch, layer=self.layer, vertex_list=self.strings[0])
            self.strings[1] = camera.draw_line(b, c, batch=batch, layer=self.layer, vertex_list=self.strings[1])
        else:
            self.strings[0] = camera.draw_line(a, c, batch=batch, layer=self.layer, vertex_list=self.strings[0])
            if self.strings[1]:
                self.strings[1].delete()
                self.strings[1] = None
