import numpy as np
from numpy.linalg import norm

from helpers import rotate


class Decal:
    def __init__(self, position, image_path, size=1.0, angle=0.0, layer=1):
        self.image_path = image_path
        self.position = np.array(position, dtype=float)
        self.angle = angle
        self.size = size
        self.sprite = None
        self.layer = layer

    def draw(self, batch, camera, image_handler):
        self.sprite = camera.draw_sprite(image_handler, self.image_path, self.position, self.size, angle=self.angle,
                                         batch=batch, layer=self.layer, sprite=self.sprite)


class Drawable(Decal):
    def __init__(self, position, image_path='', size=1.0, angle=0.0, layer=3):
        super().__init__(position, image_path, size, angle, layer)
        self.direction = 1
        self.angle = angle
        self.image_position = np.zeros(2)
        self.shadow_sprite = None

    def delete(self):
        if self.sprite:
            self.sprite.delete()
        if self.shadow_sprite:
            self.shadow_sprite.delete()

    def rotate(self, delta_angle):
        self.angle += delta_angle

    def flip_horizontally(self):
        self.direction *= -1
        self.image_position[0] *= -1

    def draw(self, batch, camera, image_handler):
        if not self.image_path:
            return

        pos = self.position + rotate(self.image_position, self.angle)
        self.sprite = camera.draw_sprite(image_handler, self.image_path, pos, self.size, self.direction, self.angle,
                                         batch=batch, layer=self.layer, sprite=self.sprite)

    def draw_shadow(self, batch, camera, image_handler, light):
        if not self.image_path:
            return

        r = self.position - light.position
        pos = self.position + 0.5 * r / norm(r) + rotate(self.image_position, self.angle)

        self.shadow_sprite = camera.draw_sprite(image_handler, self.image_path, pos, self.size, self.direction,
                                                self.angle, batch=batch, layer=2, sprite=self.shadow_sprite)
        self.shadow_sprite.color = (0, 0, 0)
        self.shadow_sprite.opacity = 128
