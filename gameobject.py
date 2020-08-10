import numpy as np
from numpy.linalg import norm

from collider import Circle, Group, Rectangle
from drawable import Drawable
from helpers import norm2, rotate, normalized, basis, random_unit
from particle import Dust

MAX_SPEED = 75.0


class GameObject(Drawable):
    def __init__(self, position, image_path='', size=1.05, layer=4, angle=0.0):
        super().__init__(position, image_path, size, angle, layer)

        self.collider = None
        self.collision_enabled = True

        self.parent = None
        self.sounds = set()
        self.id = None

    def delete(self):
        super().delete()
        if self.collider and self.collider.vertex_list:
            self.collider.vertex_list.delete()

    def get_data(self):
        data = (self.id, type(self), self.position[0], self.position[1], self.direction, self.angle)

        return data

    def apply_data(self, data):
        self.id = data[0]
        self.set_position(np.array([data[2], data[3]]))
        if data[4] != self.direction:
            self.flip_horizontally()
        self.rotate(data[5] - self.angle)

    def flip_horizontally(self):
        super().flip_horizontally()

        if type(self.collider) is Rectangle:
            w = 2 * self.collider.half_width / self.collider.width
            r = self.collider.position - self.position
            self.collider.position -= 2 * np.dot(r, w) * w

    def set_position(self, position):
        delta_pos = position - self.position

        self.position += delta_pos
        if self.collider:
            self.collider.set_position(self.collider.position + delta_pos)

    def add_collider(self, collider):
        self.collider = collider
        collider.parent = self
        collider.position += self.position

    def debug_draw(self, batch, camera, image_handler):
        if self.collider:
            self.collider.draw(batch, camera, image_handler)

    def play_sounds(self, sound_handler):
        for sound in list(self.sounds):
            player = sound_handler.sounds[sound].play()
            player.volume = sound_handler.volume

        self.sounds.clear()


class PhysicsObject(GameObject):
    def __init__(self, position, velocity=(0, 0), image_path='', size=1.05, gravity_scale=1.0, bump_sound='bump',
                 dust=True):
        super().__init__(position, image_path, size)
        self.velocity = np.array(velocity, dtype=float)
        self.speed = norm(self.velocity)
        self.acceleration = np.zeros(2)

        self.angular_velocity = 0.0
        self.angular_acceleration = 0.0

        self.bounce = 0.5
        self.on_ground = False
        self.mass = 1.0
        self.inertia = 0.0
        self.gravity_scale = gravity_scale

        self.particle_clouds = []

        self.active = True

        self.bump_sound = bump_sound

        self.parent = None
        self.group = None

        self.dust = dust
        self.dust_particle = Dust
        self.blunt_damage = 0.5
        self.roll = False
        self.grabbed = False

        self.camera_shake = None

    def delete(self):
        super().delete()
        for p in self.particle_clouds:
            p.delete()

    def add_collider(self, collider):
        super().add_collider(collider)
        self.group = collider.group

    def get_data(self):
        return super().get_data() + (self.velocity[0], self.velocity[1], self.sounds, self.group, self.grabbed)

    def apply_data(self, data):
        super().apply_data(data)
        self.velocity[0] = data[6]
        self.velocity[1] = data[7]
        self.sounds.clear()
        for s in data[8]:
            self.sounds.add(s)
        if len(data) > 10:
            self.group = data[9]
            self.grabbed = data[10]

    def rotate(self, delta_angle):
        super().rotate(delta_angle)
        if self.collider:
            self.collider.rotate(delta_angle)
            r = self.collider.position - self.position
            self.collider.position = self.position + rotate(r, delta_angle)

    def rotate_90(self):
        self.angle += np.pi / 2
        self.collider.rotate_90()

    def get_acceleration(self, gravity):
        return self.gravity_scale * gravity

    def update(self, gravity, time_step, colliders):
        for p in self.particle_clouds:
            p.update(gravity, time_step)
            if not p.active:
                self.particle_clouds.remove(p)

        if not self.active:
            return

        if self.velocity[1] != 0:
            self.on_ground = False

        self.speed = norm(self.velocity)
        if self.speed != 0:
            self.velocity *= min(self.speed, MAX_SPEED) / self.speed

        delta_pos = self.velocity * time_step + 0.5 * self.acceleration * time_step**2
        self.set_position(self.position + delta_pos)

        if not self.grabbed and self.roll:
            self.angular_velocity = -self.gravity_scale * self.velocity[0]

        if self.collider:
            height = self.collider.axis_half_width(basis(1))

        delta_angle = self.angular_velocity * time_step + 0.5 * self.angular_acceleration * time_step**2
        if delta_angle:
            self.rotate(delta_angle)
        ang_acc_old = float(self.angular_acceleration)
        self.angular_acceleration = 0.0

        if self.collider is None or not self.collision_enabled:
            return

        if any(np.abs(delta_pos) > 0.01) or abs(delta_angle) > 1e-3:
            self.collider.update_occupied_squares(colliders)

        self.collider.update_collisions(colliders)

        for collision in self.collider.collisions:
            collider = collision.collider
            obj = collider.parent

            if collider.group is Group.PLATFORMS:
                if self.grabbed:
                    self.collider.collisions.remove(collision)
                    continue

                bottom = self.collider.position[1] - delta_pos[1] - height
                platform_top = collider.position[1] + collider.half_height[1]
                if bottom < platform_top - 0.05:
                    self.collider.collisions.remove(collision)
                    continue

            if self.collider.group is Group.THROWN:
                # Can't hit self with thrown object
                if obj is self.parent:
                    self.collider.collisions.remove(collision)
                    continue

                # If hits another players's object, he drops it
                if obj.parent:
                    obj.parent.drop_object()

            if collision.overlap[1] > 0:
                self.on_ground = True
                if not self.parent:
                    if type(self.collider) is Rectangle:
                        self.angular_velocity = 5.0 * (self.collider.rest_angle() - self.angle)
                        if abs(self.angular_velocity) > 1.0:
                            self.sounds.add(self.bump_sound)
            elif collision.overlap[0] < 0:
                self.angular_velocity *= -1

            if not self.grabbed:
                n = min(int(self.speed / 3), 5)
                if n > 1:
                    self.sounds.add(self.bump_sound)
                    if self.dust:
                        v = min(0.2 * self.speed, 5.0) * normalized(collision.overlap)
                        self.particle_clouds.append(self.dust_particle(self.position, v, n))

            self.set_position(self.position + collision.overlap)

            if isinstance(collider.parent, PhysicsObject):
                if not self.grabbed:
                    obj.velocity[:] = 2 * self.mass / (self.mass + obj.mass) * self.velocity
                if self.blunt_damage and self.speed > 1.0:
                    if isinstance(collider.parent, Destroyable):
                        particle_type = obj.damage(self.speed * self.blunt_damage, colliders)
                        if particle_type:
                            self.particle_clouds.append(particle_type(self.position, 0.5 * self.velocity))

                n = collision.overlap
                self.velocity -= 2 * self.velocity.dot(n) * n / norm2(n)
                self.velocity *= -(self.mass - obj.mass) / (self.mass + obj.mass)
            else:
                n = collision.overlap
                self.velocity -= 2 * self.velocity.dot(n) * n / norm2(n)
                self.velocity *= self.bounce

        if self.collider:
            if self.collider.group is Group.THROWN and self.collider.collisions:
                self.parent = None
                self.collider.group = self.group

        self.acceleration += self.get_acceleration(gravity)
        self.velocity += self.acceleration * time_step
        self.acceleration[:] = 0
        self.angular_velocity += 0.5 * (ang_acc_old + self.angular_acceleration) * time_step

        if abs(self.velocity[0]) < 0.05:
            self.velocity[0] = 0.0

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        for p in self.particle_clouds:
            p.draw(batch, camera, image_handler)


class Destroyable(PhysicsObject):
    def __init__(self, position, velocity=(0, 0), image_path='', debris_path='', size=1.05, debris_size=1.0,
                 health=100, parent=None, bump_sound='bump'):
        super().__init__(position, velocity, image_path, size, bump_sound=bump_sound)
        self.health = health
        self.debris_path = debris_path
        self.destroyed = False
        self.debris = []
        self.debris_size = debris_size
        self.parent = parent
        self.fall_damage = 2
        self.fall_damage_speed = 15.0

    def delete(self):
        super().delete()
        for d in self.debris:
            d.delete()

    def get_data(self):
        return super().get_data() + (self.health, )

    def apply_data(self, data):
        super().apply_data(data)
        self.health = data[9]

    def damage(self, amount, colliders):
        if self.health > 0:
            self.health -= amount

        if self.health <= 0:
            self.destroy(colliders)

        return None

    def destroy(self, colliders):
        if self.destroyed:
            return

        self.collider.clear_occupied_squares(colliders)
        self.delete()

        self.destroyed = True

        self.camera_shake = self.speed * random_unit()

        if self.debris_path:
            for _ in range(3):
                r = np.abs(np.random.normal(15, 1.0))
                v = r * random_unit()
                d = PhysicsObject(self.position, v, image_path=self.debris_path, size=self.debris_size, dust=False)
                d.add_collider(Circle([0, 0], 0.1, Group.DEBRIS))
                d.angular_velocity = 10 * np.sign(d.velocity[0])
                self.debris.append(d)
        self.particle_clouds.append(Dust(self.position, np.zeros(2)))

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if not self.destroyed:
            if self.collider and self.collider.collisions:
                if self.speed > self.fall_damage_speed:
                    self.damage(self.speed * self.fall_damage, colliders)

        for d in self.debris:
            d.update(gravity, time_step, colliders)
            if d.on_ground and d.speed < norm(gravity) * time_step:
                d.delete()
                self.debris.remove(d)

        self.update_active()

    def update_active(self):
        if self.destroyed:
            self.active = False
            
            if self.debris:
                self.active = True
                return

            if self.particle_clouds:
                self.active = True

    def draw(self, batch, camera, image_handler):
        for d in self.debris:
            d.draw(batch, camera, image_handler)
        for p in self.particle_clouds:
            p.draw(batch, camera, image_handler)

        if not self.destroyed:
            super().draw(batch, camera, image_handler)

    def draw_shadow(self, screen, camera, image_handler, light):
        if not self.destroyed:
            super().draw_shadow(screen, camera, image_handler, light)
        elif self.shadow_sprite:
            self.shadow_sprite.delete()
            self.shadow_sprite = None

    def debug_draw(self, screen, camera, image_handler):
        super().debug_draw(screen, camera, image_handler)
        #camera.draw_text(str(self.health), self.position, 0.05, color=image_handler.debug_color)

    def play_sounds(self, sound_handler):
        super().play_sounds(sound_handler)

        for d in self.debris:
            d.play_sounds(sound_handler)


class Animation:
    def __init__(self, xs, ys, angles, image_path):
        self.xs = xs
        self.ys = ys
        self.angles = angles
        self.times = np.arange(len(xs)) / 15
        self.time = 0.0
        self.direction = 1
        self.image_path = image_path
        self.angle = 0.0

    def update(self, time_step):
        if self.time < 0:
            self.time += self.times[-1]
        if self.time > self.times[-1]:
            self.time -= self.times[-1]

        x = np.interp(self.time, self.times, self.xs)
        y = np.interp(self.time, self.times, self.ys)

        position = np.array([x, y])
        angle = np.interp(self.time, self.times, self.angles)

        self.time += time_step

        return position, angle

    def rotate(self, angle):
        for i in range(len(self.xs)):
            v = np.array([self.xs[i], self.ys[i]])
            v = rotate(v, angle)
            self.xs[i] = v[0]
            self.ys[i] = v[1]
            self.angles[i] += angle
        self.angle += angle


class AnimatedObject(GameObject):
    def __init__(self, position, image_path, size):
        super().__init__(position, image_path=image_path, size=size)
        self.animations = dict()
        self.animation = 'idle'
        self.animation_direction = 1
        self.loop = False
        self.animation_angle = 0.0
        self.relative_position = np.zeros(2)

    def current_animation(self):
        return self.animations[self.animation]

    def add_animation(self, xs, ys, angles, name, image=''):
        if not image:
            image = self.image_path
        self.animations[name] = Animation(xs, ys, angles, image)

    def loop_animation(self, name, time=0):
        if self.animation == name:
            return

        self.animation = name
        self.animations[self.animation].time = time
        self.loop = True

    def play_animation(self, name):
        self.animation = name
        self.animations[self.animation].time = 0
        self.loop = False

    def animate(self, time_step):
        anim = self.animations[self.animation]

        self.image_path = anim.image_path

        pos, angle = anim.update(self.animation_direction * time_step)

        pos[0] *= self.direction

        pos = rotate(pos, self.animation_angle)
        self.relative_position = pos

        self.set_position(self.position + pos)
        self.angle = self.direction * angle + self.animation_angle

        if not self.loop and anim.time >= anim.times[-1]:
            anim.time = anim.times[-1]
