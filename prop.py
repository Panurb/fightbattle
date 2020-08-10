import numpy as np
import pyglet

from gameobject import PhysicsObject, Destroyable
from collider import Rectangle, Circle, Group
from helpers import random_unit
from particle import Sparks
from weapon import Revolver, Shotgun, Shield, Axe, Grenade, Bow


class Crate(Destroyable):
    def __init__(self, position):
        super().__init__(position, image_path='crate', debris_path='crate_debris', health=100)
        self.add_collider(Rectangle([0, 0], 1, 1, Group.BOXES))
        self.loot_list = [Revolver, Shotgun, Shield, Axe, Grenade, Bow]
        self.rotate(0.5 * np.pi * np.random.randint(0, 4))

    def apply_data(self, data):
        super().apply_data(data)
        #self.rotate(0.5 * np.pi * np.random.randint(0, 4))

    def destroy(self, colliders):
        if not self.destroyed:
            self.sounds.add('crate_break')
            self.gravity_scale = 0.0

        super().destroy(colliders)


class Box(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, image_path='box')
        self.add_collider(Rectangle([0, 0], 1, 1, Group.BOXES))
        self.rotate(0.5 * np.pi * np.random.randint(0, 4))
        self.mass = 2.0
        self.bump_sound = 'gun'

    def apply_data(self, data):
        super().apply_data(data)
        #self.rotate(0.5 * np.pi * np.random.randint(0, 4))


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


class Television(Destroyable):
    def __init__(self, position):
        super().__init__(position, image_path='television', debris_path='shard', health=1)
        self.add_collider(Rectangle([0, 0], 1.5, 1.2, group=Group.PROPS))
        self.mass = 3
        self.cracked = False
        self.fall_damage_speed = 5.0
        self.trigger = Circle(self.position, 3.0)
        self.triggered = False
        self.player = None

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        if not self.triggered:
            self.trigger.set_position(self.position)
            self.trigger.update_occupied_squares(colliders)
            self.trigger.update_collisions(colliders, {Group.PLAYERS})
            if self.trigger.collisions:
                self.triggered = True
                self.image_path = 'television_baddie'

        if self.cracked:
            self.player.delete()

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        #self.trigger.draw(batch, camera, image_handler)

    def play_sounds(self, sound_handler):
        super().play_sounds(sound_handler)
        if self.triggered and self.player is None:
            self.player = sound_handler.sounds['level1'].play()
            self.player.volume = sound_handler.volume
            self.player.on_eos = self.reset_path

    def reset_path(self):
        self.image_path = 'television'

    def destroy(self, colliders):
        if self.cracked:
            return

        self.cracked = True

        self.image_path = 'television_cracked'

        self.camera_shake = self.speed * random_unit()
        self.sounds.add('glass')

        for _ in range(4):
            r = np.abs(np.random.normal(15, 1.0))
            v = r * random_unit()
            d = PhysicsObject(self.position, v, image_path=self.debris_path, size=self.debris_size, dust=False)
            d.add_collider(Circle([0, 0], 0.1, Group.DEBRIS))
            d.angular_velocity = 10 * np.sign(d.velocity[0])
            self.debris.append(d)

        self.particle_clouds.append(Sparks(self.position, np.zeros(2)))
