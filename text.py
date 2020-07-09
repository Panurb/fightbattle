import numpy as np


class Icon:
    def __init__(self, image_path, position):
        self.position = np.array(position, dtype=float)
        self.sprite = None
        self.image_path = image_path
        self.size = 1.0

    def draw(self, batch, camera, image_handler):
        self.sprite = camera.draw_sprite(image_handler, self.image_path, self.position, scale=self.size,
                                         batch=batch, layer=9, sprite=self.sprite)


class Text:
    def __init__(self, string, position, size, font=None, color=(255, 255, 255), layer=8):
        self.string = string
        self.position = np.array(position, dtype=float)
        self.size = size
        self.font = font
        self.color = color
        self.label = None
        self.layer = layer
        self.visible = True
        self.icons = []

        for i in range(len(self.string)):
            for char in 'ABCD':
                if self.string[i:i+3] == f'({char})':
                    pos = self.position + 0.2 * np.array([-0.5 * len(self.string) + 1.3 * i, -0.5])
                    self.icons.append(Icon(char.lower(), pos))
                self.string = self.string.replace(f'({char})', '   ')

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

    def draw(self, batch, camera, image_handler):
        string = self.string if self.visible else ''
        self.label = camera.draw_label(string, self.position, self.visible * self.size, self.font, self.color,
                                       batch=batch, layer=self.layer, label=self.label)
        for icon in self.icons:
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
