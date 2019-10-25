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
