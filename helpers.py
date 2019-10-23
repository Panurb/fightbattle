import numpy as np
from numpy.linalg import norm


def norm2(r):
    return np.sum(r**2)


def projection(v, a, b):
    return np.array([np.dot(v, a) / norm(a), np.dot(v, b) / norm(b)])
