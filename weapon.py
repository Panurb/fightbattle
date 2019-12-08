import numpy as np

from gameobject import PhysicsObject
from collider import Rectangle, Circle, Group
from helpers import basis, rotate
from particle import Cloud


class Gun(PhysicsObject):
    def __init__(self, position):
        super().__init__(position)
        self.parent = None
        self.add_collider(Rectangle([0.35, 0.15], 1.1, 0.6, Group.GUNS))
        self.inertia = 0.0
        self.ammo = 0
        self.hit = False

        self.bullets = []

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        for b in self.bullets:
            b.update(gravity, time_step, colliders)
            if b.destroyed:
                self.bullets.remove(b)

    def draw(self, screen, camera, image_handler):
        super().draw(screen, camera, image_handler)

        for b in self.bullets:
            b.draw(screen, camera, image_handler)

    def attack(self):
        if self.ammo == 0:
            return

        self.ammo -= 1

        p = self.position + self.direction * 1.5 * self.collider.half_width + 1.5 * self.collider.half_height
        v = self.direction * 1.5 * np.array([np.cos(self.angle), np.sin(self.angle)])

        self.bullets.append(Bullet(p, v, self.parent))
        s = (255, 255, 200)
        e = (255, 215, 0)
        self.particle_clouds.append(Cloud(p, 0.05 * v, 10, 10, 0.2, gravity_scale=0.0, start_color=s, end_color=e))
        self.particle_clouds.append(Cloud(p, 0.025 * rotate(v, 0.5 * np.pi), 10, 10, 0.2, gravity_scale=0.0,
                                          start_color=s, end_color=e))
        self.particle_clouds.append(Cloud(p, 0.025 * rotate(v, -0.5 * np.pi), 10, 10, 0.2, gravity_scale=0.0,
                                          start_color=s, end_color=e))


class Revolver(Gun):
    def __init__(self, position):
        super().__init__(position)
        self.ammo = 100
        self.image_path = 'revolver'
        self.image_position = np.array([0.35, 0.15])


class Bullet(PhysicsObject):
    def __init__(self, position, velocity, parent):
        super().__init__(position, velocity)
        self.parent = parent
        self.add_collider(Circle(np.zeros(2), 0.2, Group.BULLETS))
        self.gravity_scale = 0
        self.image_path = 'bullet'
        self.size = 0.8
        self.bounce = 1.0

        self.lifetime = 20
        self.time = 0
        self.destroyed = False
        self.collision = False

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

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
                    obj.damage(10, self.position, self.velocity)
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
