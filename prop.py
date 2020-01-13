import numpy as np
from numpy.linalg import norm

from gameobject import PhysicsObject, Destroyable
from collider import Rectangle, Circle, Group
from weapon import Revolver, Shotgun
from helpers import random_unit


class Crate(Destroyable):
    def __init__(self, position):
        super().__init__(position, image_path='crate', debris_path='crate_debris', health=10)
        self.add_collider(Rectangle([0, 0], 1, 1, Group.PROPS))
        for _ in range(np.random.randint(4)):
            self.rotate_90()
        self.loot = np.random.choice([Revolver, Shotgun])(self.position)
        self.loot.active = False

    def update(self, gravity, time_step, colliders):
        if self.destroyed:
            if not self.loot.active:
                colliders[self.loot.collider.group].append(self.loot.collider)
                self.loot.active = True
            self.loot.update(gravity, time_step, colliders)

        super().update(gravity, time_step, colliders)

        if not self.destroyed:
            if self.collider.collisions:
                if norm(self.velocity) / self.bounce > 0.9:
                    self.destroy(-self.velocity)

    def draw(self, screen, camera, image_handler):
        super().draw(screen, camera, image_handler)

        if self.destroyed:
            self.loot.draw(screen, camera, image_handler)

    def debug_draw(self, screen, camera, image_handler):
        super().debug_draw(screen, camera, image_handler)

        if self.destroyed:
            self.loot.debug_draw(screen, camera, image_handler)

    def destroy(self, velocity):
        super().destroy(velocity)

        self.gravity_scale = 0.0
        self.loot.set_position(self.position)
        self.loot.velocity[:] = 0.25 * random_unit()


class Ball(PhysicsObject):
    def __init__(self, position):
        super().__init__(position)
        self.add_collider(Circle([0, 0], 0.5, Group.PROPS))
        self.bounce = 0.8
        self.image_path = 'ball'
        self.size = 1.05
