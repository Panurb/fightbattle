import numpy as np
import pygame

from helpers import basis, norm2, rotate


class Camera:
    def __init__(self, position, resolution):
        self.position = np.array(position, dtype=float)
        self.max_zoom = resolution[1] / 720 * 50.0
        self.zoom = self.max_zoom
        self.half_width = 0.5 * resolution[0] * basis(0)
        self.half_height = 0.5 * resolution[1] * basis(1)
        self.shake = np.zeros(2)
        self.velocity = np.zeros(2)

    def set_resolution(self, resolution):
        self.max_zoom = resolution[1] / 720 * 50.0
        self.zoom = self.max_zoom
        self.half_width = 0.5 * resolution[0] * basis(0)
        self.half_height = 0.5 * resolution[1] * basis(1)

    def update(self, time_step, players, level):
        cam_goal = sum(p.position for p in players.values()) / len(players)

        #cam_goal[0] = max(cam_goal[0], self.half_width[0] / self.zoom)
        #cam_goal[0] = min(cam_goal[0], level.width - self.half_width[0] / self.zoom)

        if level.height > 2 * self.half_height[1] / self.zoom:
            cam_goal[1] = max(cam_goal[1], self.half_height[1] / self.zoom)
            cam_goal[1] = min(cam_goal[1], level.height - self.half_height[1] / self.zoom)
        else:
            cam_goal[1] = level.position[1]

        self.position[:] += time_step * (cam_goal - self.position)

        if len(players) > 1:
            dist2 = max(norm2(p.position - cam_goal) for p in players.values())
            zoom_goal = max(min(500 / (np.sqrt(dist2) + 1e-6), self.max_zoom), level.width)
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

    def draw_image(self, screen, image, position, size, direction, angle):
        scale = 1.05 * self.zoom * size / 100

        if direction == -1:
            image = pygame.transform.flip(image, True, False)

        image = pygame.transform.rotozoom(image, np.degrees(angle), scale)

        rect = image.get_rect()
        rect.center = self.world_to_screen(position)

        screen.blit(image, rect)

    def draw_text(self, screen, string, position, size, font='', color=(255, 255, 255), chromatic_aberration=False):
        if not font:
            font = pygame.font.Font(None, int(size * self.zoom))
        else:
            font = pygame.font.Font(f'data/fonts/{font}', int(size * self.zoom))

        pos = self.world_to_screen(position)

        if chromatic_aberration:
            text = font.render(string, True, (255, 0, 0))
            screen.blit(text, [pos[0] - text.get_width() // 2 - size, pos[1] - text.get_height() // 2])

            text = font.render(string, True, (0, 255, 255))
            screen.blit(text, [pos[0] - text.get_width() // 2 + size + 1, pos[1] - text.get_height() // 2])

        text = font.render(string, True, color)
        screen.blit(text, [pos[0] - text.get_width() // 2, pos[1] - text.get_height() // 2])

    def draw_triangle(self, screen, position, size, angle=0, color=(255, 255, 255), chromatic_aberration=False):
        a = size * rotate(np.array([0, 0.5]), angle)
        b = size * rotate(np.array([0, -0.5]), angle)
        c = size * rotate(np.array([np.sqrt(3) / 2, 0]), angle)

        if chromatic_aberration:
            offset = 0.05 * size * basis(0)

            points = [self.world_to_screen(-self.zoom / 100 * p + position - offset) for p in [a, b, c]]
            pygame.draw.polygon(screen, (255, 0, 0), points)

            points = [self.world_to_screen(-self.zoom / 100 * p + position + offset) for p in [a, b, c]]
            pygame.draw.polygon(screen, (0, 255, 0), points)

        points = [self.world_to_screen(-self.zoom / 100 * p + position) for p in [a, b, c]]
        pygame.draw.polygon(screen, color, points)

    def draw_polygon(self, screen, points, color=(255, 255, 255), width=1):
        points = [self.world_to_screen(p) for p in points]
        pygame.draw.polygon(screen, color, points, width)

    def draw_circle(self, screen, position, radius, color=(255, 255, 255), width=1):
        pos = self.world_to_screen(position)
        r = int(self.zoom * radius)
        pygame.draw.circle(screen, color, pos, r, width)
