import numpy as np
import pygame
import pyglet

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

pygame.init()

option_handler = OptionHandler()
image_handler = ImageHandler()
input_handler = InputHandler()
sound_handler = SoundHandler()
loop = GameLoop(option_handler)

width, height = option_handler.resolution
window = pyglet.window.Window(width, height, vsync=False, fullscreen=option_handler.fullscreen)
pyglet.gl.glClearColor(0.2, 0.2, 0.2, 1)

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
    loop.play_sounds(sound_handler)


pyglet.clock.schedule_interval(update, 1.0 / option_handler.fps)
pyglet.app.run()
