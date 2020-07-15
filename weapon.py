import numpy as np
from numpy.linalg import norm

from bullet import Pellet, Bullet, Arrow
from gameobject import PhysicsObject, Destroyable, GameObject
from collider import Rectangle, Circle, Group
from helpers import basis, polar_to_cartesian, rotate, random_unit, normalized
from particle import MuzzleFlash, Explosion, Dust, Sparks


class Weapon(PhysicsObject):
    def __init__(self, position, image_path):
        super().__init__(position, image_path=image_path, bump_sound='gun')
        self.hand_position = np.zeros(2)
        self.attacked = False
        self.hit = False
        self.attack_delay = 0.25
        self.timer = 0.0

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)
        self.timer = max(0.0, self.timer - time_step)

    def attack(self):
        self.attacked = False
        self.timer = self.attack_delay

        return []


class Gun(Weapon):
    def __init__(self, position, image_path):
        super().__init__(position, image_path=image_path)
        self.barrel_position = np.array([0.7, 0.3])
        self.grip_position = None
        self.bullet_speed = 45.0

    def get_data(self):
        return super().get_data() + (self.attacked, )

    def apply_data(self, data):
        super().apply_data(data)
        self.attacked = data[-1]

    def get_hand_position(self):
        v = self.hand_position.copy()
        v[0] *= self.direction
        return self.position + rotate(v, self.angle)

    def get_grip_position(self):
        v = self.grip_position.copy()
        v[0] *= self.direction
        return self.position + rotate(v, self.angle)

    def get_barrel_position(self):
        v = self.barrel_position.copy()
        v[0] *= self.direction
        return self.position + rotate(v, self.angle)

    def attack(self):
        super().attack()
        v = self.direction * polar_to_cartesian(0.1, self.angle)
        self.particle_clouds.append(MuzzleFlash(self.get_barrel_position(), v))

        return []

    def play_sounds(self, sound_handler):
        super().play_sounds(sound_handler)


class Revolver(Gun):
    def __init__(self, position):
        super().__init__(position, 'revolver')
        self.image_position = np.array([0.35, 0.15])
        self.add_collider(Rectangle([0.35, 0.29], 1.1, 0.3, Group.WEAPONS))

    def attack(self):
        bs = super().attack()
        self.sounds.add('revolver')
        v = self.direction * self.bullet_speed * polar_to_cartesian(1, self.angle)
        bs.append(Bullet(self.get_barrel_position(), v, self.parent))
        self.angular_velocity += self.direction * 15
        self.velocity -= 2 * self.collider.half_width / self.collider.width * self.direction * 10
        return bs


class Shotgun(Gun):
    def __init__(self, position):
        super().__init__(position, 'shotgun')
        self.size = 0.9
        self.image_position = np.array([0, -0.1])
        self.add_collider(Rectangle([0, 0.08], 1.8, 0.3, Group.WEAPONS))
        self.bullet_speed = 30.0
        self.hand_position = np.array([-0.7, -0.2])
        self.grip_position = np.array([0.45, -0.05])
        self.attack_delay = 0.75
        self.mass = 1.5

    def attack(self):
        bs = super().attack()
        self.sounds.add('shotgun')
        theta = self.angle - 0.1
        for _ in range(3):
            theta += 0.1
            v = self.direction * np.random.normal(self.bullet_speed, 0.05) * polar_to_cartesian(1, theta)
            bs.append(Pellet(self.get_barrel_position(), v, self.parent))
        self.angular_velocity += self.direction * 15
        self.velocity -= 2 * self.collider.half_width / self.collider.width * self.direction * 10
        self.velocity += 2 * self.collider.half_height / self.collider.height * 10

        return bs


class Axe(Weapon):
    def __init__(self, position):
        super().__init__(position, image_path='axe')
        self.bump_sound = 'sword'
        self.add_collider(Rectangle([0.25, 0.2], 0.6, 1.5, Group.SHIELDS))
        self.image_position = np.array([0.25, 0.2])
        self.rotate(np.pi / 2)
        self.hit = False
        self.timer = 0.0
        self.parent = None
        self.rest_angle = 0.5 * np.pi
        self.blunt_damage = 60
        self.attack_delay = 0.5
        self.mass = 0.7

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if self.timer > 0 and self.hit:
            return

        if self.attacked:
            self.attack()

        if self.collider.collisions:
            if self.parent is not None and self.timer > 0:
                self.sounds.add('sword')
                self.parent.camera_shake = 10 * random_unit()
                v = -5 * self.direction * basis(0)
                self.particle_clouds.append(Sparks(self.position + self.collider.half_height, v))
            self.hit = True
            return

        if self.grabbed and self.timer > 0:
            self.collider.update_collisions(colliders, [Group.HITBOXES, Group.PROPS, Group.SHIELDS])

            for c in self.collider.collisions:
                obj = c.collider.parent
                if obj not in {self.parent.body, self.parent.head}:
                    if isinstance(obj, PhysicsObject):
                        r = normalized(self.collider.position - obj.collider.position)
                        obj.velocity -= r
                        if isinstance(obj, Destroyable):
                            particle_type = obj.damage(50, colliders)
                            if particle_type:
                                self.particle_clouds.append(particle_type(self.position, 5.0 * r))
                    self.hit = True
                    self.parent.camera_shake = 10 * random_unit()
                    break

    def attack(self):
        super().attack()
        self.hit = False
        self.sounds.add('swing')
        self.angular_velocity -= self.direction * 20
        self.velocity[1] -= 10


class Shield(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, image_path='shield', size=0.85, bump_sound='gun')
        self.add_collider(Rectangle([0, 0], 0.5, 2.0, Group.SHIELDS))
        self.rest_angle = 0.5 * np.pi
        self.mass = 2.0


class Grenade(Destroyable):
    def __init__(self, position):
        super().__init__(position, bump_sound='gun', health=1)
        self.image_path = 'grenade'
        self.size = 1.1
        self.add_collider(Circle([0, 0], 0.25, Group.PROPS))
        self.timer = 0.0
        self.primed = False
        self.pin = PhysicsObject(self.position, image_path='grenade_pin')
        self.pin.add_collider(Circle([0, 0], 0.25, Group.DEBRIS))
        self.destroyed = False
        self.attacked = False
        self.camera_shake = np.zeros(2)
        self.roll = True
        self.fall_damage = 0
        self.delay = 3.0
        self.mass = 0.5
        self.decal = ''

    def delete(self):
        super().delete()
        if self.pin:
            self.pin.delete()

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if self.primed:
            if self.pin:
                self.pin.update(gravity, time_step, colliders)
            self.timer -= time_step

            if self.timer <= 0.0:
                self.destroy(colliders)
        else:
            if self.pin:
                self.pin.set_position(self.position + 0.15 * rotate(basis(0), self.angle))
                self.pin.rotate(self.angle - self.pin.angle)

    def destroy(self, colliders):
        if not self.destroyed:
            if self.sprite:
                self.sprite.delete()
                self.sprite = None
            self.destroyed = True

            if self.pin:
                if self.pin.sprite:
                    self.pin.sprite.delete()
                self.pin = None

            explosion_collider = Circle(self.position, 3.0)
            explosion_collider.update_occupied_squares(colliders)
            explosion_collider.update_collisions(colliders, {Group.PLAYERS, Group.PROPS})

            for c in explosion_collider.collisions:
                obj = c.collider.parent
                if obj is self:
                    continue

                r = obj.position - self.position
                r_norm = norm(r)

                obj.velocity += 10 * (5 - r_norm) * r / r_norm

                if isinstance(obj, Destroyable):
                    particle_type = obj.damage(int(abs(30 * (5 - r_norm))), colliders)
                    if particle_type:
                        self.particle_clouds.append(particle_type(obj.position, 5 * r))

            self.particle_clouds.append(Explosion(self.position))
            self.sounds.add('grenade')

            self.collider.clear_occupied_squares(colliders)
            self.collider = None

            self.camera_shake = 100 * random_unit()
            self.decal = 'ash'

    def attack(self):
        if not self.primed:
            self.pin.velocity[0] = self.velocity[0] - self.direction * 2.5
            self.pin.velocity[1] = 5.0
            self.primed = True
            self.timer = self.delay
            self.sounds.add('pin')

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        if self.pin:
            self.pin.draw(batch, camera, image_handler)


class Bow(Gun):
    def __init__(self, position):
        super().__init__(position, 'bow')
        self.bump_sound = 'bump'
        self.image_path = 'bow'
        self.add_collider(Rectangle([0, 0], 0.5, 1.9, Group.WEAPONS))
        self.bullet_speed = 30.0
        self.rotate(np.pi / 2)
        self.hand_position = -0.2 * basis(0)
        self.barrel_position = 0.5 * basis(0)
        self.grip_position = 0.2 * basis(0)
        self.string_upper = np.array([-0.22, 1.0])
        self.string_lower = np.array([-0.22, -1.0])
        self.string_middle = np.zeros(2)
        self.timer = 0.0
        self.string_width = 0.05
        self.string_color = (50, 50, 50)
        self.attack_charge = 0.0
        self.string = None
        self.layer = 3
        self.attack_delay = 0.67
        self.charge_speed = 1.0

        self.arrow = GameObject(self.position, 'arrow', size=1.2, layer=5)
        self.arrow.image_position = 0.5 * basis(0)

    def delete(self):
        super().delete()
        self.string.delete()
        self.arrow.delete()

    def get_data(self):
        return super().get_data() + (self.attack_charge, )

    def apply_data(self, data):
        super().apply_data(data)
        self.attack_charge = data[-1]

    def flip_horizontally(self):
        super().flip_horizontally()
        self.arrow.flip_horizontally()

    def update(self, gravity, time_step, colliders):
        Weapon.update(self, gravity, time_step, colliders)

        if self.parent:
            if self.timer == 0.0 and self.parent.attack_charge > 0.0:
                self.hand_position[0] = -(0.2 + 0.6 * self.parent.attack_charge)
                self.arrow.set_position(self.get_hand_position())
                self.arrow.angle = self.parent.hand.angle
            else:
                self.hand_position[0] = -0.8
                self.timer = max(0.0, self.timer - time_step)
        else:
            self.hand_position[0] = -0.2
            self.timer = 0.0

        self.string_middle[0] *= -0.7

    def attack(self):
        if self.timer == 0.0:
            self.attacked = False
            self.sounds.add('bow_release')
            v = self.direction * self.attack_charge * self.bullet_speed * polar_to_cartesian(1, self.angle)
            self.timer = self.attack_delay
            self.attack_charge = 0.0
            self.string_middle[0] = 0.5 * self.direction

            return [Arrow(self.get_barrel_position(), v, self.parent)]

        return []

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)

        if self.arrow.sprite:
            if self.attack_charge:
                self.arrow.sprite.visible = True
            else:
                self.arrow.sprite.visible = False

        a = self.position + self.direction * rotate(self.string_upper, self.angle)
        c = self.position + self.direction * rotate(self.string_lower, self.angle)
        if self.attack_charge:
            b = self.get_hand_position()
        else:
            b = (a + c) / 2 + rotate(self.string_middle, self.angle)

        self.string = camera.draw_line([a, b, c], self.string_width, self.string_color,
                                       batch=batch, layer=self.layer+2, vertex_list=self.string)
