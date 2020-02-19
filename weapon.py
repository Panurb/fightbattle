import pygame

import numpy as np
from numpy.linalg import norm

from gameobject import PhysicsObject, Destroyable, GameObject
from collider import Rectangle, Circle, Group
from helpers import basis, polar_to_cartesian, polar_angle, rotate
from particle import MuzzleFlash, Explosion


class Weapon(PhysicsObject):
    def __init__(self, position):
        super().__init__(position)
        self.parent = None
        self.hit = False

    def attack(self):
        pass


class Gun(Weapon):
    def __init__(self, position):
        super().__init__(position)
        self.barrel_position = np.array([1.0, 0.3])
        self.hand_position = np.zeros(2)
        self.grip_position = None
        self.bullet_speed = 3.0

        self.bullets = []

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

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        for b in self.bullets:
            b.update(gravity, time_step, colliders)
            if b.destroyed and not b.particle_clouds:
                self.bullets.remove(b)

    def draw(self, screen, camera, image_handler):
        super().draw(screen, camera, image_handler)

        for b in self.bullets:
            b.draw(screen, camera, image_handler)

    def debug_draw(self, screen, camera, image_handler):
        super().debug_draw(screen, camera, image_handler)

        pygame.draw.circle(screen, image_handler.debug_color, camera.world_to_screen(self.get_hand_position()), 2)

        for b in self.bullets:
            b.debug_draw(screen, camera, image_handler)

    def attack(self):
        v = 0.1 * self.direction * polar_to_cartesian(1, self.angle)
        self.particle_clouds.append(MuzzleFlash(self.get_barrel_position(), v, self.parent.velocity))
        self.particle_clouds.append(
            MuzzleFlash(self.get_barrel_position(), rotate(0.5 * v, 0.5 * np.pi), self.parent.velocity))
        self.particle_clouds.append(
            MuzzleFlash(self.get_barrel_position(), rotate(0.5 * v, -0.5 * np.pi), self.parent.velocity))


class Revolver(Gun):
    def __init__(self, position):
        super().__init__(position)
        self.image_path = 'revolver'
        self.image_position = np.array([0.35, 0.15])
        self.add_collider(Rectangle([0.35, 0.15], 1.1, 0.6, Group.GUNS))

    def attack(self):
        super().attack()
        v = self.direction * self.bullet_speed * polar_to_cartesian(1, self.angle)
        self.bullets.append(Bullet(self.get_barrel_position(), v, self.parent))


class Shotgun(Gun):
    def __init__(self, position):
        super().__init__(position)
        self.size = 0.9
        self.image_path = 'shotgun'
        self.image_position = np.array([0, -0.1])
        self.add_collider(Rectangle([0, -0.1], 1.8, 0.6, Group.GUNS))
        self.bullet_speed = 2.0
        self.hand_position = np.array([-0.7, -0.2])
        self.grip_position = np.array([0.45, -0.05])

    def attack(self):
        super().attack()
        for _ in range(5):
            theta = np.random.normal(self.angle, 0.1)
            v = self.direction * np.random.normal(self.bullet_speed, 0.05) * polar_to_cartesian(1, theta)
            self.bullets.append(Bullet(self.get_barrel_position(), v, self.parent, 10, 0.5, dmg=8))


class Bullet(PhysicsObject):
    def __init__(self, position, velocity, parent, lifetime=20, size=1.0, dmg=20):
        super().__init__(position, velocity)
        self.parent = parent
        self.add_collider(Circle(np.zeros(2), 0.2, Group.BULLETS))
        self.gravity_scale = 0
        self.image_path = 'bullet'
        self.size = size
        self.bounce = 1.0

        self.lifetime = lifetime
        self.time = 0
        self.destroyed = False
        self.collision = False
        self.dmg = dmg

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if self.collider.collisions:
            self.destroyed = True
        elif np.any(self.velocity):
            self.angle = polar_angle(self.velocity)

        if self.time < self.lifetime:
            self.time += time_step
        else:
            self.destroyed = True

        self.collider.update_collisions(colliders, [Group.HITBOXES, Group.PROPS])

        for c in self.collider.collisions:
            obj = c.collider.parent
            if obj not in [self.parent.body, self.parent.head]:
                try:
                    obj.damage(self.dmg, self.position, self.velocity)
                except AttributeError:
                    print('Cannot damage', obj)
                self.destroyed = True

            return


class Sword(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, image_path='sword', size=1.0)
        self.add_collider(Rectangle([0.0, 0.8], 0.25, 2.25, Group.SWORDS))
        self.image_position = np.array([0.0, 0.8])
        self.rotate(np.pi / 2)
        self.hit = False
        self.timer = 0.0
        self.parent = None

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if self.collider.collisions:
            self.hit = True
            self.timer = 0.0
            return

        self.collider.update_collisions(colliders, [Group.HITBOXES, Group.PROPS, Group.SHIELDS])

        if self.parent:
            if self.timer > 0:
                for c in self.collider.collisions:
                    obj = c.collider.parent
                    if obj not in [self.parent.body, self.parent.head]:
                        obj.damage(50, self.position, self.direction * basis(0))
                        self.hit = True
                        self.timer = 0.0
                        break
                else:
                    self.timer = max(0.0, self.timer - time_step)

    def attack(self):
        self.hit = False
        self.timer = 5.0


class Shield(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, image_path='shield', size=0.85)
        self.add_collider(Rectangle([0.0, 0.0], 0.25, 2.0, Group.SHIELDS))
        self.rotate_90()


class Grenade(Destroyable):
    def __init__(self, position):
        super().__init__(position, size=1.1, image_path='grenade', health=1)
        self.add_collider(Circle([0, 0], 0.25, Group.PROPS))
        self.explosion_collider = Circle([0, 0], 5.0)
        self.timer = 50.0
        self.primed = False
        self.pin = PhysicsObject(self.position, image_path='grenade_pin')
        self.pin.add_collider(Circle([0, 0], 0.25, Group.DEBRIS))

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if self.primed:
            self.pin.update(gravity, time_step, colliders)
            self.timer -= time_step

            if self.timer <= 0.0:
                if not self.destroyed:
                    self.explosion_collider.position = self.position
                    self.explosion_collider.update_collisions(colliders, [Group.PLAYERS, Group.PROPS])
                    for c in self.explosion_collider.collisions:
                        obj = c.collider.parent
                        r = -self.position + obj.position
                        r_norm = norm(r)
                        obj.damage(int(abs(30 * (5 - r_norm))), obj.position, 0.1 * r / (r_norm + 0.1))

                self.destroy()
        else:
            self.pin.set_position(self.position + 0.15 * rotate(basis(0), self.angle))
            self.pin.rotate(self.angle - self.pin.angle)

    def destroy(self, velocity=(0, 0)):
        if not self.destroyed:
            self.particle_clouds.append(Explosion(self.position))

        super().destroy(velocity)

    def attack(self):
        if not self.primed:
            self.pin.velocity[0] = self.velocity[0] - self.direction * 0.25
            self.pin.velocity[1] = 0.5
            self.primed = True

    def draw(self, screen, camera, image_handler):
        super().draw(screen, camera, image_handler)
        self.pin.draw(screen, camera, image_handler)


class Arrow(Bullet):
    def __init__(self, position, velocity, parent):
        super().__init__(position, velocity, parent, lifetime=80, size=1.2)
        self.gravity_scale = 1.0
        self.image_path = 'arrow'
        self.bounce = 0.0
        self.hit = False
        self.angle = polar_angle(self.velocity)

    def update(self, gravity, time_step, colliders):
        if self.time < self.lifetime:
            self.time += time_step
        else:
            self.destroyed = True

        if self.hit:
            return

        PhysicsObject.update(self, gravity, time_step, colliders)

        if self.collider.collisions:
            self.hit = True
            return

        if np.any(self.velocity):
            self.angle = polar_angle(self.velocity)

        self.collider.update_collisions(colliders, [Group.HITBOXES, Group.PROPS])

        for c in self.collider.collisions:
            obj = c.collider.parent
            if obj not in [self.parent.body, self.parent.head]:
                try:
                    obj.damage(int(self.speed * self.dmg), self.position, self.velocity)
                except AttributeError:
                    print('Cannot damage', obj)
                self.destroyed = True

            return


class Bow(Gun):
    def __init__(self, position):
        super().__init__(position)
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
        self.arrow = GameObject(self.position, 'arrow', size=1.2)
        self.arrow.image_position = 0.5 * basis(0)

    def flip_horizontally(self):
        super().flip_horizontally()
        self.arrow.flip_horizontally()

    def update(self, gravity, time_step, colliders):
        Weapon.update(self, gravity, time_step, colliders)

        for b in self.bullets:
            if b.destroyed:
                self.bullets.remove(b)
            else:
                b.update(gravity, time_step, colliders)

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
            v = self.direction * self.parent.attack_charge * self.bullet_speed * polar_to_cartesian(1, self.angle)
            self.bullets.append(Arrow(self.get_barrel_position(), v, self.parent))
            self.timer = 10.0

    def draw(self, screen, camera, image_handler):
        super().draw(screen, camera, image_handler)

        a = camera.world_to_screen(self.position + self.direction * rotate(self.string_upper, self.angle))
        c = camera.world_to_screen(self.position + self.direction * rotate(self.string_lower, self.angle))
        if self.parent and self.parent.attack_charge:
            b = camera.world_to_screen(self.get_hand_position())
            pygame.draw.line(screen, self.string_color, a, b, 2)
            pygame.draw.line(screen, self.string_color, b, c, 2)
        else:
            pygame.draw.line(screen, self.string_color, a, c, 2)
