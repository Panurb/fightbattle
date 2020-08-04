import numpy as np
import pyglet
from PIL import Image

from gameobject import GameObject, Destroyable
from collider import Rectangle, Group
from helpers import basis, normalized
from text import Text


class Wall(GameObject):
    def __init__(self, position, width, height):
        super().__init__(position, image_path='wall', layer=3)
        self.add_collider(Rectangle([0, 0], width, height, Group.WALLS))
        self.image_position = np.array([0.0, -0.2])

        if width == 1:
            self.image_path = 'wall_vertical'

        if height == 1:
            self.image_path = 'wall_horizontal'

        self.border = False

    def get_data(self):
        return type(self), self.position[0], self.position[1], self.collider.width, self.collider.height

    def blit_to_image(self, image, image_handler, light=None):
        if self.border:
            self.image_path = 'wall'
            if light is not None:
                return

        w = 0.5 * self.collider.width
        h = 0.5 * self.collider.height
        nx = int(self.collider.width)
        ny = int(self.collider.height)

        for i, x in enumerate(np.linspace(-w, w, nx, False)):
            n = 1
            if not self.border:
                if i == 0:
                    n = 0
                elif i == nx - 1:
                    n = 2
            if nx == 1:
                n = 0
            if self.border and int(self.position[0]) == 0:
                n = 2

            for j in range(ny):
                m = 1
                if not self.border:
                    if j == 0:
                        m = 0
                    elif j == ny - 1:
                        m = 2
                if ny == 1:
                    m = 0
                if self.border and int(self.position[1]) == 0:
                    m = 2

                pos = self.position + self.image_position + np.array([x, j - h])
                decal = image_handler.tiles[self.image_path][n][m]
                size = [int(1.05 * s) for s in decal.size]
                decal = decal.resize(size, Image.ANTIALIAS)
                mask = decal.convert('RGBA')

                if light is not None:
                    decal = decal.convert('L').point(lambda _: 0, mode='1').convert('RGBA')
                    decal.putalpha(128)

                    shadow_offset = 0.5 * normalized(self.position - light.position)
                    image.paste(decal, [int(p * 100) for p in pos + shadow_offset], mask)
                else:
                    image.paste(decal, [int(p * 100) for p in pos], mask)

    def draw(self, batch, camera, image_handler):
        if self.sprite is None:
            width = int(self.collider.width * 100) + 50
            height = int(self.collider.height * 100) + 100
            image = Image.new('RGBA', (width, height), (0, 0, 0, 0))

            pos = self.position.copy()
            self.position = self.collider.half_width + self.collider.half_height + 0.6 * basis(1)
            self.blit_to_image(image, image_handler)
            self.position[:] = pos

            image = pyglet.image.ImageData(width, height, 'RGBA', image.tobytes())
            self.sprite = pyglet.sprite.Sprite(img=image, x=0, y=0, batch=batch, group=camera.layers[self.layer])

        x, y = camera.world_to_screen(self.position - self.collider.half_width - self.collider.half_height)
        self.sprite.update(x, y - 0.5 * camera.zoom, scale=camera.zoom / 100)


class Platform(Wall):
    def __init__(self, position, width):
        super().__init__(position, width, 1)
        self.collider.group = Group.PLATFORMS
        self.image_path = 'platform'
        self.image_position = np.array([0.0, 0.45])

    def get_data(self):
        return type(self), self.position[0], self.position[1], 2 * self.collider.half_width[0]


class Scoreboard(GameObject):
    def __init__(self, position):
        super().__init__(position, image_path='scoreboard', layer=1)
        self.add_collider(Rectangle([0, 0], 7, 4))
        self.teams = ['blue', 'red']
        self.scores = {t: 0 for t in self.teams}
        self.text = Text('00 - 00', self.position, 2, 'Seven Segment', (200, 255, 0), layer=self.layer+1)

    def set_position(self, position):
        super().set_position(position)
        self.text.position[:] = position

    def delete(self):
        super().delete()
        self.text.delete()

    def get_data(self):
        return tuple(self.position)

    def apply_data(self, data):
        self.set_position(np.array(data))

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        self.text.string = '-'.join(map(lambda x: str(x) if x > 9 else '0' + str(x), self.scores.values()))
        self.text.draw(batch, camera, image_handler)


class Barrier(Wall, Destroyable):
    def __init__(self, position, width=1, height=1):
        Destroyable.__init__(self, position, health=10, image_path='wall', debris_path='crate_debris')
        self.add_collider(Rectangle([0, 0], width, height, Group.BARRIERS))
        self.image_position[:] = [0.0, -0.5]

        if width == 1:
            self.image_path = 'barrier_vertical'

        if height == 1:
            self.image_path = 'barrier_horizontal'

        self.border = False
        self.gravity_scale = 0.0

    def delete(self):
        Destroyable.delete(self)

    def get_data(self):
        return self.id, type(self), self.position[0], self.position[1], self.collider.width, self.collider.height

    def apply_data(self, data):
        self.set_position(data[2:4])
        self.collider.width = data[4]
        self.collider.height = data[5]
        self.collider.half_width[0] = 0.5 * self.collider.width
        self.collider.half_height[1] = 0.5 * self.collider.height

        if self.collider.width == 1:
            self.image_path = 'barrier_vertical'

        if self.collider.height == 1:
            self.image_path = 'barrier_horizontal'

    def update(self, gravity, time_step, colliders):
        if self.destroyed:
            super().update(gravity, time_step, colliders)

    def blit_to_image(self, image, image_handler, light=None):
        Wall.blit_to_image(self, image, image_handler, light)

    def draw(self, batch, camera, image_handler):
        if self.destroyed:
            Destroyable.draw(self, batch, camera, image_handler)
        else:
            Wall.draw(self, batch, camera, image_handler)
