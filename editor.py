import math
import os
import pickle

import numpy as np
import pyglet
from numpy.linalg import norm
from pyglet.window import key
from pyglet.window import mouse

from imagehandler import ImageHandler
from optionhandler import OptionHandler
from camera import Camera
from goal import Exit, Basket, Goal
from level import Level, PlayerSpawn
from prop import Crate, Ball, Box, Television
from text import Text
from wall import Scoreboard, Wall, Platform, Barrier
from weapon import Revolver, Shotgun, Bow, Grenade, Axe, Shield, Sniper, SawedOff, MachineGun


class Editor(pyglet.window.Window):
    def __init__(self):
        self.option_handler = OptionHandler()
        self.image_handler = ImageHandler()

        width, height = self.option_handler.resolution
        super().__init__(width, height, vsync=self.option_handler.vsync, fullscreen=False)

        # background color
        pyglet.gl.glClearColor(0.2, 0.2, 0.2, 1)

        self.fps_display = pyglet.window.FPSDisplay(window=self)

        self.batch = pyglet.graphics.Batch()

        self.level = Level(editor=True)

        self.grid_color = (150, 150, 150)

        self.camera = Camera([0, 0], self.option_handler.resolution)

        self.wall_start = None
        self.grabbed_object = None
        self.grab_offset = np.zeros(2)
        self.grab_start = np.zeros(2)
        self.object_types = [Wall, Platform, Barrier, Scoreboard, PlayerSpawn, Exit, Television, Basket, Crate, Box,
                             Ball, Revolver, Shotgun, Bow, Grenade, Axe, Shield, SawedOff, Sniper, MachineGun]
        self.type_index = 0
        self.type_text = Text('', np.zeros(2), 0.5)

        self.mouse_position = np.zeros(2)

        self.type_select = False

        self.path = os.path.join('data', 'levels', 'multiplayer', 'circle')

    def on_key_press(self, symbol, modifiers):
        if symbol == key.S:
            for i, o in enumerate(self.level.objects.values()):
                o.id = i
            with open(self.path + '.pickle', 'wb') as f:
                pickle.dump(self.level.get_data(), f)
        elif symbol == key.L:
            with open(self.path + '.pickle', 'rb') as f:
                data = pickle.load(f)
                self.level.clear()
                self.level.apply_data(data)
        elif symbol == key.DELETE:
            self.level.clear()
        elif symbol == key.SPACE:
            self.type_select = True

    def on_key_release(self, symbol, modifiers):
        if symbol == key.SPACE:
            self.type_select = False

    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse_position[:] = self.camera.screen_to_world([x, y])

    def get_objects(self):
        objects = self.level.walls + self.level.player_spawns + list(self.level.objects.values()) + self.level.goals
        if self.level.scoreboard:
            objects.append(self.level.scoreboard)
        return objects

    def on_mouse_press(self, x, y, button, modifiers):
        if button == mouse.LEFT:
            for obj in self.get_objects():
                if obj.collider.point_inside(self.mouse_position):
                    self.grabbed_object = obj
                    self.grab_offset = self.grabbed_object.position - self.mouse_position
                    self.grab_start = np.round(self.mouse_position)
                    break
            else:
                if self.type_index < 3:
                    self.wall_start = np.round(self.mouse_position)
                else:
                    pos = np.floor(self.mouse_position) + np.array([0.5, 0.501])
                    obj = self.object_types[self.type_index](pos)
                    self.grabbed_object = obj

                    if type(obj) is Scoreboard:
                        self.level.scoreboard = obj
                    elif type(obj) is PlayerSpawn:
                        self.level.player_spawns.append(obj)
                    elif isinstance(obj, Goal):
                        self.level.goals.append(obj)
                    else:
                        self.level.add_object(obj)

    def on_mouse_release(self, x, y, button, modifiers):
        mouse_pos = self.camera.screen_to_world([x, y])

        if button == mouse.LEFT:
            if self.grabbed_object is not None:
                if type(self.grabbed_object) in {PlayerSpawn, Basket}:
                    if norm(np.round(self.mouse_position) - self.grab_start) < 1.0:
                        self.grabbed_object.change_team()
                        return

                self.grabbed_object = None
            else:
                end = np.round(self.mouse_position)
                pos = 0.5 * (self.wall_start + end)
                size = np.abs(end - self.wall_start)
                if np.all(size):
                    if self.type_index == 0:
                        self.level.add_wall(pos, size[0], size[1])
                    elif self.type_index == 1:
                        self.level.add_platform(pos, size[0])
                    elif self.type_index == 2:
                        self.level.add_object(Barrier(pos, size[0], size[1]))
                self.wall_start = None
        elif button == mouse.RIGHT:
            for w in self.level.walls:
                if w.collider.point_inside(mouse_pos):
                    w.delete()
                    self.level.walls.remove(w)

            for p in self.level.player_spawns:
                if p.collider.point_inside(mouse_pos):
                    p.delete()
                    self.level.player_spawns.remove(p)

            for k in list(self.level.objects.keys()):
                if self.level.objects[k].collider.point_inside(mouse_pos):
                    self.level.objects[k].delete()
                    del self.level.objects[k]

            for g in self.level.goals:
                if g.collider.point_inside(mouse_pos):
                    g.delete()
                    self.level.goals.remove(g)

            if self.level.scoreboard and self.level.scoreboard.collider.point_inside(mouse_pos):
                self.level.scoreboard.delete()
                self.level.scoreboard = None

    def on_mouse_drag(self, x, y, dx, dy, button, modifiers):
        self.mouse_position[:] = self.camera.screen_to_world([x, y])

        if button == mouse.MIDDLE:
            self.camera.position[0] -= dx / self.camera.zoom
            self.camera.position[1] -= dy / self.camera.zoom
        elif button == mouse.LEFT:
            if self.grabbed_object is not None:
                w = self.grabbed_object.collider.half_width
                h = self.grabbed_object.collider.half_height
                pos = np.floor(self.mouse_position + self.grab_offset - np.floor(w) - np.floor(h))
                self.grabbed_object.set_position(pos + w + h)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        if self.type_select:
            self.type_index = (self.type_index - int(scroll_y)) % len(self.object_types)
        else:
            self.camera.set_zoom(self.camera.zoom * 1.5**scroll_y)

    def on_draw(self):
        self.clear()
        self.draw_grid(1.0)
        self.level.draw(self.batch, self.camera, self.image_handler)

        for g in self.level.goals:
            g.draw(self.batch, self.camera, self.image_handler)
            g.sprite.color = (0, 0, 255) if g.team == 'blue' else (255, 0, 0)

        for p in self.level.player_spawns:
            p.draw(self.batch, self.camera, self.image_handler)
            p.sprite.color = (0, 0, 255) if p.team == 'blue' else (255, 0, 0)

        self.draw_selection()

        self.type_text.string = str(self.object_types[self.type_index]).split('.')[1].replace("'>", "")
        self.type_text.size = 20 / self.camera.zoom
        pos = self.camera.position + 3 * self.type_text.size - self.camera.half_width - self.camera.half_height
        self.type_text.set_position(pos)
        self.type_text.draw(self.batch, self.camera, self.image_handler)

        if self.option_handler.debug_draw:
            self.level.debug_draw(self.batch, self.camera, self.image_handler)

        self.batch.draw()

    def draw_grid(self, size):
        x_min = math.floor(self.camera.position[0] - self.camera.half_width[0])
        x_max = math.ceil(self.camera.position[0] + self.camera.half_width[0])
        y_min = math.floor(self.camera.position[1] - self.camera.half_height[1])
        y_max = math.ceil(self.camera.position[1] + self.camera.half_height[1])

        for x in np.linspace(x_min, x_max, int(abs(x_max - x_min) / size) + 1):
            if x % 5 == 0:
                width = 0.1
            else:
                width = 0.05
            self.camera.draw_line([np.array([x, y_min]), np.array([x, y_max])], width, self.grid_color)

        for y in np.linspace(y_min, y_max, int(abs(y_max - y_min) / size) + 1):
            if y % 5 == 0:
                width = 0.1
            else:
                width = 0.05
            self.camera.draw_line([np.array([x_min, y]), np.array([x_max, y])], width, self.grid_color)

    def draw_selection(self):
        if self.wall_start is not None:
            end = np.round(self.mouse_position)
            size = end - self.wall_start
            pos = (self.wall_start + end) / 2
            self.camera.draw_rectangle(pos, size[0], size[1], linewidth=0.1)


if __name__ == "__main__":
    window = Editor()
    pyglet.app.run()
