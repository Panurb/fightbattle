import numpy as np

from gameobject import PhysicsObject, Destroyable
from collider import Rectangle, Circle, Group


class Crate(Destroyable):
    def __init__(self, position):
        super().__init__(position, image_path='crate', health=10)
        self.add_collider(Rectangle([0, 0], 1, 1, Group.PROPS))
        for _ in range(np.random.randint(4)):
            self.rotate_90()


class Ball(PhysicsObject):
    def __init__(self, position):
        super().__init__(position)
        self.add_collider(Circle([0, 0], 0.5, Group.PROPS))
        self.bounce = 0.8
        self.image_path = 'ball'
        self.size = 1.05

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        self.angular_velocity = - self.gravity_scale * self.velocity[0]
