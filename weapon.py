import numpy as np

from gameobject import PhysicsObject
from collider import Rectangle, Circle, Group


class Gun(PhysicsObject):
    def __init__(self, position):
        super().__init__(position)
        self.parent = None
        self.add_collider(Rectangle([0.35, 0.15], 1.1, 0.6, Group.GUNS))
        self.inertia = 0.0
        self.ammo = 0

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

        p = self.position + np.array([self.direction * 0.3, 0.35])
        v = self.direction * 1.5

        self.bullets.append(Bullet(p, (v, 0), self.parent))


class Revolver(Gun):
    def __init__(self, position):
        super().__init__(position)
        self.ammo = 6
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

        self.lifetime = 100
        self.time = 0
        self.destroyed = False
        self.collision = False

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if self.time < self.lifetime:
            self.time += time_step
        else:
            self.destroyed = True

        for c in self.collider.collisions:
            try:
                if self.parent is not c.collider.parent:
                    c.collider.parent.damage(10, self.position, self.velocity)
            except AttributeError:
                print(c.collider.parent)

            self.destroyed = True
            return


class Sword(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, image_path='sword', size=1.0)
        self.add_collider(Rectangle([0.0, 1.0], 0.25, 2.0, Group.SWORDS))
        self.image_position = np.array([0.0, 1.0])
        self.rotate_90()


class Shield(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, image_path='shield', size=0.85)
        self.add_collider(Rectangle([0.0, 0.0], 0.25, 2.0, Group.SHIELDS))
        self.rotate_90()
