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
        self.debug_color = (255, 0, 255)
        pyglet.resource.path = ['data/images', 'data/images/bodies', 'data/images/hands', 'data/images/heads',
                                'data/images/weapons']
        pyglet.resource.reindex()

        self.load_images()

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

        self.image_to_tiles('wall', 3, 1)
        self.image_to_tiles('wall_vertical', 1, 3)
        self.image_to_tiles('platform', 3, 1)

    def image_to_tiles(self, name, nx, ny):
        # TODO use ImageGrid
        image = self.images[name]
        width = image.width
        height = image.height
        tile_width = width // nx
        tile_height = height // ny

        for i in range(nx):
            for j in range(ny):
                self.images[f'{name}_{i}_{j}'] = image.get_region(i * tile_width, j * tile_height,
                                                                  tile_width, tile_height)
