import numpy as np

from gameobject import PhysicsObject, Group
from collider import Rectangle, Circle


class Gun(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, group=Group.GUNS)
        self.add_collider(Rectangle(np.zeros(2), 1, 0.5))
        self.inertia = 0.0

        self.bullets = []

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        for b in self.bullets:
            b.update(gravity, time_step, colliders)
            if b.destroyed:
                self.bullets.remove(b)

    def draw(self, screen, camera):
        super().draw(screen, camera)

        for b in self.bullets:
            b.draw(screen, camera)

    def attack(self):
        if self.flipped:
            p = self.position + [-0.5, 0.25]
            v = -3
        else:
            p = self.position + [0.5, 0.25]
            v = 3

        self.bullets.append(Bullet(p, (v, 0)))


class Bullet(PhysicsObject):
    def __init__(self, position, velocity):
        super().__init__(position, velocity, group=Group.BULLETS)
        self.add_collider(Circle(np.zeros(2), 0.2))
        self.gravity_scale = 0

        self.lifetime = 15
        self.time = 0
        self.destroyed = False

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if self.time < self.lifetime:
            self.time += time_step
        else:
            self.destroyed = True

        for c in self.collider.collisions:
            try:
                c.collider.parent.damage(100)
            except AttributeError:
                pass

            self.destroyed = True
            return
