import numpy as np

from collider import Circle, Group
from gameobject import PhysicsObject, Destroyable
from helpers import polar_angle
from particle import Sparks, BloodSplatter


class Bullet(PhysicsObject):
    def __init__(self, position, velocity=(0, 0), parent=None, lifetime=20, size=1.0, dmg=20):
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
        self.dmg = dmg

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if self.collider.collisions:
            self.destroy(Sparks)
        elif np.any(self.velocity):
            self.angle = polar_angle(self.velocity)

        if self.time < self.lifetime:
            self.time += time_step
        else:
            self.destroy()

        if not self.destroyed:
            self.collider.update_collisions(colliders, [Group.HITBOXES, Group.PROPS])

            for c in self.collider.collisions:
                obj = c.collider.parent
                #if obj not in [self.parent.body, self.parent.head]:
                if isinstance(obj, Destroyable):
                    self.particle_clouds += obj.damage(self.dmg, self.position, self.velocity, colliders)
                    self.destroy()
                else:
                    obj.velocity += self.velocity
                    self.destroy(Sparks)

                return

    def destroy(self, particle_type=None):
        if not self.destroyed:
            self.destroyed = True
            if particle_type is not None:
                self.particle_clouds.append(particle_type(self.position, 0.05 * self.velocity))
            self.active = False
            self.sounds.append('gun')

    def draw(self, screen, camera, image_handler):
        if self.destroyed:
            for p in self.particle_clouds:
                p.draw(screen, camera, image_handler)
        else:
            super().draw(screen, camera, image_handler)


class Pellet(Bullet):
    def __init__(self, position, velocity=(0, 0), parent=None):
        super().__init__(position, velocity, parent, 10, 0.5, 15)


class Arrow(Bullet):
    def __init__(self, position, velocity=(0, 0), parent=None):
        super().__init__(position, velocity, parent, lifetime=40, size=1.2)
        self.gravity_scale = 1.0
        self.image_path = 'arrow'
        self.bounce = 0.0
        self.hit = False
        self.angle = polar_angle(self.velocity)

    def update(self, gravity, time_step, colliders):
        if self.time < self.lifetime:
            self.time += time_step
        else:
            self.destroyed = True

        PhysicsObject.update(self, gravity, time_step, colliders)

        if self.hit:
            return

        if self.collider.collisions:
            self.hit = True
            self.sounds.append('gun')
            self.velocity[:] = np.zeros(2)
            self.active = False
            return

        if np.any(self.velocity):
            self.angle = polar_angle(self.velocity)

        self.collider.update_collisions(colliders, [Group.HITBOXES, Group.PROPS])

        for c in self.collider.collisions:
            obj = c.collider.parent
            if obj not in [self.parent.body, self.parent.head]:
                try:
                    obj.damage(int(self.speed * self.dmg), self.position, self.velocity, colliders)
                except AttributeError:
                    print('Cannot damage', obj)
                self.destroy(True)

            return

    def destroy(self, sparks):
        self.destroyed = True
