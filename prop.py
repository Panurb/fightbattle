import numpy as np
from numpy.linalg import norm

from gameobject import PhysicsObject, Destroyable
from collider import Rectangle, Circle, Group
from weapon import Revolver, Shotgun, Shield, Sword, Grenade, Bow
from helpers import random_unit


class Crate(Destroyable):
    def __init__(self, position):
        super().__init__(position, image_path='crate', debris_path='crate_debris', health=10)
        self.add_collider(Rectangle([0, 0], 1, 1, Group.PROPS))
        self.loot_list = [Bow, Shotgun, Revolver]
        self.loot = None

    def update(self, gravity, time_step, colliders):
        if self.destroyed and self.loot is not None:
            if isinstance(self.loot, Destroyable) and self.loot.destroyed:
                self.loot = None
                return
            elif not self.loot.active:
                colliders[self.loot.collider.group].append(self.loot.collider)
                self.loot.active = True

            self.loot.update(gravity, time_step, colliders)

        super().update(gravity, time_step, colliders)

        if not self.destroyed:
            if self.collider.collisions:
                if norm(self.velocity) / self.bounce > 0.9:
                    self.destroy(-self.velocity, colliders)

            if not self.parent and self.collider.collisions and self.speed > 0.1:
                self.sounds.append('crate')

    def draw(self, screen, camera, image_handler):
        super().draw(screen, camera, image_handler)

        if self.destroyed and self.loot:
            self.loot.draw(screen, camera, image_handler)

    def debug_draw(self, screen, camera, image_handler):
        super().debug_draw(screen, camera, image_handler)

        if self.destroyed and self.loot:
            self.loot.debug_draw(screen, camera, image_handler)

    def destroy(self, velocity, colliders):
        if not self.destroyed:
            self.sounds.append('crate_break')
            self.gravity_scale = 0.0
            if self.loot_list:
                self.loot = np.random.choice(self.loot_list)(self.position)
                self.loot.velocity[:] = 0.25 * random_unit()
                self.loot.active = False

        super().destroy(velocity, colliders)

    def play_sounds(self, sound_handler):
        super().play_sounds(sound_handler)
        if self.loot is not None:
            self.loot.play_sounds(sound_handler)


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
