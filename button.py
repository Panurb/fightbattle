import numpy as np

from collider import Rectangle
from gameobject import GameObject
from helpers import basis
from text import Text


class Button(GameObject):
    def __init__(self, string, target_state):
        super().__init__([0, 0])
        self.add_collider(Rectangle([0, 0], 3, 1))
        self.target_state = target_state
        self.color = (150, 150, 150)
        self.color_selected = (255, 255, 255)
        self.selected = False
        self.text = Text(string, self.position, 0.45)
        self.visible = True

    def set_visible(self, visible):
        self.visible = visible
        self.text.set_visible(visible)

    def delete(self):
        self.text.delete()

    def set_position(self, position):
        super().set_position(position)
        self.text.set_position(position)

    def draw(self, batch, camera, image_handler):
        if self.visible:
            color = self.color_selected if self.selected else self.color
            self.text.color = color

        self.text.visible = self.visible
        self.text.draw(batch, camera, image_handler)
        
        
class RebindButton(Button):
    def __init__(self, string):
        super().__init__(f'{string}: Button 0', None)
        self.add_collider(Rectangle([0, 0], 3, 1))

    def set_visible(self, visible):
        self.visible = visible
        self.text.set_visible(visible)

    def delete(self):
        self.text.delete()

    def set_position(self, position):
        super().set_position(position)
        self.text.set_position(position)

    def draw(self, batch, camera, image_handler):
        if self.visible:
            color = self.color_selected if self.selected else self.color
            self.text.color = color

        self.text.visible = self.visible
        self.text.draw(batch, camera, image_handler)


class Slider(GameObject):
    def __init__(self, string, values, cyclic=True, selection=0):
        super().__init__([0, 0])
        self.add_collider(Rectangle([0, 0], 3, 1))
        self.color = (150, 150, 150)
        self.color_selected = (255, 255, 255)
        self.selected = False
        self.selection = selection
        self.values = values
        self.cyclic = cyclic
        self.text = Text(string, self.position + 0.63 * basis(1), 0.45)
        self.value_text = Text('', self.position, 0.45)
        self.triangle_left = None
        self.triangle_right = None
        self.visible = True

    def set_visible(self, visible):
        self.visible = visible
        self.text.set_visible(visible)
        self.value_text.set_visible(visible)
        self.triangle_left.visible = visible
        self.triangle_right.visible = visible

    def set_position(self, position):
        super().set_position(position)
        self.text.set_position(position + 0.63 * basis(1))
        self.value_text.set_position(position)

    def delete(self):
        self.text.delete()
        self.value_text.delete()
        if self.triangle_left:
            self.triangle_left.delete()
        if self.triangle_right:
            self.triangle_right.delete()

    def get_value(self):
        return self.values[self.selection]

    def move_right(self):
        if self.cyclic:
            self.selection = (self.selection + 1) % len(self.values)
        else:
            self.selection = min(self.selection + 1, len(self.values) - 1)

    def move_left(self):
        if self.cyclic:
            self.selection = (self.selection - 1) % len(self.values)
        else:
            self.selection = max(self.selection - 1, 0)

    def draw(self, batch, camera, image_handler):
        self.text.visible = self.visible
        self.value_text.visible = self.visible

        self.text.draw(batch, camera, image_handler)
        self.value_text.draw(batch, camera, image_handler)
        self.triangle_left = camera.draw_sprite(image_handler, 'left', self.position - 2 * basis(0), 0.7,
                                                batch=batch, sprite=self.triangle_left)
        self.triangle_right = camera.draw_sprite(image_handler, 'right', self.position + 2 * basis(0), 0.7,
                                                 batch=batch, sprite=self.triangle_right)

        if self.visible:
            color = self.color_selected if self.selected else self.color

            self.text.color = color

            self.value_text.color = color
            val_str = str(self.values[self.selection]).replace(', ', 'x').strip('()')
            self.value_text.string = val_str

        if self.triangle_left:
            if not self.visible or not self.selected or (not self.cyclic and self.selection == 0):
                self.triangle_left.visible = False
            else:
                self.triangle_left.visible = True

        if self.triangle_right:
            if not self.visible or not self.selected or (not self.cyclic and self.selection == len(self.values) - 1):
                self.triangle_right.visible = False
            else:
                self.triangle_right.visible = True

    def randomize(self):
        self.selection = np.random.randint(len(self.values))
