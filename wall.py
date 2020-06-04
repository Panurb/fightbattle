import numpy as np
import pyglet
from PIL import Image
from numpy.linalg import norm

from gameobject import GameObject
from collider import Rectangle, Group, ColliderGroup, Circle
from helpers import basis


class Wall(GameObject):
    def __init__(self, position, width, height):
        super().__init__(position, image_path='wall', layer=2)
        self.add_collider(Rectangle([0, 0], width, height, Group.WALLS))
        self.size = 1.0
        self.vertical = 0

        self.image_position = -0.7 * basis(1)
        if width == 1:
            self.vertical = 1
            self.image_position = np.array([-0.5, -0.2])
            self.image_path = 'wall_vertical'

    def get_data(self):
        return (type(self), self.position[0], self.position[1],
                2 * self.collider.half_width[0], 2 * self.collider.half_height[1])

    def blit_to_image(self, image, image_handler):
        if self.vertical:
            d = self.collider.half_height[1]
        else:
            d = self.collider.half_width[0]

        n = int(2 * d)

        for i, x in enumerate(np.linspace(-d, d, n, False)):
            if i == 0:
                j = 0
            elif i == n - 1:
                j = 2
            else:
                j = 1

            decal = image_handler.tiles[self.image_path][j]
            size = [int(1.05 * x) for x in decal.size]
            decal = decal.resize(size, Image.ANTIALIAS)
            pos = [int((self.position[0] + self.image_position[0] + x * (1 - self.vertical)) * 100),
                   int((self.position[1] + self.image_position[1] + x * self.vertical) * 100)]
            image.paste(decal, pos, decal.convert('RGBA'))

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

    def draw_shadow(self, batch, camera, image_handler, light):
        if self.shadow_sprite is None:
            width = int(self.collider.width * 100) + 50
            height = int(self.collider.height * 100) + 100
            image = Image.new('RGBA', (width, height), (0, 0, 0, 0))

            pos = self.position.copy()
            self.position = self.collider.half_width + self.collider.half_height + 0.6 * basis(1)
            self.blit_to_image(image, image_handler)
            self.position[:] = pos

            image = pyglet.image.ImageData(width, height, 'RGBA', image.tobytes())
            self.shadow_sprite = pyglet.sprite.Sprite(img=image, x=0, y=0, batch=batch, group=camera.layers[1])
            self.shadow_sprite.color = (0, 0, 0)
            self.shadow_sprite.opacity = 128

        r = self.position - light
        pos = self.position + 0.5 * r / norm(r)

        x, y = camera.world_to_screen(pos - self.collider.half_width - self.collider.half_height)
        self.shadow_sprite.update(x, y - 0.5 * camera.zoom, scale=camera.zoom / 100)


class Platform(Wall):
    def __init__(self, position, width):
        super().__init__(position, width, 1)
        self.collider.group = Group.PLATFORMS
        self.image_path = 'platform'
        self.image_position = np.array([0.0, -0.1])

    def get_data(self):
        return type(self), self.position[0], self.position[1], 2 * self.collider.half_width[0]


class Basket(GameObject):
    def __init__(self, position, team='blue'):
        super().__init__(position, image_path='basket')
        self.image_position = np.array([0.4, -0.15])
        self.add_collider(ColliderGroup([0, 0]))
        self.collider.add_collider(Circle([-0.3, 0.0], 0.1, Group.WALLS))
        self.collider.add_collider(Circle([1.3, 0.0], 0.1, Group.WALLS))
        self.collider.add_collider(Circle([0.5, -0.5], 0.2, Group.GOALS))
        self.collider.add_collider(Rectangle([0.5, -0.9], 1.4, -0.5, Group.WALLS))
        self.team = team
        self.score = 0
        self.front = GameObject(self.position, 'basket_front', layer=4)
        self.front.image_position = np.array([0.4, -0.72])

    def change_team(self):
        self.team = 'blue' if self.team == 'red' else 'red'

    def set_position(self, position):
        super().set_position(position)
        self.front.set_position(position)

    def get_data(self):
        return type(self), self.position[0], self.position[1], self.team

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        self.front.draw(batch, camera, image_handler)

    def draw_shadow(self, batch, camera, image_handler, light):
        super().draw_shadow(batch, camera, image_handler, light)
        self.front.draw_shadow(batch, camera, image_handler, light)


class Scoreboard(GameObject):
    def __init__(self, position):
        super().__init__(position, layer=1)
        self.add_collider(Rectangle([0, 0], 7, 4))
        self.scores = {'blue': 0, 'red': 0}
        self.vertex_list = [None, None]
        self.labels = 3 * [None]

    def get_data(self):
        return tuple(self.position)

    def apply_data(self, data):
        self.set_position(np.array(data))

    def draw(self, batch, camera, image_handler):
        corners = self.collider.corners()
        self.vertex_list[0] = camera.draw_polygon(corners, (10, 10, 10), batch=batch,
                                                  layer=self.layer, vertex_list=self.vertex_list[0])
        self.vertex_list[1] = camera.draw_line(corners + [corners[0]], 1, (80, 80, 80),
                                               batch=batch, layer=self.layer, vertex_list=self.vertex_list[1])

        text = ' - '.join(map(str, self.scores.values()))
        self.labels = camera.draw_text(text, self.position, 2, 'Seven Segment.ttf', (200, 255, 0),
                                       batch=batch, layer=self.layer, labels=self.labels)
