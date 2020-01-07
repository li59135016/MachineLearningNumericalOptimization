import numpy as np
import pytest

from optimization.test_functions import *
from optimization.unconstrained.quasi_newton import BroydenFletcherGoldfarbShanno


def test_quadratic():
    x, status = BroydenFletcherGoldfarbShanno(gen_quad_1).minimize()
    assert np.allclose(x, gen_quad_1.x_star)
    assert status is 'optimal'

    x, status = BroydenFletcherGoldfarbShanno(gen_quad_2).minimize()
    assert np.allclose(x, gen_quad_2.x_star)
    assert status is 'optimal'

    x, status = BroydenFletcherGoldfarbShanno(gen_quad_5).minimize()
    assert np.allclose(x, gen_quad_5.x_star)
    assert status is 'optimal'


def test_Rosenbrock():
    obj = Rosenbrock()
    x, status = BroydenFletcherGoldfarbShanno(Rosenbrock()).minimize()
    assert np.allclose(x, obj.x_star)
    assert status is 'optimal'


if __name__ == "__main__":
    pytest.main()
