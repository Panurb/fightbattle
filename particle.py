import numpy as np
from numpy.linalg import norm

from helpers import polar_angle, polar_to_cartesian, norm2, random_unit, basis, rotate


class Cloud:
    def __init__(self, image_path, position, velocity, number, lifetime, start_size, end_size=0.0, gravity_scale=1.0,
                 base_velocity=(0, 0), stretch=0.0):
        self.particles = []

        self.active = True

        if np.any(velocity):
            angle = polar_angle(velocity)
        else:
            angle = None

        v_norm = norm(velocity)
        for i in range(number):
            if angle is None:
                v = 5.0 * random_unit()
            else:
                theta = np.random.normal(angle, 1.0)
                r = np.abs(np.random.normal(v_norm, v_norm))
                v = polar_to_cartesian(r, theta)

            self.particles.append(Particle(image_path, position, base_velocity + v, lifetime=lifetime,
                                           start_size=start_size, end_size=end_size,
                                           gravity_scale=gravity_scale, stretch=stretch))

    def update(self, gravity, time_step):
        for p in self.particles:
            p.update(gravity, time_step)

            if p.time >= p.lifetime:
                p.delete()
                self.particles.remove(p)

        if not self.particles:
            self.active = False

    def draw(self, batch, camera, image_handler):
        if not self.active:
            return

        for p in self.particles:
            p.draw(batch, camera, image_handler)

    def delete(self):
        for p in self.particles:
            p.delete()
        self.particles.clear()


class Particle:
    def __init__(self, image_path, position, velocity, lifetime, start_size, end_size=0.0, gravity_scale=1.0,
                 stretch=0.0):
        self.initial_position = position.copy()
        self.position = position.copy()
        self.initial_velocity = velocity.copy()
        self.velocity = np.zeros_like(velocity)
        self.gravity_scale = gravity_scale
        self.angle = 0.0
        self.lifetime = lifetime
        self.size = start_size
        self.start_size = start_size
        self.end_size = end_size
        self.stretch = stretch
        self.time = 0.0
        self.layer = 13
        self.image_path = image_path
        self.sprite = None

    def delete(self):
        if self.sprite:
            self.sprite.delete()

    def update(self, gravity, time_step):
        self.time = min(self.time + time_step, self.lifetime)

        self.velocity = self.initial_velocity + self.gravity_scale * gravity * self.time
        self.position = self.initial_position + self.initial_velocity * self.time \
            + 0.5 * self.gravity_scale * gravity * self.time ** 2
        self.angle = polar_angle(self.velocity)
        self.size = self.start_size + self.time / self.lifetime * (self.end_size - self.start_size)

    def draw(self, batch, camera, image_handler):
        self.sprite = camera.draw_sprite(image_handler, self.image_path, self.position, angle=self.angle,
                                         batch=batch, layer=self.layer, sprite=self.sprite,
                                         scale_x=(1 + self.stretch * norm(self.velocity)) * self.size,
                                         scale_y=self.size)
        if self.end_size > 0:
            self.sprite.opacity = (1 - (self.time / self.lifetime)**4) * 255


class MuzzleFlash:
    def __init__(self, position, velocity):
        self.angle = polar_angle(velocity)
        self.start_size = 1.5
        self.initial_position = position + polar_to_cartesian(0.75 * self.start_size, self.angle)
        self.position = self.initial_position.copy()
        self.velocity = velocity.copy()
        self.time = 0.0
        self.lifetime = 0.25
        self.size = self.start_size
        self.image_path = 'muzzleflash'
        self.layer = 13
        self.sprite = None
        self.active = True

    def delete(self):
        if self.sprite:
            self.sprite.delete()

    def update(self, gravity, time_step):
        self.time += time_step
        if self.time >= self.lifetime:
            self.active = False
            self.delete()
            return

        self.position = self.initial_position + self.velocity * self.time
        self.size = (1 - (self.time / self.lifetime)**2) * self.start_size

    def draw(self, batch, camera, image_handler):
        self.sprite = camera.draw_sprite(image_handler, self.image_path, self.position, angle=self.angle,
                                         batch=batch, layer=self.layer, sprite=self.sprite,
                                         scale_x=self.start_size, scale_y=self.size)


class BloodSplatter(Cloud):
    def __init__(self, position, direction, number=10):
        super().__init__('blood', position, direction, number, 0.67, 1.5, stretch=0.5)


class Explosion(Cloud):
    def __init__(self, position):
        super().__init__('smoke', position, 1.0 * basis(1), 5, 1.0, start_size=4.0, end_size=0.0, gravity_scale=-0.5)
        self.particles.append(Particle('explosion', position, np.zeros(2), 0.5, start_size=2.0, end_size=2.5,
                                       gravity_scale=0.0))


class Dust(Cloud):
    def __init__(self, position, velocity, number=5):
        super().__init__('dust', position, velocity, number, 0.3, 2.5, gravity_scale=0.5)


class Sparks(Cloud):
    def __init__(self, position, direction, number=5):
        super().__init__('spark', position, direction, number, 0.67, 1.5, stretch=0.5)
