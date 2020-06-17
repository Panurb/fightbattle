import os

from PIL import Image, ImageOps

import numpy as np
import pyglet


SHADOW_COLOR = (80, 80, 80)


class ImageHandler:
    def __init__(self):
        self.camera = np.zeros(2)
        self.scale = 100
        self.images = dict()
        self.decals = dict()
        self.tiles = dict()
        self.debug_color = (255, 0, 255)
        pyglet.resource.path = ['data/images', 'data/images/bodies', 'data/images/hands', 'data/images/heads',
                                'data/images/weapons', 'data/images/particles']
        pyglet.resource.reindex()

        self.load_images()

        self.set_clear_color((50, 50, 50))

    def set_clear_color(self, color):
        pyglet.gl.glClearColor(color[0] / 255, color[1] / 255, color[2] / 255, 1)

    def load_images(self):
        path = os.path.join('data', 'images')

        for r, d, f in os.walk(path):
            if 'decals' in r:
                for file in f:
                    if '.png' in file:
                        name = file.replace('.png', '')
                        img = Image.open(os.path.join(r, file))
                        self.decals[name] = ImageOps.mirror(img)

                continue

            if 'tiles' in r:
                for file in f:
                    if '.png' in file:
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

            if 'bodies' in r:
                prefix = f'{r.split(os.sep)[-1]}/'
                suffix = f'_{r.split(os.sep)[-1]}'
            else:
                prefix = ''
                suffix = ''

            for file in f:
                if '.png' in file:
                    name = file.replace('.png', '') + suffix

                    image = pyglet.resource.image(prefix + file)
                    image.anchor_x = image.width // 2
                    image.anchor_y = image.height // 2
                    self.images[name] = image

                    image = pyglet.resource.image(prefix + file, flip_x=True)
                    image.anchor_x = image.width // 2
                    image.anchor_y = image.height // 2
                    self.images[name + '_flipped'] = image

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
