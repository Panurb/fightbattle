import numpy as np
from numpy.linalg import norm

from helpers import normalized
from player import Player
from weapon import Sword


class Enemy(Player):
    def __init__(self, position):
        super().__init__(position)
        self.object = Sword(self.hand.position)
        self.object.parent = self

    def seek_players(self, players):
        if self.destroyed:
            return

        goal = None
        dist = np.inf
        for p in players:
            if p.destroyed:
                continue

            d = norm(p.position - self.position)
            if d < dist:
                goal = p.position
                dist = d

        if goal is None:
            return

        if dist > 2.0:
            self.goal_velocity[0] = 0.25 * normalized(goal - self.position)[0]
        else:
            self.goal_velocity[0] = 0.0
            self.attack()
        self.hand_goal[0] = np.sign(goal - self.position)[0]
