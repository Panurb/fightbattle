import enum

import level


class State(enum.Enum):
    QUIT = 1
    PLAY = 2


class GameLoop:
    def __init__(self):
        self.state = State.PLAY

        self.level = level.Level()

    def update(self, input_handler, time_step):
        if self.state is State.PLAY:
            input_handler.update()

            self.level.input(input_handler)

            self.level.update(time_step)

        if input_handler.quit:
            self.state = State.QUIT

    def draw(self, screen):
        screen.fill((0, 0, 0))

        self.level.draw(screen)
