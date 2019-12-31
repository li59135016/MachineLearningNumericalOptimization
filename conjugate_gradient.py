import matplotlib.pyplot as plt
import numpy as np

from line_search import armijo_wolfe_line_search, backtracking_line_search
from optimization_test_functions import Ackley, Rosenbrock


def NCG(f, x, wf=0, r_start=0, eps=1e-6, max_f_eval=1000, m1=0.01, m2=0.9, a_start=1, tau=0.9,
        sfgrd=0.01, m_inf=-np.inf, min_a=1e-16, verbose=False, plot=False):
    # Apply a Nonlinear Conjugated Gradient algorithm for the minimization of
    # the provided function f.
    #
    # Input:
    #
    # - x is either a [n x 1] real (column) vector denoting the input of
    #   f(), or [] (empty).
    #
    # Output:
    #
    # - v (real, scalar): if x == [] this is the best known lower bound on
    #   the unconstrained global optimum of f(); it can be -inf if either f()
    #   is not bounded below, or no such information is available. If x ~= []
    #   then v = f(x).
    #
    # - g (real, [n x 1] real vector): this also depends on x. if x == []
    #   this is the standard starting point from which the algorithm should
    #   start, otherwise it is the gradient of f() at x (or a subgradient if
    #   f() is not differentiable at x, which it should not be if you are
    #   applying the gradient method to it).
    #
    # The other [optional] input parameters are:
    #
    # - x (either [n x 1] real vector or [], default []): starting point.
    #   If x == [], the default starting point provided by f() is used.
    #
    # - wf (integer scalar, optional, default value 0): which of the Nonlinear
    #   Conjugated Gradient formulae to use. Possible values are:
    #   = 0: Fletcher-Reeves
    #   = 1: Polak-Ribiere
    #   = 2: Hestenes-Stiefel
    #   = 3: Dai-Yuan
    #
    # - r_start (integer scalar, optional, default value 0): if > 0, restarts
    #   (setting beta = 0) are performed every n * r_start iterations
    #
    # - eps (real scalar, optional, default value 1e-6): the accuracy in the
    #   stopping criterion: the algorithm is stopped when the norm of the
    #   gradient is less than or equal to eps. If a negative value is provided,
    #   this is used in a *relative* stopping criterion: the algorithm is
    #   stopped when the norm of the gradient is less than or equal to
    #   (- eps) * || norm of the first gradient ||.
    #
    # - max_f_eval (integer scalar, optional, default value 1000): the maximum
    #   number of function evaluations (hence, iterations will be not more than
    #   max_f_eval because at each iteration at least a function evaluation is
    #   performed, possibly more due to the line search).
    #
    # - m1 (real scalar, optional, default value 0.01): first parameter of the
    #   Armijo-Wolfe-type line search (sufficient decrease). Has to be in (0,1)
    #
    # - m2 (real scalar, optional, default value 0.9): typically the second
    #   parameter of the Armijo-Wolfe-type line search (strong curvature
    #   condition). It should to be in (0,1); if not, it is taken to mean that
    #   the simpler Backtracking line search should be used instead
    #
    # - a_start (real scalar, optional, default value 1): starting value of
    #   alpha in the line search (> 0)
    #
    # - tau (real scalar, optional, default value 0.9): scaling parameter for
    #   the line search. In the Armijo-Wolfe line search it is used in the
    #   first phase: if the derivative is not positive, then the step is
    #   divided by tau (which is < 1, hence it is increased). In the
    #   Backtracking line search, each time the step is multiplied by tau
    #   (hence it is decreased).
    #
    # - sfgrd (real scalar, optional, default value 0.01): safeguard parameter
    #   for the line search. to avoid numerical problems that can occur with
    #   the quadratic interpolation if the derivative at one endpoint is too
    #   large w.r.t. the one at the other (which leads to choosing a point
    #   extremely near to the other endpoint), a *safeguarded* version of
    #   interpolation is used whereby the new point is chosen in the interval
    #   [as * (1 + sfgrd) , am * (1 - sfgrd)], being [as , am] the
    #   current interval, whatever quadratic interpolation says. If you
    #   experience problems with the line search taking too many iterations to
    #   converge at "nasty" points, try to increase this
    #
    # - m_inf (real scalar, optional, default value -inf): if the algorithm
    #   determines a value for f() <= m_inf this is taken as an indication that
    #   the problem is unbounded below and computation is stopped
    #   (a "finite -inf").
    #
    # - min_a (real scalar, optional, default value 1e-16): if the algorithm
    #   determines a step size value <= min_a, this is taken as an indication
    #   that something has gone wrong (the gradient is not a direction of
    #   descent, so maybe the function is not differentiable) and computation
    #   is stopped. It is legal to take min_a = 0, thereby in fact skipping this
    #   test.
    #
    # Output:
    #
    # - x ([n x 1] real column vector): the best solution found so far.
    #
    # - status (string): a string describing the status of the algorithm at
    #   termination
    #
    #   = 'optimal': the algorithm terminated having proven that x is a(n
    #     approximately) optimal solution, i.e., the norm of the gradient at x
    #     is less than the required threshold
    #
    #   = 'unbounded': the algorithm has determined an extremely large negative
    #     value for f() that is taken as an indication that the problem is
    #     unbounded below (a "finite -inf", see m_inf above)
    #
    #   = 'stopped': the algorithm terminated having exhausted the maximum
    #     number of iterations: x is the bast solution found so far, but not
    #     necessarily the optimal one
    #
    #   = 'error': the algorithm found a numerical error that prevents it from
    #     continuing optimization (see min_a above)

    x = np.asarray(x)

    # reading and checking input
    if not np.isrealobj(x):
        return ValueError('x not a real vector')

    if x.shape[1] != 1:
        return ValueError('x is not a (column) vector')

    f_star = f.function([])

    n = x.shape[0]

    if wf < 0 or wf > 3:
        return ValueError('unknown NCG formula {:d}'.format(wf))

    if not np.isscalar(r_start):
        return ValueError('r_start is not an integer scalar')

    if not np.isreal(eps) or not np.isscalar(eps):
        return ValueError('eps is not a real scalar')

    if not np.isscalar(max_f_eval):
        return ValueError('max_f_eval is not an integer scalar')

    if not np.isscalar(m1):
        return ValueError('m1 is not a real scalar')

    if m1 <= 0 or m1 >= 1:
        return ValueError('m1 is not in (0,1)')

    if not np.isscalar(m1):
        return ValueError('m2 is not a real scalar')

    if not np.isscalar(a_start):
        return ValueError('a_start is not a real scalar')
    if a_start < 0:
        return ValueError('a_start must be > 0')

    if not np.isscalar(tau):
        return ValueError('tau is not a real scalar')

    if tau <= 0 or tau >= 1:
        return ValueError('tau is not in (0,1)')

    if not np.isscalar(sfgrd):
        return ValueError('sfgrd is not a real scalar')

    if sfgrd <= 0 or sfgrd >= 1:
        return ValueError('sfgrd is not in (0,1)')

    if not np.isscalar(m_inf):
        return ValueError('m_inf is not a real scalar')

    if not np.isscalar(min_a):
        return ValueError('min_a is not a real scalar')

    if min_a < 0:
        return ValueError('min_a is < 0')

    last_x = np.zeros((n, 1))  # last point visited in the line search
    last_g = np.zeros((n, 1))  # gradient of last_x
    f_eval = 1  # f() evaluations count ("common" with LSs)

    # initializations
    if verbose:
        if f_star > -np.inf:
            print('f_eval\trel gap', end='')
        else:
            print('f_eval\tf(x)', end='')
        print('\t\t|| g(x) ||\tbeta\tls f_eval\ta*')

    v, g = f.function(x), f.jacobian(x)
    ng = np.linalg.norm(g)
    if eps < 0:
        ng0 = -ng  # np.linalg.norm of first subgradient
    else:
        ng0 = 1  # un-scaled stopping criterion

    if plot and n == 2:
        surface_plot, contour_plot, contour_plot, contour_axes = f.plot()

    i = 1  # iterations count (as distinguished from f() evaluations)
    while True:
        if verbose:
            # output statistics
            if f_star > -np.inf:
                print('{:4d}\t{:1.4e}\t{:1.4e}'.format(f_eval, (v - f_star) / max(abs(f_star), 1), ng), end='')
            else:
                print('{:4d}\t{:1.8e}\t\t{:1.4e}'.format(f_eval, v, ng), end='')

        # stopping criteria
        if ng <= eps * ng0:
            status = 'optimal'
            break

        if f_eval > max_f_eval:
            status = 'stopped'
            break

        # compute search direction
        # formulae could be streamlined somewhat and some
        # norms could be saved from previous iterations
        if i == 1:  # first iteration is off-line, standard gradient
            d = -g
            if verbose:
                print('\t', end='')
        else:  # normal iterations, use appropriate NCG formula
            if r_start > 0 and i % n * r_start == 0:
                # ... unless a restart is being performed
                beta = 0
                if verbose:
                    print('\t(res)', end='')
            else:
                if wf == 0:  # Fletcher-Reeves
                    beta = (ng / np.linalg.norm(past_g)) ** 2
                elif wf == 1:  # Polak-Ribiere
                    beta = (g.T.dot(g - past_g) / np.linalg.norm(past_g) ** 2).item()
                    beta = max(beta, 0)
                elif wf == 2:  # Hestenes-Stiefel
                    beta = (g.T.dot(g - past_g) / (g - past_g).T.dot(past_d)).item()
                else:  # Dai-Yuan
                    beta = (ng ** 2 / (g - past_g).T.dot(past_d)).item()
                if verbose:
                    print('\t{:1.4f}'.format(beta), end='')

            if beta != 0:
                d = -g + beta * past_d
            else:
                d = -g

        past_g = g  # previous gradient
        past_d = d  # previous search direction

        # compute step size
        phi_p0 = g.T.dot(d).item()

        if 0 < m2 < 1:
            a, v, last_x, last_g, _, f_eval = armijo_wolfe_line_search(
                f, d, x, last_x, last_g, None, f_eval, max_f_eval, min_a, sfgrd, v, phi_p0, 1, m1, m2, tau, verbose)
        else:
            a, v, last_x, last_g, _, f_eval = backtracking_line_search(
                f, d, x, last_x, last_g, None, f_eval, max_f_eval, min_a, v, phi_p0, 1, m1, tau, verbose)

        # output statistics
        if verbose:
            print('\t{:1.2e}'.format(a))

        if a <= min_a:
            status = 'error'
            break

        if v <= m_inf:
            status = 'unbounded'
            break

        # plot the trajectory
        if plot and n == 2:
            p_xy = np.hstack((x, last_x))
            contour_axes.plot(p_xy[0], p_xy[1], color='k')

        # update new point
        x = last_x

        # update gradient
        g = last_g
        ng = np.linalg.norm(g)

        # iterate
        i += 1

    if verbose:
        print()
    if plot and n == 2:
        plt.show()
    return x, status


if __name__ == "__main__":
    print(NCG(Rosenbrock(), [[-1], [1]], verbose=True, plot=True))
