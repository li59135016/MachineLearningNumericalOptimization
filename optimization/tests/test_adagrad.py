import numpy as np
import pytest

from optimization.optimization_function import quad1, quad2, Rosenbrock
from optimization.unconstrained.adagrad import AdaGrad


def test_AdaGrad_quadratic():
    x, _ = AdaGrad(quad1, nesterov_momentum=True).minimize()
    assert np.allclose(x, quad1.x_star(), rtol=1e-3)

    x, _ = AdaGrad(quad2, nesterov_momentum=True).minimize()
    assert np.allclose(x, quad2.x_star(), rtol=0.1)


def test_AdaGrad_Rosenbrock():
    obj = Rosenbrock()
    x, _ = AdaGrad(obj, nesterov_momentum=True).minimize()
    assert np.allclose(x, obj.x_star(), rtol=0.01)


if __name__ == "__main__":
    pytest.main()