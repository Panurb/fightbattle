import numpy as np


class Camera:
    def __init__(self, position):
        self.position = np.array(position, dtype=float)
        self.zoom = 50.0
        self.half_width = 0.5 * np.array([1280, 0.0])
        self.half_height = 0.5 * np.array([0.0, 720])

    def set_zoom(self, zoom):
        self.half_width *= zoom / self.zoom
        self.half_height *= zoom / self.zoom
        self.zoom = zoom

    def world_to_screen(self, position):
        pos = (position - self.position) * self.zoom + self.half_width - self.half_height
        pos[1] *= -1

        return [int(pos[0]), int(pos[1])]

    def screen_to_world(self, position):
        pos = np.array([position[0], -position[1]], dtype=float)
        pos = (pos - self.half_width + self.half_height) / self.zoom + self.position

        return pos
