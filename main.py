import cProfile
import io
import pstats
from pstats import SortKey

import pygame

import gameloop
import imagehandler
import inputhandler
import menu
import optionhandler
import soundhandler


class Main:
    def __init__(self):
        # init mixer first to prevent audio delay
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()

        #pygame.mixer.set_num_channels(16)

        pygame.init()
        pygame.display.set_caption('NEXTGAME')

        self.option_handler = optionhandler.OptionsHandler()

        mode = pygame.FULLSCREEN if self.option_handler.fullscreen else 0

        self.screen = pygame.display.set_mode(self.option_handler.resolution, mode)

        self.image_handler = imagehandler.ImageHandler()
        self.sound_handler = soundhandler.SoundHandler()
        self.input_handler = inputhandler.InputHandler()

        self.loop = gameloop.GameLoop(self.option_handler)

        self.clock = pygame.time.Clock()

        self.time_step = 15.0 / self.option_handler.fps

        self.font = pygame.font.Font(None, 30)

    def main_loop(self):
        while self.loop.state != menu.State.QUIT:
            fps = self.clock.get_fps()

            if self.option_handler.fps == 999:
                if fps != 0:
                    self.time_step = 15.0 / fps

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


def profile():
    pr = cProfile.Profile()
    pr.enable()
    main()
    pr.disable()
    s = io.StringIO()
    sortby = SortKey.CUMULATIVE
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    print(s.getvalue())


if __name__ == "__main__":
    main()
