import numpy as np

from gameobject import PhysicsObject, Destroyable
from collider import Rectangle, Circle, Group
from weapon import Revolver, Shotgun, Shield, Sword, Grenade, Bow
from helpers import random_unit


class Crate(Destroyable):
    def __init__(self, position):
        super().__init__(position, image_path='crate', debris_path='crate_debris', health=10)
        self.add_collider(Rectangle([0, 0], 1, 1, Group.PROPS))
        self.loot_list = [Bow, Shotgun, Revolver]

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if not self.destroyed:
            if self.collider.collisions:
                if self.speed / self.bounce > 0.9:
                    self.damage(self.health, self.position, -self.velocity, colliders)

    def destroy(self, velocity, colliders):
        if not self.destroyed:
            self.sounds.append('crate_break')
            self.gravity_scale = 0.0

        super().destroy(velocity, colliders)


class Ball(PhysicsObject):
    def __init__(self, position):
        super().__init__(position)
        radius = 0.5
        self.add_collider(Circle([0, 0], radius, Group.PROPS))
        self.bounce = 0.8
        self.image_path = 'ball'
        self.size = 2.1 * radius

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if not self.parent and self.collider.collisions and self.speed > 0.1:
            self.sounds.append('ball')
