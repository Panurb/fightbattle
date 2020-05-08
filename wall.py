import numpy as np
import pygame

from gameobject import GameObject
from collider import Rectangle, Group, ColliderGroup, Circle


class Wall(GameObject):
    def __init__(self, position, width, height):
        super().__init__(position)
        self.add_collider(Rectangle([0, 0], width, height, Group.WALLS))
        self.size = 1.0
        self.vertical = False

        if width == 1:
            self.vertical = True

    def get_data(self):
        return (type(self), self.position[0], self.position[1],
                2 * self.collider.half_width[0], 2 * self.collider.half_height[1])

    def draw(self, screen, camera, image_handler):
        if self.vertical:
            h = self.collider.half_height[1]
            ny = int(2 * h)

            for j, y in enumerate(np.linspace(-h, h, ny, False)):
                if j == 0:
                    l = 2
                elif j == ny - 1:
                    l = 0
                else:
                    l = 1

                self.image_position[0] = 0.0
                self.image_position[1] = y + 0.52
                self.image_path = f'wall_vertical_0_{l}'
                GameObject.draw(self, screen, camera, image_handler)
        else:
            w = self.collider.half_width[0]
            nx = int(2 * w)

            for i, x in enumerate(np.linspace(-w, w, nx, False)):
                if i == 0:
                    k = 0
                elif i == nx - 1:
                    k = 2
                else:
                    k = 1

                self.image_position[0] = x + 0.5
                self.image_position[1] = 0.04
                self.image_path = f'wall_{k}_0'
                GameObject.draw(self, screen, camera, image_handler)

    def draw_front(self, screen, camera, image_handler):
        pass


class Platform(Wall):
    def __init__(self, position, width):
        super().__init__(position, width, 1)
        self.collider.group = Group.PLATFORMS
        self.image_path = 'platform'
        self.image_position[1] = 0.33

    def get_data(self):
        return type(self), self.position[0], self.position[1], 2 * self.collider.half_width[0]

    def draw(self, screen, camera, image_handler):
        w = self.collider.half_width[0]
        nx = int(2 * w)

        for i, x in enumerate(np.linspace(-w, w, nx, False)):
            if i == 0:
                k = 0
            elif i == nx - 1:
                k = 2
            else:
                k = 1

            self.image_position[0] = x + 0.5
            self.image_position[1] = 0.33
            self.image_path = f'platform_{k}_0'
            GameObject.draw(self, screen, camera, image_handler)


class Basket(GameObject):
    def __init__(self, position, team=0):
        super().__init__(position)
        self.add_collider(ColliderGroup(self.position))
        self.collider.add_collider(Circle([-0.3, 0.0], 0.1, Group.WALLS))
        self.collider.add_collider(Circle([1.3, 0.0], 0.1, Group.WALLS))
        self.collider.add_collider(Circle([0.5, -0.5], 0.2, Group.GOALS))
        self.collider.add_collider(Rectangle([0.5, -0.9], 1.4, -0.5, Group.WALLS))
        self.team = team
        self.score = 0

    def get_data(self):
        return type(self), self.position[0], self.position[1], self.team

    def draw(self, screen, camera, image_handler):
        self.image_path = 'basket'
        self.image_position = np.array([0.4, -0.15])
        super().draw(screen, camera, image_handler)

    def draw_front(self, screen, camera, image_handler):
        self.image_path = 'basket_front'
        self.image_position = np.array([0.4, -0.7])
        super().draw(screen, camera, image_handler)


class Scoreboard(GameObject):
    def __init__(self, position):
        super().__init__(position)
        self.add_collider(Rectangle([0, 0], 7, 4))
        self.scores = [0, 0]

    def draw(self, screen, camera, image_handler):
        super().draw(screen, camera, image_handler)

        points = [camera.world_to_screen(p) for p in self.collider.corners()]

        pygame.draw.polygon(screen, (10, 10, 10), points)

        font = image_handler.get_font('Seven Segment', int(camera.zoom * 3))
        text = font.render(' - '.join(map(str, self.scores)), True, (200, 255, 0))
        pos = camera.world_to_screen(self.position)
        screen.blit(text, [pos[0] - text.get_width() // 2, pos[1] - text.get_height() // 2])

    def update(self, gravity, time_step, colliders):
        pass
