import math
import pickle

import numpy as np
import pygame

import imagehandler
import inputhandler
import optionhandler
from camera import Camera
from level import Level, PlayerSpawn
from prop import Crate
from weapon import Weapon, Revolver


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

        self.level = Level()

        self.grid_color = [150, 150, 150]

        self.wall_start = None
        self.grabbed_object = None
        self.grab_offset = np.zeros(2)
        self.object_types = ['wall', 'scaffolding']
        self.type_index = 0

        self.camera = Camera([0, 0], self.option_handler.resolution)

    def main_loop(self):
        while not self.input_handler.quit:
            self.input_handler.update(self.camera)
            self.input()

            if self.grabbed_object is not None:
                w = self.grabbed_object.collider.half_width
                h = self.grabbed_object.collider.half_height
                pos = np.floor(self.input_handler.mouse_position + self.grab_offset - np.floor(w) - np.floor(h))
                self.grabbed_object.set_position(pos + w + h)

            self.screen.fill((50, 50, 50))
            self.draw_grid(1.0)
            self.level.draw(self.screen, self.camera, self.image_handler)

            for p in self.level.player_spawns:
                p.draw(self.screen, self.camera, self.image_handler)

            self.draw_selection()

            type_str = self.font.render(self.object_types[self.type_index], True, self.image_handler.debug_color)
            self.screen.blit(type_str, (50, 50))

            pygame.display.update()
            self.clock.tick(self.option_handler.fps)

    def input(self):
        if self.input_handler.mouse_pressed[1]:
            for obj in self.level.walls + self.level.player_spawns + self.level.objects:
                if obj.collider.point_inside(self.input_handler.mouse_position):
                    self.grabbed_object = obj
                    self.grab_offset = self.grabbed_object.position - self.input_handler.mouse_position
                    break
            else:
                self.wall_start = np.round(self.input_handler.mouse_position)

        if self.input_handler.mouse_released[1]:
            if self.grabbed_object is not None:
                if isinstance(self.grabbed_object, Weapon):
                    for obj in self.level.objects:
                        if type(obj) is Crate and obj.collider.point_inside(self.input_handler.mouse_position):
                            obj.loot_list.append(type(obj))
                            self.level.objects.remove(self.grabbed_object)
                            break

                self.grabbed_object = None
            else:
                end = np.round(self.input_handler.mouse_position)
                pos = 0.5 * (self.wall_start + end)
                size = np.abs(end - self.wall_start)
                if np.all(size):
                    if self.type_index == 0:
                        self.level.add_wall(pos, size[0], size[1])
                    else:
                        self.level.add_platform(pos, size[0])
                self.wall_start = None

        if self.input_handler.mouse_down[1]:
            self.camera.position -= self.input_handler.mouse_change

        if self.input_handler.mouse_pressed[3]:
            for w in self.level.walls:
                if w.collider.point_inside(self.input_handler.mouse_position):
                    self.level.walls.remove(w)

            for w in self.level.player_spawns:
                if w.collider.point_inside(self.input_handler.mouse_position):
                    self.level.player_spawns.remove(w)

            for w in self.level.objects:
                if w.collider.point_inside(self.input_handler.mouse_position):
                    self.level.objects.remove(w)

        if self.input_handler.mouse_pressed[4]:
            self.camera.zoom *= 1.5

        if self.input_handler.mouse_pressed[5]:
            self.camera.zoom /= 1.5

        if self.input_handler.keys_pressed[pygame.K_s]:
            with open('lvl.pickle', 'wb') as f:
                pickle.dump(self.level, f)

        if self.input_handler.keys_pressed[pygame.K_l]:
            with open('lvl.pickle', 'rb') as f:
                self.level = pickle.load(f)

        if self.input_handler.keys_pressed[pygame.K_w]:
            if self.type_index == len(self.object_types) - 1:
                self.type_index = 0
            else:
                self.type_index += 1

        if self.input_handler.keys_pressed[pygame.K_p]:
            pos = np.floor(self.input_handler.mouse_position) + np.array([0.5, 0.501])
            self.level.player_spawns.append(PlayerSpawn(pos))

        if self.input_handler.keys_pressed[pygame.K_c]:
            self.level.add_object(Crate(np.floor(self.input_handler.mouse_position) + np.array([0.5, 0.501])))

        if self.input_handler.keys_pressed[pygame.K_r]:
            self.level.add_object(Revolver(np.floor(self.input_handler.mouse_position) + np.array([0.5, 0.501])))

    def draw_grid(self, size):
        x_min = math.floor(self.camera.position[0] - self.camera.half_width[0] / self.camera.zoom)
        x_max = math.ceil(self.camera.position[0] + self.camera.half_width[0] / self.camera.zoom)
        y_min = math.floor(self.camera.position[1] - self.camera.half_height[1] / self.camera.zoom)
        y_max = math.ceil(self.camera.position[1] + self.camera.half_height[1] / self.camera.zoom)

        for x in np.linspace(x_min, x_max, abs(x_max - x_min) // size + 1):
            if x % 5 == 0:
                width = 3
            else:
                width = 1
            pygame.draw.line(self.screen, self.grid_color, self.camera.world_to_screen([x, y_min]),
                             self.camera.world_to_screen([x, y_max]), width)

        for y in np.linspace(y_min, y_max, abs(y_max - y_min) // size + 1):
            if y % 5 == 0:
                width = 3
            else:
                width = 1
            pygame.draw.line(self.screen, self.grid_color, self.camera.world_to_screen([x_min, y]),
                             self.camera.world_to_screen([x_max, y]), width)

    def draw_selection(self):
        if self.wall_start is not None:
            end = np.round(self.input_handler.mouse_position)
            size = self.camera.zoom * (end - self.wall_start)
            size[1] *= -1
            pos = self.camera.world_to_screen(self.wall_start)
            rect = pygame.rect.Rect(pos[0], pos[1], size[0], size[1])
            pygame.draw.rect(self.screen, [255, 255, 255], rect, 5)


def main():
    editor_window = Editor()
    editor_window.main_loop()


if __name__ == "__main__":
    main()
