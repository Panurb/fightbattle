from itertools import chain

import numpy as np
import pyglet
from PIL import Image
from pyglet.gl import *

from helpers import basis, rotate, norm2


UNIT_CIRCLE = [np.zeros(2)] + [np.array([np.cos(theta), np.sin(theta)]) for theta in np.linspace(0, 2 * np.pi, 20)]


class Camera:
    def __init__(self, position, resolution):
        self.position = np.array(position, dtype=float)
        self.max_zoom = resolution[1] / 720 * 50.0
        self.zoom = self.max_zoom
        self.half_width = 0.5 * resolution[0] / self.zoom * basis(0)
        self.half_height = 0.5 * resolution[1] / self.zoom * basis(1)
        self.resolution = np.array(resolution, dtype=int)
        self.shake = np.zeros(2)
        self.shake_velocity = np.zeros(2)
        self.velocity = np.zeros(2)
        self.layers = [pyglet.graphics.OrderedGroup(i) for i in range(9)]

        self.sprite = None
        self.target_position = self.position.copy()
        self.target_zoom = self.max_zoom
        self.speed = 10

    def draw(self, batch):
        if not self.sprite:
            image = Image.new('RGBA', [1, 1], (0, 0, 0))
            image = pyglet.image.ImageData(1, 1, 'RGBA', image.tobytes())
            self.sprite = pyglet.sprite.Sprite(img=image, x=0, y=0, batch=batch, group=self.layers[7])
        self.sprite.update(scale_x=self.resolution[0], scale_y=self.resolution[1])

    def set_resolution(self, resolution):
        self.max_zoom = resolution[1] / 720 * 50.0
        self.zoom = self.max_zoom
        self.target_zoom = self.zoom
        self.half_width = 0.5 * resolution[0] / self.zoom * basis(0)
        self.half_height = 0.5 * resolution[1] / self.zoom * basis(1)
        self.resolution[:] = resolution

    def set_position_zoom(self, position, zoom):
        self.position[:] = position
        self.target_position[:] = position
        self.zoom = min(zoom, self.max_zoom)
        self.target_zoom = self.zoom

    def set_target(self, players, level):
        self.target_position = sum(p.position for p in players.values()) / len(players)

        if level.width < 2 * self.half_width[0]:
            self.target_position[0] = 0.5 * level.width

        if level.height < 2 * self.half_height[1]:
            self.target_position[1] = 0.5 * level.height

        self.target_position[0] = max(self.target_position[0], self.half_width[0])
        self.target_position[0] = min(self.target_position[0], level.width - self.half_width[0])

        self.target_position[1] = max(self.target_position[1], self.half_height[1])
        self.target_position[1] = min(self.target_position[1], level.height - self.half_height[1])

        if len(players) > 1:
            eps = 1e-6
            x = max(abs(p.position[0] - self.target_position[0]) for p in players.values()) + eps
            y = max(abs(p.position[1] - self.target_position[1]) for p in players.values()) + eps
            self.target_zoom = min(0.4 * self.resolution[0] / x, 0.4 * self.resolution[1] / y)
            self.target_zoom = min(self.target_zoom, self.max_zoom)
        else:
            self.target_zoom = self.max_zoom

        for p in players.values():
            if p.camera_shake is not None:
                self.shake += p.camera_shake
                p.camera_shake = None

        for o in level.objects.values():
            if o.camera_shake is not None:
                self.shake += o.camera_shake
                o.camera_shake = None

    def update(self, time_step):
        delta_pos = self.target_position - self.position
        if norm2(delta_pos) > 0.001:
            self.position[:] += self.speed * time_step * delta_pos
        else:
            self.position[:] = self.target_position

        delta_zoom = self.target_zoom - self.zoom
        if abs(delta_zoom) > 0.01:
            self.zoom += self.speed * time_step * delta_zoom
        else:
            self.zoom = self.target_zoom

        if norm2(self.shake) < 0.01:
            self.shake = np.zeros(2)
        else:
            # Damped harmonic oscillator
            self.shake_velocity -= 5 * self.shake + 0.1 * self.shake_velocity
            self.shake += self.shake_velocity * time_step

    def set_zoom(self, zoom):
        self.zoom = zoom
        self.half_width = 0.5 * self.resolution[0] / self.zoom * basis(0)
        self.half_height = 0.5 * self.resolution[1] / self.zoom * basis(1)

    def world_to_screen(self, position):
        pos = (position - self.position) * self.zoom + 0.5 * self.resolution + self.shake

        return [int(pos[0]), int(pos[1])]

    def screen_to_world(self, position):
        pos = np.array([position[0], position[1]], dtype=float)
        pos = (pos - 0.5 * self.resolution - self.shake) / self.zoom + self.position

        return pos

    def draw_sprite(self, image_handler, image_path, position, scale=1, direction=1, angle=0.0, scale_x=None,
                    scale_y=None, batch=None, layer=1, sprite=None):
        if sprite is None:
            sprite = pyglet.sprite.Sprite(img=image_handler.images[image_path], batch=batch, group=self.layers[layer])

        if direction == -1:
            sprite.image = image_handler.images[f'{image_path}_flipped']
        else:
            sprite.image = image_handler.images[image_path]

        scale = 1.05 * self.zoom * scale / 100 if scale else None
        scale_x = 1.05 * self.zoom * scale_x / 100 if scale_x else None
        scale_y = 1.05 * self.zoom * scale_y / 100 if scale_y else None
        sprite.update(*self.world_to_screen(position), -np.rad2deg(angle), scale, scale_x, scale_y)
        sprite.group = self.layers[layer]

        return sprite

    def draw_label(self, string, position, size, font=None, color=(255, 255, 255), batch=None, layer=6, label=None):
        if not label:
            if font is not None:
                pyglet.font.add_file(f'data/fonts/{font}')
                font = font.split('.')[0]

            label = pyglet.text.Label(string, font_name=font, font_size=size*self.zoom,
                                      anchor_x='center', anchor_y='center', color=color + (255,),
                                      batch=batch, group=self.layers[layer])

        label.text = string
        label.color = color + (255,)
        x, y = self.world_to_screen(position)
        label.x = x
        label.y = y
        if size * self.zoom != label.font_size:
            label.font_size = size * self.zoom

        return label

    def draw_triangle(self, position, size, angle=0, color=(255, 255, 255), batch=None, vertex_list=None):
        a = size * rotate(np.array([0, 0.5]), angle)
        b = size * rotate(np.array([0, -0.5]), angle)
        c = size * rotate(np.array([np.sqrt(3) / 2, 0]), angle)

        points = [-self.zoom / 100 * p + position for p in [a, b, c]]
        vertex_list = self.draw_polygon(points, color=color, batch=batch, vertex_list=vertex_list)

        return vertex_list

    def draw_rectangle(self, position, width, height, color=(255, 255, 255), batch=None, layer=1, vertex_list=None,
                       linewidth=0):
        w = 0.5 * width * basis(0)
        h = 0.5 * height * basis(1)
        vertices = [position + w + h, position - w + h, position - w - h, position + w - h, position + w + h]
        return self.draw_polygon(vertices, color, batch, layer, vertex_list, linewidth)

    def draw_polygon(self, points, color=(255, 255, 255), batch=None, layer=1, vertex_list=None, linewidth=0):
        if linewidth != 0:
            return self.draw_line(points + [points[0]], linewidth, color, batch, layer, vertex_list)

        vertices = [self.world_to_screen(p)[i] for p in points for i in range(2)]
        colors = [int(c) for c in color] * len(points)

        if batch is None:
            pyglet.graphics.draw(len(points), pyglet.gl.GL_TRIANGLES, ('v2i', vertices), ('c3B', colors))
            return

        # no idea what this does
        # https://codereview.stackexchange.com/questions/90921/drawing-circles-with-triangles
        index = list(chain.from_iterable((0, x - 1, x) for x in range(2, len(points))))

        if vertex_list is None:
            return batch.add_indexed(len(points), pyglet.gl.GL_TRIANGLES, self.layers[layer],
                                     index, ('v2i', vertices), ('c3B', colors))
        else:
            vertex_list.vertices = vertices
            vertex_list.colors = colors
            return vertex_list

    def draw_circle(self, position, radius, color=(255, 255, 255), batch=None, layer=1, vertex_list=None, linewidth=0):
        points = [radius * x + position for x in UNIT_CIRCLE]
        return self.draw_polygon(points, color, batch=batch, layer=layer, vertex_list=vertex_list, linewidth=linewidth)

    def draw_ellipse(self, position, width, height, angle=0.0, color=(255, 255, 255), batch=None, layer=1, vertex_list=None):
        if width == height:
            return self.draw_circle(position, width, color, batch, layer, vertex_list)

        points = [position]
        points += [rotate(np.array([width * np.cos(theta), height * np.sin(theta)]), angle) + position
                   for theta in np.linspace(0, 2 * np.pi, 8)]
        return self.draw_polygon(points, color, batch=batch, layer=layer, vertex_list=vertex_list)
        
    def draw_line(self, points, linewidth=1, color=(255, 255, 255), batch=None, layer=1, vertex_list=None):
        pyglet.gl.glLineWidth(1)

        points = [points[0]] + [p for p in points[1:-1] for _ in range(2)] + [points[-1]]
        vertices = [self.world_to_screen(p)[i] for p in points for i in range(2)]
        n = int(len(vertices) / 2)
        colors = [int(c) for c in color] * n
        
        if batch is None:
            pyglet.graphics.draw(n, pyglet.gl.GL_LINES, ('v2i', vertices), ('c3B', colors))
            return

        if vertex_list is None:
            return batch.add(n, pyglet.gl.GL_LINES, self.layers[layer], ('v2i', vertices), ('c3B', colors))
        else:
            vertex_list.vertices = vertices
            vertex_list.colors = colors
            return vertex_list
