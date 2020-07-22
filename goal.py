from collider import ColliderGroup, Circle, Rectangle, Group
from gameobject import GameObject


class Goal(GameObject):
    def __init__(self, position, image_path, team='blue'):
        super().__init__(position, image_path=image_path)
        self.team = team
        self.score = 0

    def get_data(self):
        return type(self), self.position[0], self.position[1], self.team

    def apply_data(self, data):
        super().apply_data(data)
        self.team = data[-1]

    def change_team(self):
        self.team = 'blue' if self.team == 'red' else 'red'


class Basket(Goal):
    def __init__(self, position, team='blue'):
        super().__init__(position, 'basket', team)
        self.image_position[:] = [0.4, -0.15]
        self.add_collider(ColliderGroup([0, 0]))
        self.collider.add_collider(Circle([-0.3, 0.0], 0.1, Group.WALLS))
        self.collider.add_collider(Circle([1.3, 0.0], 0.1, Group.WALLS))
        self.collider.add_collider(Circle([0.5, -0.5], 0.2, Group.GOALS))
        self.collider.add_collider(Rectangle([0.5, -0.9], 1.4, -0.5, Group.WALLS))
        self.front = GameObject(self.position, 'basket_front', layer=4)
        self.front.image_position[:] = [0.4, -0.72]

    def reset(self):
        self.collider.colliders[-1].group = Group.WALLS

    def delete(self):
        super().delete()
        self.front.delete()

    def set_position(self, position):
        super().set_position(position)
        self.front.set_position(position)

    def draw(self, batch, camera, image_handler):
        super().draw(batch, camera, image_handler)
        self.front.draw(batch, camera, image_handler)

    def draw_shadow(self, batch, camera, image_handler, light):
        super().draw_shadow(batch, camera, image_handler, light)
        self.front.draw_shadow(batch, camera, image_handler, light)


class Exit(Goal):
    def __init__(self, position, team='blue'):
        super().__init__(position, 'exit', team)
        self.add_collider(Rectangle([0, 0], 1, 3, group=Group.GOALS))
        self.image_position[1] = 0.45
        self.size = 1.0
