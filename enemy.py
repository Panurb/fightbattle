import os
from enum import Enum

import numpy as np

from collider import Circle, Group
from helpers import normalized, norm2, basis
from player import Player
from prop import Crate
from weapon import Shield, Weapon, Axe

path = os.path.join('data', 'images', 'heads')
HEADS = [x.split('.')[0] for x in os.listdir(path)]

path = os.path.join('data', 'images', 'bodies')
BODIES = [x.split('.')[0] for x in os.listdir(path)]


class EnemyState(Enum):
    IDLE = 1
    SEEK_WEAPON = 2
    SEEK_CRATE = 3
    HOLDING_CRATE = 4
    SEEK_PLAYER = 5
    PATROL = 6
    RUN_AWAY = 7


class Enemy(Player):
    def __init__(self, position):
        super().__init__(position, controller_id=-1)
        self.goal = None
        self.body_type = np.random.choice(BODIES)
        self.head_type = np.random.choice(HEADS)
        self.state = EnemyState.IDLE
        self.vision_collider = Circle(self.position, 1)

    def reset(self, colliders):
        super().reset(colliders)
        self.goal = None
        self.state = EnemyState.IDLE

    def update(self, gravity, time_step, colliders):
        super().update(gravity, time_step, colliders)

        self.vision_collider.set_position(self.position + np.array([2 * self.direction, -1]))
        self.vision_collider.update_occupied_squares(colliders)
        self.vision_collider.update_collisions(colliders, {Group.WALLS, Group.PLATFORMS})

    def update_ai(self, objects, player):
        print(self.state)

        self.goal_crouched = 0.0

        if self.state is EnemyState.IDLE:
            self.goal_velocity[0] = 0.0
            if not self.object:
                self.state = EnemyState.SEEK_WEAPON
        elif self.state is EnemyState.SEEK_WEAPON:
            if self.goal is None:
                for obj in sorted(objects.values(), key=lambda x: norm2(self.position - x.position)):
                    if obj.parent:
                        continue

                    if isinstance(obj, Weapon):
                        self.goal = objects[obj.id]
                        break
                else:
                    self.state = EnemyState.SEEK_CRATE
                    return

            r = self.goal.position - self.position
            self.hand_goal = normalized(r)

            if abs(r[0]) < 0.25:
                self.goal_velocity[0] = 0.0
                if abs(r[1]) > 0.5:
                    self.goal_crouched = 1.0
                self.grab_object()
            else:
                self.goal_velocity[0] = np.sign(r[0]) * self.walk_speed

            if self.object:
                self.goal_velocity[0] = 0.0
                self.state = EnemyState.PATROL
                self.goal = None
        elif self.state is EnemyState.SEEK_CRATE:
            if self.goal is None:
                for obj in sorted(objects.values(), key=lambda x: norm2(self.position - x.position)):
                    if obj.parent:
                        continue

                    if type(obj) is Crate:
                        self.goal = objects[obj.id]
                        break
                else:
                    self.state = EnemyState.RUN_AWAY
                    return

            r = self.goal.position - self.position
            self.hand_goal = normalized(r)

            if abs(r[0]) < 0.25:
                self.goal_velocity[0] = 0.0
                if abs(r[1]) > 0.5:
                    self.goal_crouched = 1.0
                self.grab_object()
            else:
                self.goal_velocity[0] = np.sign(r[0]) * self.walk_speed

            if self.object:
                self.state = EnemyState.HOLDING_CRATE
                self.goal_crouched = 0.0
        elif self.state is EnemyState.HOLDING_CRATE:
            self.hand_goal = -basis(1)
            self.goal_velocity[0] = 0.0
            if self.throw_charge == 1:
                self.throw_object()
                self.charging_throw = False
            else:
                self.charging_throw = True

            if self.goal.destroyed:
                self.goal = None
                self.state = EnemyState.SEEK_WEAPON
        elif self.state is EnemyState.SEEK_PLAYER:
            r = player.position - self.position
            self.hand_goal = normalized(r)

            if type(self.object) is Axe:
                if abs(r[0]) > 1.0:
                    self.goal_velocity[0] = np.sign(r[0]) * self.run_speed
                else:
                    self.goal_velocity[0] = 0.0
                    self.attack()
            elif abs(r[0]) > 10.0:
                self.goal_velocity[0] = np.sign(r[0]) * self.run_speed
            else:
                self.goal_velocity[0] = 0.0
                if abs(self.hand.angle - np.arctan(r[1] / (r[0] + 1e-3))) < 0.1:
                    self.attack()

            if not self.vision_collider.collisions:
                self.goal_velocity[0] = 0.0

            if player.destroyed:
                self.state = EnemyState.IDLE
            elif not self.object:
                self.state = EnemyState.SEEK_WEAPON
        elif self.state is EnemyState.PATROL:
            if not self.goal_velocity[0]:
                self.goal_velocity[0] = 0.5 * self.walk_speed

            for c in self.collider.collisions:
                if c.overlap[0]:
                    self.goal_velocity[0] = np.sign(c.overlap[0]) * 0.5 * self.walk_speed
                    break

            if not self.vision_collider.collisions:
                self.goal_velocity[0] *= -1

            self.hand_goal = np.sign(self.goal_velocity[0]) * basis(0)

            if not self.object:
                self.state = EnemyState.SEEK_WEAPON

            r = player.position - self.position
            if r[0] * self.direction > 0 and abs(r[1]) < 0.5:
                self.state = EnemyState.SEEK_PLAYER

            if player.object and player.object.attacked:
                self.direction = np.sign(r)
                self.state = EnemyState.SEEK_PLAYER
        elif self.state is EnemyState.RUN_AWAY:
            r = player.position - self.position
            self.goal_velocity[0] = -np.sign(r[0]) * self.run_speed
            self.direction = -np.sign(r[0])

            if not self.vision_collider.collisions:
                self.goal_velocity[0] = 0.0
