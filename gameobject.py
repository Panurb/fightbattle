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
        self.mass = 1.0
        self.inertia = self.mass * (1**2 + 1**2) / 12
        self.inertia = 50

    def draw(self, screen, camera):
        super().draw(screen, camera)

    def update(self, gravity, time_step, colliders):
        if self.velocity[1] > 0:
            self.on_ground = False

        delta_pos = self.velocity * time_step + 0.5 * self.acceleration * time_step**2
        self.position += delta_pos

        self.angle += self.angular_velocity * time_step + 0.5 * self.angular_acceleration * time_step**2

        acc_old = self.acceleration
        ang_acc_old = float(self.angular_acceleration)

        self.acceleration[:] = gravity
        self.angular_acceleration = 0.0

        for collider in self.colliders:
            collider.position += delta_pos
            collider.update_collisions(colliders)

            for collision in collider.collisions:
                if collision.overlap[1] > 0:
                    self.on_ground = True

                self.position += collision.overlap

                for c in self.colliders:
                    c.position += collision.overlap

                if self.bounce:
                    n = collision.overlap
                    self.velocity -= 2 * self.velocity.dot(n) * n / n.dot(n)
                    self.velocity *= self.bounce
                else:
                    if not collision.overlap[0]:
                        self.velocity[1] = 0.0
                        self.acceleration[0] -= np.sign(self.velocity[0]) * collision.collider.friction
                    elif not collision.overlap[1]:
                        self.velocity[0] = 0.0

                left = collider.right()
                right = collider.left()
                for s in collision.supports:
                    left = min(left, s[0])
                    right = max(right, s[0])

                if not left < self.position[0] < right:
                    for s in collision.supports:
                        r = self.position - s

                        # Steiner's theorem
                        inertia = self.inertia + self.mass * np.sum(r**2)

                        alpha = np.cross(r, gravity) / inertia
                        self.angular_acceleration += alpha

                        t = np.cross(r, np.array([0, 0, 1]))[:-1]
                        t /= np.linalg.norm(t)
                        self.acceleration += np.linalg.norm(r) * alpha * t

        self.velocity += 0.5 * (acc_old + self.acceleration) * time_step
        self.angular_velocity += 0.5 * (ang_acc_old + self.angular_acceleration) * time_step

        if abs(self.velocity[0]) < 0.05:
            self.velocity[0] = 0
            self.acceleration[0] = 0

        for c in self.colliders:
            r = np.array([[np.cos(self.angle), -np.sin(self.angle)], [np.sin(self.angle), np.cos(self.angle)]])
            if c.type is Type.RECTANGLE:
                c.half_width = np.matmul(r, c.half_width)
                c.half_height = np.matmul(r, c.half_height)
