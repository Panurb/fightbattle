import pygame
import pyglet
from pyglet.window import key
from pyglet.gl import *

from gameloop import GameLoop
from imagehandler import ImageHandler
from inputhandler import InputHandler
from menu import State
from optionhandler import OptionHandler
from soundhandler import SoundHandler


# transparency stuff
#glEnable(GL_BLEND)
#glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
#glBlendEquation(GL_MAX_EXT)


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
        if self.option_handler.show_fps:
            self.fps_display.draw()

    def update(self, dt):
        self.set_exclusive_mouse(self.loop.state in {State.SINGLEPLAYER, State.MULTIPLAYER, State.LAN})
        self.loop.input(self.input_handler)
        self.loop.update(min(dt, 0.03))
        self.loop.play_sounds(self.sound_handler)
        if self.loop.state is State.OPTIONS:
            if self.loop.options_menu.options_changed:
                self.set_fullscreen(self.option_handler.fullscreen, None, None,
                                    self.option_handler.resolution[0], self.option_handler.resolution[1])
                self.loop.options_menu.options_changed = False
        elif self.loop.state is State.QUIT:
            self.close()


def main():
    pygame.init()
    window = GameWindow()
    window.push_handlers(window.input_handler)
    pyglet.clock.schedule_interval(window.update, 1.0 / window.option_handler.fps)
    pyglet.app.run()


if __name__ == '__main__':
    main()
