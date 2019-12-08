import numpy as np
from numpy.linalg import norm

from gameobject import PhysicsObject, Destroyable
from collider import Rectangle, Circle, Group
from weapon import Revolver
from helpers import random_unit


class Crate(Destroyable):
    def __init__(self, position):
        super().__init__(position, image_path='crate', debris_path='crate_debris', health=10)
        self.add_collider(Rectangle([0, 0], 1, 1, Group.PROPS))
        for _ in range(np.random.randint(4)):
            self.rotate_90()
        self.loot = [Revolver(self.position)]
        for loot in self.loot:
            loot.active = False

    def update(self, gravity, time_step, colliders):
        if self.destroyed:
            for loot in self.loot:
                if not loot.active:
                    colliders[loot.collider.group].append(loot.collider)
                    loot.active = True
                loot.update(gravity, time_step, colliders)

        super().update(gravity, time_step, colliders)

        if not self.destroyed:
            if self.collider.collisions:
                if norm(self.velocity) / self.bounce > 0.9:
                    self.destroy(-self.velocity)

    def draw(self, screen, camera, image_handler):
        super().draw(screen, camera, image_handler)

        if self.destroyed:
            for loot in self.loot:
                loot.draw(screen, camera, image_handler)

    def debug_draw(self, screen, camera, image_handler):
        super().debug_draw(screen, camera, image_handler)

        if self.destroyed:
            for loot in self.loot:
                loot.debug_draw(screen, camera, image_handler)

    def destroy(self, velocity):
        super().destroy(velocity)

        self.gravity_scale = 0.0
        for loot in self.loot:
            loot.set_position(self.position)
            loot.velocity[:] = 0.25 * random_unit()


class Ball(PhysicsObject):
    def __init__(self, position):
        super().__init__(position)
        self.add_collider(Circle([0, 0], 0.5, Group.PROPS))
        self.bounce = 0.8
        self.image_path = 'ball'
        self.size = 1.05
