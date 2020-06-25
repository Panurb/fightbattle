import math
import pickle

import numpy as np
import pyglet
from numpy.linalg import norm
from pyglet.window import key
from pyglet.window import mouse

from imagehandler import ImageHandler
from optionhandler import OptionHandler
from camera import Camera
from level import Level, PlayerSpawn
from prop import Crate, Ball
from wall import Basket, Scoreboard
from weapon import Weapon, Revolver, Shotgun


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

        self.wall_start = None
        self.grabbed_object = None
        self.grab_offset = np.zeros(2)
        self.grab_start = np.zeros(2)
        self.object_types = ['wall', 'platform']
        self.type_index = 0

        self.camera = Camera([0, 0], self.option_handler.resolution)

        self.mouse_position = np.zeros(2)

    def on_key_press(self, symbol, modifiers):
        if symbol == key.S:
            for i, o in enumerate(self.level.objects.values()):
                o.id = i

            with open('data/levels/lvl.pickle', 'wb') as f:
                pickle.dump(self.level.get_data(), f)
        elif symbol == key.L:
            self.batch = pyglet.graphics.Batch()
            with open('data/levels/lvl.pickle', 'rb') as f:
                data = pickle.load(f)
                self.level.clear()
                self.level.apply_data(data)
        elif symbol == key.DELETE:
            self.level.clear()
        elif symbol == key.W:
            if self.type_index == len(self.object_types) - 1:
                self.type_index = 0
            else:
                self.type_index += 1

        pos = np.floor(self.mouse_position) + np.array([0.5, 0.501])

        if symbol == key.P:
            self.level.player_spawns.append(PlayerSpawn(pos))
        elif symbol == key.C:
            self.level.add_object(Crate(pos))
        elif symbol == key.B:
            self.level.add_object(Ball(pos))
        elif symbol == key.G:
            self.level.add_object(Shotgun(pos))
        elif symbol == key.T:
            self.level.goals.append(Basket(pos))
        elif symbol == key.I:
            self.level.scoreboard = Scoreboard(pos)

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
                self.wall_start = np.round(self.mouse_position)

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
                    else:
                        self.level.add_platform(pos, size[0])
                self.wall_start = None
        elif button == mouse.RIGHT:
            for w in self.level.walls:
                if w.collider.point_inside(mouse_pos):
                    w.sprite.delete()
                    if w.collider.vertex_list:
                        w.collider.vertex_list.delete()
                    self.level.walls.remove(w)

            for p in self.level.player_spawns:
                if p.collider.point_inside(mouse_pos):
                    if p.collider.vertex_list:
                        p.collider.vertex_list.delete()
                    p.vertex_list.delete()
                    self.level.player_spawns.remove(p)

            for k in list(self.level.objects.keys()):
                if self.level.objects[k].collider.point_inside(mouse_pos):
                    self.level.objects[k].sprite.delete()
                    if self.level.objects[k].collider.vertex_list:
                        self.level.objects[k].collider.vertex_list.delete()
                    del self.level.objects[k]

            for g in self.level.goals:
                if g.collider.point_inside(mouse_pos):
                    g.sprite.delete()
                    g.front.sprite.delete()
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
        self.camera.set_zoom(self.camera.zoom * 1.5**scroll_y)

    def on_draw(self):
        self.clear()
        self.draw_grid(1.0)
        self.level.draw(self.batch, self.camera, self.image_handler)
        for g in self.level.goals:
            g.sprite.color = (0, 0, 255) if g.team == 'blue' else (255, 0, 0)
        if self.option_handler.debug_draw:
            self.level.debug_draw(self.batch, self.camera, self.image_handler)

        for p in self.level.player_spawns:
            p.draw(self.batch, self.camera, self.image_handler)

        self.draw_selection()

        pos = self.camera.half_width + self.camera.half_height - 50 * np.ones(2)
        pos = self.camera.position - pos / self.camera.zoom
        #self.camera.draw_text(self.object_types[self.type_index], pos, 32 / self.camera.zoom)

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
