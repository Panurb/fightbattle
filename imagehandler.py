import os

from PIL import Image, ImageOps

import numpy as np
import pyglet
from pyglet.gl import *


class ImageHandler:
    def __init__(self):
        self.camera = np.zeros(2)
        self.scale = 100
        self.images = dict()
        self.decals = dict()
        self.tiles = dict()
        self.debug_color = (255, 0, 255)
        pyglet.resource.path = ['data/images', 'data/images/bodies', 'data/images/hands', 'data/images/heads',
                                'data/images/weapons', 'data/images/particles', 'data/images/icons',
                                'data/images/decals']
        pyglet.resource.reindex()

        self.load_images()
        # glEnable(GL_TEXTURE_2D)
        # glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        self.load_fonts()

        self.set_clear_color((50, 50, 50))

    def set_clear_color(self, color):
        pyglet.gl.glClearColor(color[0] / 255, color[1] / 255, color[2] / 255, 1)

    def load_fonts(self):
        path = os.path.join('data', 'fonts')
        for f in os.listdir(path):
            pyglet.font.add_file(os.path.join(path, f))

    def load_images(self):
        path = os.path.join('data', 'images')

        for r, d, f in os.walk(path):
            if r.endswith('decals'):
                for file in f:
                    if file.endswith('png'):
                        name = file.replace('.png', '')
                        img = Image.open(os.path.join(r, file))
                        self.decals[name] = ImageOps.mirror(img)
            elif r.endswith('tiles'):
                for file in f:
                    if file.endswith('png'):
                        name = file.replace('.png', '')
                        img = Image.open(os.path.join(r, file))
                        img = ImageOps.mirror(img)
                        if 'vertical' in name:
                            self.tiles[name] = self.image_to_tiles(img, 1, 3)
                        elif 'horizontal' in name or name == 'platform':
                            self.tiles[name] = self.image_to_tiles(img, 3, 1)
                        else:
                            self.tiles[name] = self.image_to_tiles(img, 3, 3)
                continue
            elif r.endswith('bodies'):
                for file in f:
                    if not file.endswith('png'):
                        continue

                    name = file.replace('.png', '')
                    image = pyglet.resource.image(file)

                    w = image.width // 2
                    h = image.height // 5

                    body = image.get_region(0, 0, w, image.height)
                    foot = image.get_region(w, 0, w, h)
                    lower_leg = image.get_region(w, h, w, h)
                    upper_leg = image.get_region(w, 2 * h, w, h)
                    lower_arm = image.get_region(w, 3 * h, w, h)
                    upper_arm = image.get_region(w, 4 * h, w, h)

                    names = ['body', 'foot', 'lower_leg', 'upper_leg', 'lower_arm', 'upper_arm']
                    for i, img in enumerate([body, foot, lower_leg, upper_leg, lower_arm, upper_arm]):
                        img.anchor_x = img.width // 2
                        img.anchor_y = img.height // 2
                        self.images[f'{names[i]}_{name}'] = img

                continue

            for file in f:
                if file.endswith('png'):
                    name = file.replace('.png', '')

                    image = pyglet.resource.image(file)
                    image.anchor_x = image.width // 2
                    image.anchor_y = image.height // 2
                    self.images[name] = image

    def image_to_tiles(self, image, nx, ny):
        width = image.width
        height = image.height
        tile_width = width // nx

        if ny == 3:
            ys = [0, int(0.5 * height) - 50, int(0.5 * height) + 50, height]
        else:
            ys = [0, height]

        tiles = []
        for i in range(nx):
            row = []
            for j in range(ny):
                tile = image.crop([i * tile_width, ys[ny - j - 1],
                                   (i + 1) * tile_width, ys[ny - j]])
                tile = ImageOps.flip(tile)
                row.append(tile)
            tiles.append(row)

        return tiles
