import os

import numpy as np
import pygame


class ImageHandler:
    def __init__(self):
        self.camera = np.zeros(2)
        self.scale = 100
        self.images = dict()
        self.load_images()
        self.debug_color = (255, 0, 255)

    def load_images(self):
        path = os.path.join('data', 'images')

        for r, d, f in os.walk(path):
            for file in f:
                if '.png' in file:
                    try:
                        image = pygame.image.load(os.path.join(r, file))
                        image = image.convert_alpha()
                        self.images[file.replace('.png', '')] = image
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
                self.images[f'{name}_{i}_{j}'] = image.subsurface(rect)
