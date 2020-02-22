import math
import pickle

import numpy as np
import pygame

import imagehandler
import inputhandler
import optionhandler
from level import Level
from prop import Crate


class Editor:
    def __init__(self):
        # init mixer first to prevent audio delay
        pygame.mixer.pre_init(44100, -16, 2, 2048)
        pygame.mixer.init()

        pygame.init()
        pygame.display.set_caption('NEXTGAME')

        self.option_handler = optionhandler.OptionsHandler()

        mode = 0
        if self.option_handler.fullscreen:
            mode = pygame.FULLSCREEN

        self.screen = pygame.display.set_mode(self.option_handler.resolution, mode)

        self.image_handler = imagehandler.ImageHandler()
        self.input_handler = inputhandler.InputHandler()

        self.clock = pygame.time.Clock()

        self.time_step = 15.0 / self.option_handler.fps

        self.font = pygame.font.Font(None, 30)

        self.level = Level(self.option_handler)

        self.grid_color = [150, 150, 150]

        self.wall_start = None

    def main_loop(self):
        while not self.input_handler.quit:
            self.input_handler.update(self.level)
            self.input()

            self.screen.fill((50, 50, 50))
            self.draw_grid(1.0)
            self.level.draw(self.screen, self.image_handler)

            self.draw_selection()

            pygame.display.update()
            self.clock.tick(self.option_handler.fps)

    def input(self):
        if self.input_handler.mouse_pressed[1]:
            self.wall_start = np.round(self.input_handler.mouse_position)

        if self.input_handler.mouse_released[1]:
            end = np.round(self.input_handler.mouse_position)
            pos = 0.5 * (self.wall_start + end)
            size = np.abs(end - self.wall_start)
            if np.all(size):
                self.level.add_wall(pos, size[0], size[1])
            self.wall_start = None

        if self.input_handler.mouse_down[1]:
            self.level.camera.position -= self.input_handler.mouse_change

        if self.input_handler.mouse_pressed[3]:
            for w in self.level.walls:
                if w.collider.point_inside(self.input_handler.mouse_position):
                    self.level.colliders[w.collider.group].remove(w.collider)
                    self.level.walls.remove(w)

            for w in self.level.players:
                if w.collider.point_inside(self.input_handler.mouse_position):
                    self.level.colliders[w.collider.group].remove(w.collider)
                    self.level.players.remove(w)

            for w in self.level.objects:
                if w.collider.point_inside(self.input_handler.mouse_position):
                    self.level.colliders[w.collider.group].remove(w.collider)
                    self.level.objects.remove(w)

        if self.input_handler.mouse_pressed[4]:
            self.level.camera.zoom *= 2

        if self.input_handler.mouse_pressed[5]:
            self.level.camera.zoom /= 2

        if self.input_handler.keys_pressed[pygame.K_s]:
            with open('lvl.pickle', 'wb') as f:
                pickle.dump(self.level, f)

        if self.input_handler.keys_pressed[pygame.K_p]:
            self.level.add_player(np.floor(self.input_handler.mouse_position) + np.array([0.5, 0.501]))

        if self.input_handler.keys_pressed[pygame.K_c]:
            self.level.add_object(Crate(np.floor(self.input_handler.mouse_position) + np.array([0.5, 0.501])))

    def draw_grid(self, size):
        x_min = math.floor(self.level.camera.position[0] - self.level.camera.half_width[0] / self.level.camera.zoom)
        x_max = math.ceil(self.level.camera.position[0] + self.level.camera.half_width[0] / self.level.camera.zoom)
        y_min = math.floor(self.level.camera.position[1] - self.level.camera.half_height[1] / self.level.camera.zoom)
        y_max = math.ceil(self.level.camera.position[1] + self.level.camera.half_height[1] / self.level.camera.zoom)

        for x in np.linspace(x_min, x_max, abs(x_max - x_min) // size + 1):
            if x % 5 == 0:
                width = 3
            else:
                width = 1
            pygame.draw.line(self.screen, self.grid_color, self.level.camera.world_to_screen([x, y_min]),
                             self.level.camera.world_to_screen([x, y_max]), width)

        for y in np.linspace(y_min, y_max, abs(y_max - y_min) // size + 1):
            if y % 5 == 0:
                width = 3
            else:
                width = 1
            pygame.draw.line(self.screen, self.grid_color, self.level.camera.world_to_screen([x_min, y]),
                             self.level.camera.world_to_screen([x_max, y]), width)

    def draw_selection(self):
        if self.wall_start is not None:
            end = np.round(self.input_handler.mouse_position)
            size = self.level.camera.zoom * (end - self.wall_start)
            size[1] *= -1
            pos = self.level.camera.world_to_screen(self.wall_start)
            rect = pygame.rect.Rect(pos[0], pos[1], size[0], size[1])
            pygame.draw.rect(self.screen, [255, 255, 255], rect, 5)


def main():
    editor_window = Editor()
    editor_window.main_loop()


if __name__ == "__main__":
    main()
