import numpy as np
from numpy.linalg import norm


def norm2(r):
    return np.sum(r**2)


def basis(i):
    v = np.zeros(2)
    v[i] = 1
    return v


def perp(v):
    return np.array([-v[1], v[0]])


def projection(v, a, b):
    return np.array([np.dot(v, a) / norm(a), np.dot(v, b) / norm(b)])


def normalized(v):
    return v / norm(v)


def random_unit():
    theta = np.random.uniform(0, 2 * np.pi)
    return np.array([np.cos(theta), np.sin(theta)])


def rotate(v, angle):
    r = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    return np.matmul(r, v)


def polar_angle(v):
    return np.arctan2(*v[::-1])


def polar_to_carteesian(r, theta):
    return r * np.array([np.cos(theta), np.sin(theta)])
