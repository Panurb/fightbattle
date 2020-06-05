from itertools import chain

import numpy as np
import pyglet

from helpers import basis, norm2, rotate
from weapon import Grenade


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
        self.velocity = np.zeros(2)
        self.layers = [pyglet.graphics.OrderedGroup(i) for i in range(8)]

    def set_resolution(self, resolution):
        self.max_zoom = resolution[1] / 720 * 50.0
        self.zoom = self.max_zoom
        self.half_width = 0.5 * resolution[0] / self.zoom * basis(0)
        self.half_height = 0.5 * resolution[1] / self.zoom * basis(1)
        self.resolution[:] = resolution

    def update(self, time_step, players, level):
        cam_goal = sum(p.position for p in players.values()) / len(players)

        if level.width < 2 * self.half_width[0]:
            cam_goal[0] = 0.5 * level.width

        if level.height < 2 * self.half_height[1]:
            cam_goal[1] = 0.5 * level.height

        cam_goal[0] = max(cam_goal[0], self.half_width[0] / self.zoom)
        cam_goal[0] = min(cam_goal[0], level.width - self.half_width[0] / self.zoom)

        #if level.height > 2 * self.half_height[1] / self.zoom:
        #    cam_goal[1] = max(cam_goal[1], self.half_height[1] / self.zoom)
        #    cam_goal[1] = min(cam_goal[1], level.height - self.half_height[1] / self.zoom)
        #else:
        #    cam_goal[1] = level.position[1]

        self.position[:] += time_step * (cam_goal - self.position)

        if len(players) > 1:
            dist2 = max(norm2(p.position - cam_goal) for p in players.values())
            zoom_goal = min(500 / (np.sqrt(dist2) + 1e-6), self.max_zoom)
            self.zoom += time_step * (zoom_goal - self.zoom)

        self.shake = sum(p.camera_shake for p in players.values())

        self.shake += sum(o.camera_shake for o in level.objects.values() if type(o) is Grenade)

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

    def draw_image(self, image_handler, image_path, position, size=1, direction=1, angle=0.0,
                   batch=None, layer=1, sprite=None):
        if sprite is None:
            sprite = pyglet.sprite.Sprite(img=image_handler.images[image_path], batch=batch, group=self.layers[layer])

        if direction == -1:
            sprite.image = image_handler.images[f'{image_path}_flipped']
        else:
            sprite.image = image_handler.images[image_path]

        sprite.update(*self.world_to_screen(position), -np.rad2deg(angle), 1.05 * self.zoom * size / 100)
        sprite.group = self.layers[layer]

        return sprite

    def draw_text(self, string, position, size, font=None, color=(255, 255, 255), chromatic_aberration=0.0,
                  batch=None, layer=6, labels=None):
        if not labels[0]:
            if font is not None:
                pyglet.font.add_file(f'data/fonts/{font}')
                font = font.split('.')[0]

            labels[0] = pyglet.text.Label(string, font_name=font, font_size=size*self.zoom,
                                          anchor_x='center', anchor_y='center', color=color + (255,),
                                          batch=batch, group=self.layers[layer])

        labels[0].text = string
        labels[0].color = color + (255,)
        x, y = self.world_to_screen(position)
        labels[0].x = x
        labels[0].y = y
        labels[0].font_size = size * self.zoom

        if chromatic_aberration:
            if not labels[1]:
                if font is not None:
                    pyglet.font.add_file(f'data/fonts/{font}')
                    font = font.split('.')[0]

                labels[1] = pyglet.text.Label(string, font_name=font, font_size=size*self.zoom,
                                              anchor_x='center', anchor_y='center', color=(255, 0, 0, 255),
                                              batch=batch, group=self.layers[layer - 2])

                labels[2] = pyglet.text.Label(string, font_name=font, font_size=size*self.zoom,
                                              anchor_x='center', anchor_y='center', color=(0, 255, 255, 255),
                                              batch=batch, group=self.layers[layer - 1])

            labels[1].text = string
            labels[1].x = x - chromatic_aberration
            labels[1].y = y
            labels[1].font_size = size * self.zoom

            labels[2].text = string
            labels[2].x = x + chromatic_aberration
            labels[2].y = y
            labels[2].font_size = size * self.zoom
        else:
            if labels[1]:
                labels[1].font_size = 0
            if labels[2]:
                labels[2].font_size = 0

        return labels

    def draw_triangle(self, position, size, angle=0, color=(255, 255, 255), chromatic_aberration=False, batch=None,
                      vertex_lists=None):
        a = size * rotate(np.array([0, 0.5]), angle)
        b = size * rotate(np.array([0, -0.5]), angle)
        c = size * rotate(np.array([np.sqrt(3) / 2, 0]), angle)

        if chromatic_aberration:
            offset = 0.05 * size * basis(0)

            points = [-self.zoom / 100 * p + position - offset for p in [a, b, c]]
            vertex_lists[1] = self.draw_polygon(points, color=(255, 0, 0), batch=batch, vertex_list=vertex_lists[1])

            points = [-self.zoom / 100 * p + position + offset for p in [a, b, c]]
            vertex_lists[2] = self.draw_polygon(points, color=(0, 255, 255), batch=batch, vertex_list=vertex_lists[2])

        points = [-self.zoom / 100 * p + position for p in [a, b, c]]
        vertex_lists[0] = self.draw_polygon(points, color=color, batch=batch, vertex_list=vertex_lists[0])
        return vertex_lists

    def draw_rectangle(self, position, width, height, color=(255, 255, 255), batch=None, layer=1, vertex_list=None,
                       linewidth=0):
        w = 0.5 * width * basis(0)
        h = 0.5 * height * basis(1)
        vertices = [position + w + h, position - w + h, position - w - h, position + w - h]
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
        pyglet.gl.glLineWidth(linewidth * self.zoom)

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
