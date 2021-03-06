import numpy as np
import pytest

from optimization.optimization_function import quad1, quad2, Rosenbrock
from optimization.unconstrained.adadelta import AdaDelta


def test_AdaDelta_standard_momentum_quadratic():
    assert np.allclose(AdaDelta(quad1, momentum_type='standard').minimize()[0], quad1.x_star(), rtol=0.01)
    assert np.allclose(AdaDelta(quad2, momentum_type='standard').minimize()[0], quad2.x_star(), rtol=0.01)


def test_AdaDelta_standard_momentum_Rosenbrock():
    obj = Rosenbrock()
    assert np.allclose(AdaDelta(obj, momentum_type='nesterov').minimize()[0], obj.x_star(), rtol=0.01)


def test_AdaDelta_nesterov_momentum_quadratic():
    assert np.allclose(AdaDelta(quad1, momentum_type='nesterov').minimize()[0], quad1.x_star(), rtol=0.01)
    assert np.allclose(AdaDelta(quad2, momentum_type='nesterov').minimize()[0], quad2.x_star(), rtol=1e-3)


def test_AdaDelta_nesterov_momentum_Rosenbrock():
    obj = Rosenbrock()
    assert np.allclose(AdaDelta(obj, momentum_type='nesterov').minimize()[0], obj.x_star(), rtol=0.01)


if __name__ == "__main__":
    pytest.main()
