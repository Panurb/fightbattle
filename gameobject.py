import numpy as np

from collider import Group, Type


class GameObject:
    def __init__(self, position, group=Group.WALLS):
        self.position = np.array(position, dtype=float)
        self.colliders = []
        self.group = group

    def set_position(self, position):
        delta_pos = position - self.position

        self.position += delta_pos
        for c in self.colliders:
            c.position += delta_pos

    def add_collider(self, collider):
        collider.group = self.group
        self.colliders.append(collider)

    def draw(self, screen, camera):
        for collider in self.colliders:
            collider.draw(screen, camera)


class PhysicsObject(GameObject):
    def __init__(self, position, velocity=(0, 0), group=Group.WALLS):
        super().__init__(position, group)
        self.velocity = np.array(velocity, dtype=float)
        self.acceleration = np.zeros(2)

        self.angle = 0.0
        self.angular_velocity = 0.0
        self.angular_acceleration = 0.0

        self.bounce = 0.5
        self.on_ground = False

    def draw(self, screen, camera):
        super().draw(screen, camera)

    def update(self, gravity, time_step, colliders):
        if self.velocity[1] > 0:
            self.on_ground = False

        delta_pos = self.velocity * time_step + 0.5 * (gravity + self.acceleration) * time_step**2
        self.position += delta_pos

        self.angle += self.angular_velocity * time_step + 0.5 * self.angular_acceleration * time_step**2

        acc_old = gravity + self.acceleration
        ang_acc_old = float(self.angular_acceleration)

        collisions = []
        for collider in self.colliders:
            collider.position += delta_pos
            collider.update_collisions(colliders)
            collisions += collider.collisions

        for collision in collisions:
            if collision.overlap[1] > 0:
                self.on_ground = True

            self.position += collision.overlap

            for collider in self.colliders:
                collider.position += collision.overlap

            if self.bounce:
                n = collision.overlap
                self.velocity -= 2 * self.velocity.dot(n) * n / n.dot(n)
                self.velocity *= self.bounce
            else:
                if collision.overlap[0] == 0:
                    self.velocity[1] = 0.0
                elif collision.overlap[1] == 0:
                    self.velocity[0] = 0.0

                if collision.overlap[0] == 0:
                    self.acceleration[0] -= np.sign(self.velocity[0]) * collision.collider.friction

            #for c in self.colliders:
            #    for s in collision.supports:
            #        if c.left() <= s[0] <= c.right():
            #            self.angular_acceleration += np.cross(self.position - s, gravity)

        self.velocity += 0.5 * (acc_old + gravity + self.acceleration) * time_step
        self.angular_velocity += 0.5 * (ang_acc_old + self.angular_acceleration) * time_step

        if abs(self.velocity[0]) < 0.05:
            self.velocity[0] = 0
            self.acceleration[0] = 0

        #for c in self.colliders:
        #    r = np.array([[np.cos(self.angle), -np.sin(self.angle)], [np.sin(self.angle), np.cos(self.angle)]])
        #    if c.type is Type.RECTANGLE:
        #        c.half_width = r @ c.half_width
        #        c.half_height = r @ c.half_height
