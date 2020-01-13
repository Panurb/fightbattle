import numpy as np

from gameobject import PhysicsObject
from collider import Rectangle, Circle, Group
from helpers import basis, polar_to_carteesian, polar_angle, rotate
from particle import MuzzleFlash


class Gun(PhysicsObject):
    def __init__(self, position):
        super().__init__(position)
        self.parent = None
        self.inertia = 0.0
        self.hit = False
        self.barrel = np.array([1.5, 1.5])
        self.bullet_speed = 1.5

        self.bullets = []

    def barrel_position(self):
        return self.position + self.direction * self.barrel[0] * self.collider.half_width \
               + self.barrel[1] * self.collider.half_height

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

    def attack(self):
        v = self.direction * self.bullet_speed * polar_to_carteesian(1, self.angle)
        self.particle_clouds.append(MuzzleFlash(self.barrel_position(), 0.05 * v, self.parent.velocity))
        self.bullets.append(Bullet(self.barrel_position(), v, self.parent))


class Revolver(Gun):
    def __init__(self, position):
        super().__init__(position)
        self.image_path = 'revolver'
        self.image_position = np.array([0.35, 0.15])
        self.add_collider(Rectangle([0.35, 0.15], 1.1, 0.6, Group.GUNS))


class Shotgun(Gun):
    def __init__(self, position):
        super().__init__(position)
        self.size = 0.9
        self.image_path = 'shotgun'
        self.image_position = np.array([0, -0.1])
        self.add_collider(Rectangle([0, -0.1], 1.8, 0.6, Group.GUNS))
        self.bullet_speed = 1.0
        self.hand_position = np.array([-0.7, -0.2])
        self.grip_position = np.array([0.45, -0.05])

    def flip_horizontally(self):
        super().flip_horizontally()
        self.hand_position[0] *= -1
        self.grip_position[0] *= -1

    def attack(self):
        v = self.direction * 0.075 * polar_to_carteesian(1, self.angle)
        self.particle_clouds.append(MuzzleFlash(self.barrel_position(), v, self.parent.velocity))
        for _ in range(8):
            theta = np.random.normal(self.angle, 0.1)
            v = self.direction * np.random.normal(self.bullet_speed, 0.05) * polar_to_carteesian(1, theta)
            self.bullets.append(Bullet(self.barrel_position(), v, self.parent, 10, 0.5))


class Bullet(PhysicsObject):
    def __init__(self, position, velocity, parent, lifetime=20, size=1.0, dmg=10):
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
        self.angle = polar_angle(self.velocity)

        if self.collider.collisions:
            self.destroyed = True

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

        if self.timer > 0:
            for c in self.collider.collisions:
                obj = c.collider.parent
                if obj not in [self.parent.body, self.parent.head]:
                    obj.damage(10, self.position, self.direction * basis(0))
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
