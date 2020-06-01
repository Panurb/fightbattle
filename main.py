import pygame
import pyglet
from pyglet.window import key

from gameloop import GameLoop
from imagehandler import ImageHandler
from inputhandler import InputHandler
from optionhandler import OptionHandler
from soundhandler import SoundHandler


# transparency stuff
pyglet.gl.glEnable(pyglet.gl.GL_DEPTH_TEST)
pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)

pygame.init()


class GameWindow(pyglet.window.Window):
    def __init__(self):
        self.option_handler = OptionHandler()
        self.image_handler = ImageHandler()
        self.input_handler = InputHandler()
        self.sound_handler = SoundHandler()
        self.loop = GameLoop(self.option_handler)

        width, height = self.option_handler.resolution
        super().__init__(width, height, vsync=self.option_handler.vsync,
                         fullscreen=self.option_handler.fullscreen)

        # background color
        pyglet.gl.glClearColor(0.2, 0.2, 0.2, 1)

        self.fps_display = pyglet.window.FPSDisplay(window=self)

        self.batch = pyglet.graphics.Batch()

        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)

    def on_key_press(self, symbol, modifiers):
        self.input_handler.keys_pressed[symbol] = True

    def on_key_release(self, symbol, modifiers):
        self.input_handler.keys_released[symbol] = True
        self.input_handler.keys_down[symbol] = False

    def on_mouse_motion(self, x, y, dx, dy):
        self.input_handler.mouse_position[:] = self.loop.camera.screen_to_world([x, y])
        self.input_handler.mouse_change[0] = dx / self.loop.camera.zoom
        self.input_handler.mouse_change[1] = dy / self.loop.camera.zoom

    def on_mouse_press(self, x, y, button, modifiers):
        self.input_handler.mouse_pressed[button] = True

    def on_mouse_release(self, x, y, button, modifiers):
        self.input_handler.mouse_released[button] = True
        self.input_handler.mouse_down[button] = False

    def on_draw(self):
        self.clear()
        self.loop.draw(self.batch, self.image_handler)
        self.batch.draw()
        self.fps_display.draw()

    def update(self, dt):
        self.loop.input(self.input_handler)
        self.loop.update(min(15.0 * dt, 0.5))
        self.loop.play_sounds(self.sound_handler)


window = GameWindow()
pyglet.clock.schedule_interval(window.update, 1.0 / window.option_handler.fps)
pyglet.app.run()
