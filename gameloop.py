import pickle

import enum

import pygame


class State(enum.Enum):
    QUIT = 1
    PLAY = 2


class GameLoop:
    def __init__(self, option_handler):
        self.state = State.PLAY

        #self.level = level.Level(option_handler)

        with open('lvl.pickle', 'rb') as f:
            self.level = pickle.load(f)

    def reset_level(self):
        with open('lvl.pickle', 'rb') as f:
            self.level = pickle.load(f)

    def update(self, input_handler, time_step):
        if self.state is State.PLAY:
            if input_handler.keys_pressed[pygame.K_r]:
                self.reset_level()

            if len(self.level.players) > 1:
                count = 0
                for p in self.level.players:
                    if p.destroyed:
                        count += 1

                if count >= len(self.level.players) - 1:
                    self.reset_level()

            input_handler.update(self.level)

            self.level.input(input_handler)

            self.level.update(time_step)

        if input_handler.quit:
            self.state = State.QUIT

    def draw(self, screen, image_handler):
        screen.fill((150, 150, 150))

        self.level.draw(screen, image_handler)
