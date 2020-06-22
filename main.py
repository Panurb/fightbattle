import pyglet
from pyglet.window import key

from gameloop import GameLoop
from imagehandler import ImageHandler
from inputhandler import InputHandler
from menu import State
from optionhandler import OptionHandler
from soundhandler import SoundHandler


# transparency stuff
pyglet.gl.glEnable(pyglet.gl.GL_DEPTH_TEST)
pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)


class GameWindow(pyglet.window.Window):
    def __init__(self):
        self.option_handler = OptionHandler()
        width, height = self.option_handler.resolution
        super().__init__(width, height, vsync=self.option_handler.vsync, fullscreen=self.option_handler.fullscreen)

        self.image_handler = ImageHandler()
        self.input_handler = InputHandler()
        self.sound_handler = SoundHandler(self.option_handler)
        self.loop = GameLoop(self.option_handler)

        self.fps_display = pyglet.window.FPSDisplay(window=self)
        self.fps_display.label.color = (255, 255, 255, 128)

        self.batch = pyglet.graphics.Batch()

        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)

    def on_draw(self):
        self.clear()
        self.loop.draw(self.batch, self.image_handler)
        self.batch.draw()
        self.fps_display.draw()

    def update(self, dt):
        self.loop.input(self.input_handler)
        self.loop.update(min(15.0 * dt, 0.5))
        self.loop.play_sounds(self.sound_handler)
        if self.loop.state is State.OPTIONS:
            if self.loop.options_menu.options_changed:
                self.set_fullscreen(self.option_handler.fullscreen, None, None,
                                    self.option_handler.resolution[0], self.option_handler.resolution[1])
                self.loop.options_menu.options_changed = False
        elif self.loop.state is State.QUIT:
            self.close()


window = GameWindow()
window.push_handlers(window.input_handler)
pyglet.clock.schedule_interval(window.update, 1.0 / window.option_handler.fps)
pyglet.app.run()
