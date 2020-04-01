import numpy as np
import pygame

import menu
import gameloop
import imagehandler
import inputhandler
import soundhandler
import optionhandler
from collider import Group
from network import Network


class Main:
    def __init__(self):
        # init mixer first to prevent audio delay
        pygame.mixer.pre_init(44100, -16, 2, 2048)
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

        self.network = Network()

        p = self.network.getP()
        self.network_id = p.network_id
        self.loop.players = dict()
        self.loop.players[self.network_id] = p

    def main_loop(self):
        while self.loop.state != menu.State.QUIT:
            fps = self.clock.get_fps()

            if self.option_handler.fps == 999:
                if fps != 0:
                    self.time_step = 15.0 / fps

            old_obj = self.loop.players[self.network_id].object

            self.loop.input(self.input_handler)

            self.loop.players[self.network_id].update(self.loop.level.gravity, self.time_step, self.loop.colliders)
            self.loop.camera.update(self.time_step, self.loop.players)

            data = [self.loop.players[self.network_id], []]
            if old_obj is not None:
                data[1].append(old_obj)
            data = self.network.send(data)

            for p in data[0]:
                self.loop.players[p.network_id] = p

            for i, obj in enumerate(self.loop.level.objects):
                if obj.id == old_obj:
                    continue

                o = data[1][i]
                obj.set_position(o.position)
                obj.angle = o.angle
                obj.sounds[:] = o.sounds
                #if o.destroyed:
                #    obj.destroy(np.zeros(2), self.loop.colliders)

            for g in Group:
                if g not in [Group.NONE, Group.PLAYERS, Group.HITBOXES, Group.WALLS, Group.PLATFORMS]:
                    self.loop.colliders[g] = []

            for obj in self.loop.level.objects:
                if obj.collider is not None:
                    self.loop.colliders[obj.collider.group].append(obj.collider)

            self.loop.draw(self.screen, self.image_handler)
            self.loop.play_sounds(self.sound_handler)

            fps_str = self.font.render(str(int(fps)), True, self.image_handler.debug_color)
            self.screen.blit(fps_str, (50, 50))

            pygame.display.update()
            self.clock.tick(self.option_handler.fps)


def main():
    main_window = Main()
    main_window.main_loop()


if __name__ == "__main__":
    main()
