import numpy as np

from gameobject import PhysicsObject, Destroyable
from collider import Rectangle, Circle, Group
from weapon import Revolver, Shotgun, Shield, Axe, Grenade, Bow


class Crate(Destroyable):
    def __init__(self, position):
        super().__init__(position, image_path='crate', debris_path='crate_debris', health=100)
        self.add_collider(Rectangle([0, 0], 1, 1, Group.PROPS))
        self.loot_list = [Revolver, Shotgun, Shield, Axe, Grenade, Bow]

    def apply_data(self, data):
        super().apply_data(data)
        self.rotate(0.5 * np.pi * np.random.randint(0, 4))

    def destroy(self, colliders):
        if not self.destroyed:
            self.sounds.add('crate_break')
            self.gravity_scale = 0.0

        super().destroy(colliders)


class Ball(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, image_path='ball', bump_sound='ball')
        radius = 0.5
        self.add_collider(Circle([0, 0], radius, Group.PROPS))
        self.bounce = 0.8
        self.size = 2.1 * radius
        self.scored = ''
        self.roll = True
        self.blunt_damage = 0

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if not self.scored:
            self.collider.update_collisions(colliders, [Group.GOALS])
            for c in self.collider.collisions:
                c.collider.parent.score += 1
                c.collider.parent.collider.colliders[-1].group = Group.NONE
                self.scored = c.collider.parent.team
                self.sounds.add('alarm')
                break
