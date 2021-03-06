import itertools

import numpy as np

from ml.initializers import random_uniform
from optimization.optimization_function import OptimizationFunction, BoxConstrainedQuadratic
from optimization.line_search import ArmijoWolfeLineSearch, BacktrackingLineSearch
from utils import iter_mini_batches


class Optimizer:

    def __init__(self, f, wrt=random_uniform, batch_size=None, eps=1e-6, max_iter=1000, verbose=False, plot=False):
        """

        :param f:        the objective function.
        :param wrt:      ([n x 1] real column vector): the point where to start the algorithm from.
        :param eps:      (real scalar, optional, default value 1e-6): the accuracy in the stopping
                         criterion: the algorithm is stopped when the norm of the gradient is less
                         than or equal to eps.
        :param max_iter: (integer scalar, optional, default value 1000): the maximum number of iterations.
        :param verbose:  (boolean, optional, default value False): print details about each iteration
                         if True, nothing otherwise.
        :param plot:     (boolean, optional, default value False): plot the function's surface and its contours
                         if True and the function's dimension is 2, nothing otherwise.
        """
        if not isinstance(f, OptimizationFunction):
            raise TypeError('f is not an optimization function')
        self.f = f
        if callable(wrt):
            self.wrt = wrt(f.n)
        elif not np.isrealobj(wrt):
            raise ValueError('x not a real vector')
        else:
            self.wrt = np.asarray(wrt, dtype=float)
        self.n = self.wrt.size
        self.batch_size = batch_size
        if not np.isscalar(eps):
            raise ValueError('eps is not a real scalar')
        if not eps > 0:
            raise ValueError('eps must be > 0')
        self.eps = eps
        if not np.isscalar(max_iter):
            raise ValueError('max_iter is not an integer scalar')
        if not max_iter > 0:
            raise ValueError('max_iter must be > 0')
        self.max_iter = max_iter
        self.iter = 1
        self.verbose = verbose
        self.plot = plot
        if batch_size is None:
            self.args = itertools.repeat(f.args())
        else:
            self.args = (i for i in iter_mini_batches(f.args(), batch_size))

    def minimize(self):
        raise NotImplementedError


class BoxConstrainedOptimizer(Optimizer):
    def __init__(self, f, eps=1e-6, max_iter=1000, verbose=False, plot=False):
        if not isinstance(f, BoxConstrainedQuadratic):
            raise TypeError('f is not a box-constrained quadratic function')
        super().__init__(f, f.ub / 2,  # start from the middle of the box
                         eps=eps, max_iter=max_iter, verbose=verbose, plot=plot)


class LineSearchOptimizer(Optimizer):

    def __init__(self, f, wrt=random_uniform, batch_size=None, eps=1e-6, max_iter=1000, max_f_eval=1000, m1=0.01,
                 m2=0.9, a_start=1, tau=0.9, sfgrd=0.01, m_inf=-np.inf, min_a=1e-16, verbose=False, plot=False):
        """

        :param f:          the objective function.
        :param wrt:        ([n x 1] real column vector): the point where to start the algorithm from.
        :param eps:        (real scalar, optional, default value 1e-6): the accuracy in the stopping
                           criterion: the algorithm is stopped when the norm of the gradient is less
                           than or equal to eps.
        :param max_f_eval: (integer scalar, optional, default value 1000): the maximum number of
                           function evaluations (hence, iterations will be not more than max_f_eval
                           because at each iteration at least a function evaluation is performed,
                           possibly more due to the line search).
        :param m1:         (real scalar, optional, default value 0.01): first parameter of the
                           Armijo-Wolfe-type line search (sufficient decrease). Has to be in (0,1).
        :param m2:         (real scalar, optional, default value 0.9): typically the second parameter
                           of the Armijo-Wolfe-type line search (strong curvature condition). It should
                           to be in (0,1); if not, it is taken to mean that the simpler Backtracking
                           line search should be used instead.
        :param a_start:    (real scalar, optional, default value 1): starting value of alpha in the
                           line search (> 0).
        :param tau:        (real scalar, optional, default value 0.9): scaling parameter for the line
                           search. In the Armijo-Wolfe line search it is used in the first phase: if the
                           derivative is not positive, then the step is divided by tau (which is < 1,
                           hence it is increased). In the Backtracking line search, each time the step is
                           multiplied by tau (hence it is decreased).
        :param sfgrd:      (real scalar, optional, default value 0.01): safeguard parameter for the line search.
                           To avoid numerical problems that can occur with the quadratic interpolation if the
                           derivative at one endpoint is too large w.r.t. The one at the other (which leads to
                           choosing a point extremely near to the other endpoint), a *safeguarded* version of
                           interpolation is used whereby the new point is chosen in the interval
                           [as * (1 + sfgrd) , am * (1 - sfgrd)], being [as , am] the current interval, whatever
                           quadratic interpolation says. If you experience problems with the line search taking
                           too many iterations to converge at "nasty" points, try to increase this.
        :param m_inf:      (real scalar, optional, default value -inf): if the algorithm determines a value for
                           f() <= m_inf this is taken as an indication that the problem is unbounded below and
                           computation is stopped (a "finite -inf").
        :param min_a:      (real scalar, optional, default value 1e-16): if the algorithm determines a step size
                           value <= min_a, this is taken as an indication that something has gone wrong (the gradient
                           is not a direction of descent, so maybe the function is not differentiable) and computation
                           is stopped. It is legal to take min_a = 0, thereby in fact skipping this test.
        :param verbose:    (boolean, optional, default value False): print details about each iteration
                           if True, nothing otherwise.
        :param plot:       (boolean, optional, default value False): plot the function's surface and its contours
                           if True and the function's dimension is 2, nothing otherwise.
        """
        super().__init__(f, wrt, batch_size, eps, max_iter, verbose, plot)
        if not np.isscalar(m_inf):
            raise ValueError('m_inf is not a real scalar')
        self.m_inf = m_inf
        if 0 < m2 < 1:
            self.line_search = ArmijoWolfeLineSearch(f, max_f_eval, m1, m2, a_start, tau, sfgrd, min_a, verbose)
        else:
            self.line_search = BacktrackingLineSearch(f, max_f_eval, m1, a_start, min_a, tau, verbose)
