import enum

import level


class State(enum.Enum):
    QUIT = 1
    PLAY = 2


class GameLoop:
    def __init__(self, option_handler):
        self.state = State.PLAY

        self.level = level.Level(option_handler)

    def update(self, input_handler, time_step):
        if self.state is State.PLAY:
            input_handler.update(self.level)

            self.level.input(input_handler)

            self.level.update(time_step)

        if input_handler.quit:
            self.state = State.QUIT

    def draw(self, screen, image_handler):
        screen.fill((150, 150, 150))

        self.level.draw(screen, image_handler)
