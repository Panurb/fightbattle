import numpy as np
import pygame
import pyglet

from gameloop import GameLoop
from imagehandler import ImageHandler
from inputhandler import InputHandler
from menu import State
from optionhandler import OptionHandler
from soundhandler import SoundHandler


'''
class Main:
    def __init__(self):
        # init mixer first to prevent audio delay
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()

        pygame.mixer.set_num_channels(16)

        pygame.init()
        pygame.display.set_caption('FIGHTBATTLE')

        self.option_handler = optionhandler.OptionHandler()

        if self.option_handler.fullscreen:
            self.screen = pygame.display.set_mode(self.option_handler.resolution,
                                                  flags=(pygame.FULLSCREEN | pygame.HWSURFACE))
        else:
            self.screen = pygame.display.set_mode(self.option_handler.resolution)

        self.image_handler = imagehandler.ImageHandler()
        self.sound_handler = soundhandler.SoundHandler()
        self.input_handler = inputhandler.InputHandler()

        self.loop = gameloop.GameLoop(self.option_handler)

        self.clock = pygame.time.Clock()

        self.time_step = 15.0 / self.option_handler.fps

        self.font = pygame.font.Font(None, 30)

        self.sound_handler.set_volume(self.option_handler.sfx_volume)
        self.sound_handler.set_music_volume(self.option_handler.music_volume)
        self.sound_handler.set_music('line')

    def main_loop(self):
        while self.loop.state != menu.State.QUIT:
            fps = self.clock.get_fps()

            if self.option_handler.fps == 999:
                if fps != 0:
                    self.time_step = min(15.0 / fps, 15.0 / 60.0)

            self.loop.input(self.input_handler)
            self.loop.update(self.time_step)
            self.loop.draw(self.screen, self.image_handler)
            self.loop.play_sounds(self.sound_handler)

            fps_str = self.font.render(str(int(fps)), True, self.image_handler.debug_color)
            self.screen.blit(fps_str, (50, 50))

            pygame.display.update()
            self.clock.tick(self.option_handler.fps)


def main():
    main_window = Main()
    main_window.main_loop()


#if __name__ == "__main__":
#    main()
'''

pygame.init()

option_handler = OptionHandler()
image_handler = ImageHandler()
input_handler = InputHandler()
loop = GameLoop(option_handler)

width, height = option_handler.resolution
window = pyglet.window.Window(width, height, vsync=False)

fps_display = pyglet.window.FPSDisplay(window=window)

batch = pyglet.graphics.Batch()
background = pyglet.graphics.OrderedGroup(0)
foreground = pyglet.graphics.OrderedGroup(1)
particles = pyglet.graphics.OrderedGroup(2)


@window.event
def on_key_press(symbol, modifiers):
    input_handler.keys_pressed[symbol] = True
    input_handler.keys_down[symbol] = True


@window.event
def on_key_release(symbol, modifiers):
    input_handler.keys_released[symbol] = True
    input_handler.keys_down[symbol] = False


@window.event
def on_mouse_motion(x, y, dx, dy):
    input_handler.mouse_position[:] = loop.camera.screen_to_world([x, y])
    input_handler.mouse_change[0] = dx / loop.camera.zoom
    input_handler.mouse_change[1] = dy / loop.camera.zoom


@window.event
def on_draw():
    window.clear()
    loop.draw(batch, image_handler)
    batch.draw()
    fps_display.draw()


def update(dt):
    loop.input(input_handler)
    loop.update(15.0 * dt)


pyglet.clock.schedule_interval(update, 1.0 / option_handler.fps)
pyglet.app.run()
