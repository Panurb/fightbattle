import numpy as np

from collider import Circle, Group
from gameobject import GameObject, PhysicsObject


class Icon:
    def __init__(self, image_path, position, layer):
        self.position = np.array(position, dtype=float)
        self.sprite = None
        self.image_path = image_path
        self.size = 1.0
        self.visible = True
        self.layer = layer

    def delete(self):
        if self.sprite:
            self.sprite.delete()
        self.sprite = None

    def draw(self, batch, camera, image_handler):
        self.sprite = camera.draw_sprite(image_handler, self.image_path, self.position, scale=self.size,
                                         batch=batch, layer=self.layer, sprite=self.sprite)
        self.sprite.visible = self.visible


class Text:
    def __init__(self, string, position, size, font=None, color=(255, 255, 255), layer=15):
        self.string = string
        self.position = np.array(position, dtype=float)
        self.size = size
        self.font = font
        self.color = color
        self.label = None
        self.layer = layer
        self.visible = True
        self.icons = []

        self.parse_icons()

    def set_string(self, string):
        for icon in self.icons:
            icon.delete()
        self.icons.clear()
        self.string = string
        self.parse_icons()

    def parse_icons(self):
        for i in range(len(self.string)):
            for char in ['A', 'B', 'X', 'Y', 'RT', 'LT', 'R', 'L', 'START']:
                if self.string[i:i+len(char)+2] == f'({char})':
                    pos = self.position + 0.2 * np.array([-0.5 * len(self.string) + 1.75 * i, -0.5])
                    self.icons.append(Icon(char.lower(), pos, self.layer))
                    self.string = self.string.replace(f'({char})', '     ')

    def set_position(self, position):
        delta_pos = position - self.position
        self.position += delta_pos
        for i in self.icons:
            i.position += self.position

    def set_visible(self, visible):
        self.visible = visible
        if self.label:
            self.label.font_size = visible * self.size

    def delete(self):
        if self.label:
            self.label.delete()
        for icon in self.icons:
            icon.delete()

    def draw(self, batch, camera, image_handler):
        string = self.string if self.visible else ''
        self.label = camera.draw_label(string, self.position, self.visible * self.size, self.font, self.color,
                                       batch=batch, layer=self.layer, label=self.label)
        for icon in self.icons:
            icon.visible = self.visible
            icon.draw(batch, camera, image_handler)


class TitleText(Text):
    def __init__(self, string, position, size, font=None, color=(255, 255, 255)):
        super().__init__(string, position, size, font, color)
        self.chromatic_aberration = 0.0
        self.label_red = None
        self.label_cyan = None

    def set_visible(self, visible):
        super().set_visible(visible)
        if self.label_red:
            self.label_red.font_size = visible * self.size
        if self.label_cyan:
            self.label_cyan.font_size = visible * self.size

    def delete(self):
        super().delete()
        if self.label_red:
            self.label_red.delete()
        if self.label_cyan:
            self.label_cyan.delete()

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        string = self.string if self.visible else ''

        r = 0.05 * self.chromatic_aberration * self.size * np.array([1, -1])
        self.label_red = camera.draw_label(string, self.position - r, self.size, self.font, (255, 0, 0),
                                           batch=batch, layer=self.layer-1, label=self.label_red)
        self.label_cyan = camera.draw_label(string, self.position + r, self.size, self.font, (0, 255, 255),
                                            batch=batch, layer=self.layer-2, label=self.label_cyan)


class Tutorial(PhysicsObject):
    def __init__(self, position):
        super().__init__(position, image_path='tutorial', gravity_scale=0.0)
        self.layer = 1
        self.add_collider(Circle(np.zeros(2), 3.0))
        self.index = 0
        self.strings = ['(L) move', '(A) jump', '(X) run', '(R)   move hand', '(RT) grab', '(LT) drop',
                        '(RT) attack', '(LT) (hold) throw']
        self.text = Text(self.strings[self.index], position + np.array([0, 1]), 0.0, layer=2)
        self.visible = True

    def update(self, gravity, time_step, colliders):
        self.collider.update_collisions(colliders, {Group.PLAYERS})
        if self.collider.collisions:
            self.visible = True
        else:
            self.visible = False

        if self.visible:
            if self.text.size < 0.45:
                self.text.size += 10.0 * time_step * (0.5 - self.text.size)
            else:
                self.text.size = 0.5
        else:
            if self.text.size > 0.1:
                self.text.size += 10.0 * time_step * (0.0 - self.text.size)
            else:
                self.text.size = 0.0

        for icon in self.text.icons:
            icon.size = 1.8 * self.text.size

    def delete(self):
        super().delete()
        self.text.delete()

    def get_data(self):
        return super().get_data() + (self.index,)

    def apply_data(self, data):
        super().apply_data(data)
        self.index = data[-1]
        self.text.set_string(self.strings[self.index])

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        self.text.draw(batch, camera, image_handler)

    def draw_shadow(self, batch, camera, image_handler, light):
        pass
