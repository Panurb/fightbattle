import numpy as np
from helpers import basis, norm2


class Camera:
    def __init__(self, position, resolution):
        self.position = np.array(position, dtype=float)
        self.max_zoom = resolution[1] / 720 * 50.0
        self.zoom = self.max_zoom
        self.half_width = 0.5 * resolution[0] * basis(0)
        self.half_height = 0.5 * resolution[1] * basis(1)
        self.shake = np.zeros(2)
        self.velocity = np.zeros(2)

    def update(self, time_step, players):
        cam_goal = sum(p.position for p in players.values()) / len(players)
        self.position[:] += time_step * (cam_goal - self.position)

        if len(players) > 1:
            dist2 = max(norm2(p.position - cam_goal) for p in players.values())
            zoom_goal = min(500 / (np.sqrt(dist2) + 1e-6), self.max_zoom)
            self.zoom += time_step * (zoom_goal - self.zoom)

        self.shake = sum(p.camera_shake for p in players.values())

    def set_zoom(self, zoom):
        self.half_width *= zoom / self.zoom
        self.half_height *= zoom / self.zoom
        self.zoom = zoom

    def world_to_screen(self, position):
        pos = (position - self.position) * self.zoom + self.half_width - self.half_height + self.shake
        pos[1] *= -1

        return [int(pos[0]), int(pos[1])]

    def screen_to_world(self, position):
        pos = np.array([position[0], -position[1]], dtype=float)
        pos = (pos - self.half_width + self.half_height - self.shake) / self.zoom + self.position

        return pos
