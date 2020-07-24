import numpy as np

from collider import Circle, Group
from gameobject import PhysicsObject, Destroyable
from helpers import polar_angle, basis
from particle import BloodSplatter, Dust, Sparks


class Bullet(PhysicsObject):
    def __init__(self, position, velocity=(0, 0), parent=None, lifetime=0.5, size=1.0, dmg=20):
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
        self.decal = ''
        self.layer = 6
        self.mass = 0
        self.blunt_damage = 0
        self.dust_particle = Sparks

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        for c in self.collider.collisions:
            if c.collider.parent:
                self.parent = c.collider.parent
            else:
                self.parent = None

        self.collider.update_collisions(colliders, {Group.WALLS})
        if self.collider.collisions:
            self.destroy(Dust)
        elif np.any(self.velocity):
            self.angle = polar_angle(self.velocity)

        if self.time < self.lifetime:
            self.time += time_step
        else:
            self.destroy()

        if not self.destroyed:
            self.collider.update_collisions(colliders, {Group.PLAYERS, Group.PROPS})

            for c in self.collider.collisions:
                obj = c.collider.parent

                # Can't hit self with own bullets
                if obj is self.parent:
                    continue

                if isinstance(obj, Destroyable):
                    obj.velocity += 0.1 * self.velocity
                    particle_type = obj.damage(self.dmg, colliders)
                    self.destroy(particle_type)
                else:
                    obj.velocity += self.velocity
                    self.destroy(Dust)

                return

    def destroy(self, particle_type=None):
        if not self.destroyed:
            self.sprite.delete()
            self.sprite = None
            self.destroyed = True
            if particle_type is not None:
                self.particle_clouds.append(particle_type(self.position, -0.1 * self.velocity,
                                                          number=int(self.size * 5)))
            self.active = False
            self.sounds.add('gun')
            if particle_type is BloodSplatter:
                self.decal = 'bloodsplatter'

    def draw(self, batch, camera, image_handler):
        if self.destroyed:
            for p in self.particle_clouds:
                p.draw(batch, camera, image_handler)
        else:
            super().draw(batch, camera, image_handler)

    def draw_shadow(self, screen, camera, image_handler, light):
        pass


class Pellet(Bullet):
    def __init__(self, position, velocity=(0, 0), parent=None):
        super().__init__(position, velocity, parent, 0.5, 0.5, 15)


class Arrow(Bullet):
    def __init__(self, position, velocity=(0, 0), parent=None):
        super().__init__(position, velocity, parent, lifetime=10, size=1.2)
        self.gravity_scale = 1.0
        self.image_path = 'arrow'
        self.hit = False
        self.angle = polar_angle(self.velocity)
        self.layer = 6
        self.bounce = 1.0
        self.blunt_damage = 0
        self.dmg = 2
        self.image_position = -0.4 * basis(0)

    def update(self, gravity, time_step, colliders):
        if self.time < self.lifetime:
            self.time += time_step
        else:
            self.destroyed = True

        PhysicsObject.update(self, gravity, time_step, colliders)

        if self.hit or self.destroyed:
            return

        self.collider.update_collisions(colliders, {Group.WALLS})

        if self.collider.collisions:
            self.particle_clouds.append(Dust(self.position, -0.5 * self.velocity))
            self.hit = True
            self.sounds.add('gun')
            self.velocity[:] = np.zeros(2)
            self.active = False
            return

        if np.any(self.velocity):
            self.angle = polar_angle(self.velocity)

        self.collider.update_collisions(colliders, {Group.PLAYERS, Group.PROPS})

        for c in self.collider.collisions:
            obj = c.collider.parent

            # Can't hit self with own bullets
            if obj.parent is self.parent:
                continue

            if isinstance(obj, Destroyable):
                obj.velocity += 0.1 * self.velocity
                particle_type = obj.damage(min(self.speed * self.dmg, 60), colliders)
                self.destroy(particle_type)
                if particle_type is BloodSplatter:
                    self.decal = 'bloodsplatter'
            else:
                obj.velocity += self.velocity
                self.destroy(Dust)

            return
