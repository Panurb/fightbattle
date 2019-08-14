import numpy as np
import pygame

import gameloop
import imagehandler
import inputhandler
import soundhandler
import optionhandler


class Main:
    def __init__(self):
        # init mixer first to prevent audio delay
        pygame.mixer.pre_init(44100, -16, 2, 2048)
        pygame.mixer.init()

        pygame.init()
        pygame.display.set_caption('NEXTGAME')

        self.image_handler = imagehandler.ImageHandler()
        self.sound_handler = soundhandler.SoundHandler()
        self.input_handler = inputhandler.InputHandler()
        self.option_handler = optionhandler.OptionsHandler()

        self.screen = pygame.display.set_mode(self.option_handler.resolution)

        self.loop = gameloop.GameLoop()

        self.clock = pygame.time.Clock()

        self.time_step = 15.0 / self.option_handler.fps

    def main_loop(self):
        while self.loop.state != gameloop.State.QUIT:
            self.loop.update(self.input_handler, self.time_step)
            self.loop.draw(self.screen)

            pygame.display.update()
            self.clock.tick(self.option_handler.fps)


if __name__ == '__main__':
    main_window = Main()
    main_window.main_loop()
