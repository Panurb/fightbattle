import os

import numpy as np
import pygame


SHADOW_COLOR = (80, 80, 80)


class ImageHandler:
    def __init__(self):
        self.camera = np.zeros(2)
        self.scale = 100
        self.images = dict()
        self.load_images()
        self.debug_color = (255, 0, 255)
        self.font = pygame.font.Font(None, 30)

    def load_images(self):
        path = os.path.join('data', 'images')

        for r, d, f in os.walk(path):
            if 'bodies' in r:
                suffix = f'_{r.split(os.sep)[-1]}'
            else:
                suffix = ''

            for file in f:
                if '.png' in file:
                    try:
                        image = pygame.image.load(os.path.join(r, file))
                        image = image.convert_alpha()
                        name = file.replace('.png', '') + suffix
                        self.images[name] = image

                        image = image.copy()
                        image.fill((0, 0, 0), special_flags=pygame.BLEND_MULT)
                        image.fill(SHADOW_COLOR, special_flags=pygame.BLEND_MAX)
                        self.images[f'shadow_{name}'] = image
                    except pygame.error as message:
                        raise SystemExit(message)

        self.image_to_tiles('wall', 3, 1)
        self.image_to_tiles('wall_vertical', 1, 3)
        self.image_to_tiles('platform', 3, 1)

    def image_to_tiles(self, name, nx, ny):
        image = self.images[name]
        width, height = image.get_size()
        tile_width = width // nx
        tile_height = height // ny

        for i in range(nx):
            for j in range(ny):
                rect = pygame.Rect(i * tile_width, j * tile_height, tile_width, tile_height)
                tile = image.subsurface(rect)
                self.images[f'{name}_{i}_{j}'] = image.subsurface(rect)

                tile = tile.copy()
                tile.fill((0, 0, 0), special_flags=pygame.BLEND_MULT)
                tile.fill(SHADOW_COLOR, special_flags=pygame.BLEND_MAX)
                self.images[f'shadow_{name}_{i}_{j}'] = tile
