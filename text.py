import numpy as np

from helpers import basis


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

    def set_visible(self, visible):
        self.visible = visible
        if self.label:
            self.label.font_size = visible * self.size

    def delete(self):
        if self.label:
            self.label.delete()

    def draw(self, batch, camera):
        string = self.string if self.visible else ''
        self.label = camera.draw_label(string, self.position, self.visible * self.size, self.font, self.color,
                                       batch=batch, layer=self.layer, label=self.label)


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

    def draw(self, batch, camera):
        super().draw(batch, camera)
        string = self.string if self.visible else ''

        r = 0.05 * self.chromatic_aberration * self.size * basis(0)
        self.label_red = camera.draw_label(string, self.position - r, self.size, self.font, (255, 0, 0),
                                           batch=batch, layer=self.layer-1, label=self.label_red)
        self.label_cyan = camera.draw_label(string, self.position + r, self.size, self.font, (0, 255, 255),
                                            batch=batch, layer=self.layer-2, label=self.label_cyan)
