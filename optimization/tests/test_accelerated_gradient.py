import numpy as np
import pytest

from optimization.optimization_function import quad1, quad2, Rosenbrock
from optimization.unconstrained.accelerated_gradient import AcceleratedGradient, SteepestDescentAcceleratedGradient


def test_quadratic_wf0():
    assert np.allclose(SteepestDescentAcceleratedGradient(quad1, wf=0).minimize()[0], quad1.x_star())
    assert np.allclose(AcceleratedGradient(quad1, wf=0).minimize()[0], quad1.x_star())

    assert np.allclose(SteepestDescentAcceleratedGradient(quad2, wf=0).minimize()[0], quad2.x_star())
    assert np.allclose(AcceleratedGradient(quad2, wf=0).minimize()[0], quad2.x_star())


def test_quadratic_wf1():
    assert np.allclose(SteepestDescentAcceleratedGradient(quad1, wf=1).minimize()[0], quad1.x_star())
    assert np.allclose(AcceleratedGradient(quad1, wf=1).minimize()[0], quad1.x_star())

    assert np.allclose(SteepestDescentAcceleratedGradient(quad2, wf=1).minimize()[0], quad2.x_star())
    assert np.allclose(AcceleratedGradient(quad2, wf=1).minimize()[0], quad2.x_star())


def test_quadratic_wf2():
    assert np.allclose(SteepestDescentAcceleratedGradient(quad1, wf=2).minimize()[0], quad1.x_star())
    assert np.allclose(AcceleratedGradient(quad1, wf=2).minimize()[0], quad1.x_star())

    assert np.allclose(SteepestDescentAcceleratedGradient(quad2, wf=2).minimize()[0], quad2.x_star())
    assert np.allclose(AcceleratedGradient(quad2, wf=2).minimize()[0], quad2.x_star())


def test_quadratic_wf3():
    assert np.allclose(SteepestDescentAcceleratedGradient(quad1, wf=3).minimize()[0], quad1.x_star(), rtol=0.1)
    assert np.allclose(AcceleratedGradient(quad1, wf=3).minimize()[0], quad1.x_star())

    assert np.allclose(SteepestDescentAcceleratedGradient(quad2, wf=3).minimize()[0], quad2.x_star(), rtol=0.1)
    assert np.allclose(AcceleratedGradient(quad2, wf=3).minimize()[0], quad2.x_star())


def test_Rosenbrock():
    obj = Rosenbrock()
    assert np.allclose(SteepestDescentAcceleratedGradient(obj, a_start=0.1).minimize()[0], obj.x_star(), rtol=0.1)


if __name__ == "__main__":
    pytest.main()
