import os
from enum import Enum

import numpy as np

from collider import Circle, Group, GRID_SIZE
from helpers import normalized, norm2, basis
from player import Player
from weapon import Weapon, Axe

path = os.path.join('data', 'images', 'heads')
HEADS = [x.split('.')[0] for x in os.listdir(path)]

path = os.path.join('data', 'images', 'bodies')
BODIES = [x.split('.')[0] for x in os.listdir(path)]


class EnemyState(Enum):
    IDLE = 1
    SEEK_WEAPON = 2
    SEEK_PLAYER = 5
    PATROL = 6
    RUN_AWAY = 7
    DEAD = 8


class Enemy(Player):
    def __init__(self, position):
        super().__init__(position, controller_id=-1)
        self.goal = None
        self.body_type = np.random.choice(BODIES)
        self.head_type = np.random.choice(HEADS)
        self.state = EnemyState.IDLE
        self.vision_collider = Circle(self.position, 0.25)
        self.ai_timer = 0
        self.team = 'red'

    def reset(self, colliders):
        super().reset(colliders)
        self.goal = None
        self.state = EnemyState.IDLE

    def update_ai(self, objects, player, colliders):
        if self.ai_timer == 0:
            self.ai_timer = 10
        else:
            self.ai_timer -= 1
            return

        self.grabbing = False
        self.goal_crouched = 0.0

        self.vision_collider.set_position(self.position + np.array([2 * self.direction, -2]))
        self.vision_collider.update_occupied_squares(colliders)
        self.vision_collider.update_collisions(colliders, {Group.WALLS, Group.PLATFORMS})

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

            r = self.goal.position - self.position
            self.hand_goal = normalized(r)

            if abs(r[0]) < 0.25:
                self.goal_velocity[0] = 0.0
                if abs(r[1]) > 0.5:
                    self.goal_crouched = 1.0
                self.grabbing = True
            else:
                self.goal_velocity[0] = np.sign(r[0]) * self.walk_speed

            if self.object:
                self.goal_velocity[0] = 0.0
                self.state = EnemyState.PATROL
                self.goal = None
        elif self.state is EnemyState.SEEK_PLAYER:
            r = player.position - self.position
            self.hand_goal = normalized(r)

            if type(self.object) is Axe:
                if abs(r[0]) > 2.0:
                    self.goal_velocity[0] = np.sign(r[0]) * self.run_speed
                else:
                    self.goal_velocity[0] = 0.0
                    self.attack()
            elif abs(r[0]) > 10.0:
                self.goal_velocity[0] = np.sign(r[0]) * self.run_speed
            else:
                self.goal_velocity[0] = 0.0
                if abs(self.hand.angle - np.arctan(r[1] / (r[0] + 1e-3))) < 0.15:
                    self.attack()

            if not self.vision_collider.collisions:
                self.goal_velocity[0] = 0.0

            if player.destroyed:
                self.state = EnemyState.IDLE
            elif not self.object:
                self.state = EnemyState.SEEK_WEAPON

            if not self.raycast(self.position, r, colliders):
                self.state = EnemyState.PATROL
                self.goal_velocity[0] = 0.0
        elif self.state is EnemyState.PATROL:
            if not self.goal_velocity[0]:
                self.goal_velocity[0] = 0.5 * self.walk_speed

            for c in self.collider.collisions:
                if c.overlap[0] and c.collider.group is Group.WALLS:
                    self.goal_velocity[0] = np.sign(c.overlap[0]) * 0.5 * self.walk_speed
                    break

            if not self.vision_collider.collisions:
                self.goal_velocity[0] *= -1

            self.hand_goal = np.sign(self.goal_velocity[0]) * basis(0)

            if not self.object:
                self.state = EnemyState.SEEK_WEAPON

            r = player.position - self.position
            if r[0] * self.direction > 0 and abs(r[0]) < 20 and abs(r[1]) < 5:
                if self.raycast(self.position, r, colliders):
                    if self.object:
                        self.state = EnemyState.SEEK_PLAYER
                    else:
                        self.state = EnemyState.RUN_AWAY

            if player.object and isinstance(player.object, Weapon) and player.object.timer > 0:
                self.state = EnemyState.SEEK_PLAYER
        elif self.state is EnemyState.RUN_AWAY:
            r = player.position - self.position
            self.goal_velocity[0] = -np.sign(r[0]) * self.run_speed
            self.hand_goal = -np.sign(r) * basis(0)

            if not self.vision_collider.collisions:
                self.goal_velocity[0] = 0.0
        elif self.state is EnemyState.DEAD:
            self.goal_velocity[0] = 0.0
        
        if self.destroyed:
            self.state = EnemyState.DEAD

    def raycast(self, origin, velocity, colliders):
        position = np.floor(origin / GRID_SIZE)
        step = np.sign(velocity)

        t_max = (GRID_SIZE - (origin * step) % GRID_SIZE) / np.abs(velocity + 1e-6)
        t_delta = GRID_SIZE / np.abs(velocity + 1e-6)

        while True:
            if t_max[0] < t_max[1]:
                t_max[0] += t_delta[0]
                position[0] += step[0]
            else:
                t_max[1] += t_delta[1]
                position[1] += step[1]

            for c in reversed(colliders[int(position[0])][int(position[1])]):
                if c.parent is self:
                    continue
                if c.group is Group.WALLS:
                    return False
                if c.group is Group.PLAYERS:
                    return True

            if not 0 <= position[0] <= len(colliders) - 1:
                break

            if not 0 <= position[1] <= len(colliders[0]) - 1:
                break

        return False

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        #self.vision_collider.draw(batch, camera, image_handler)
