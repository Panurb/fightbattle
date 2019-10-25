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
