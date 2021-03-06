import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import ldl

from optimization.optimizer import BoxConstrainedOptimizer
from utils import ldl_solve


class ActiveSet(BoxConstrainedOptimizer):
    # Apply the Active Set Method to the convex Box-Constrained Quadratic
    # program:
    #
    #  (P) min { 1/2 x^T Q x + q^T x : 0 <= x <= ub }
    #
    # - max_iter (integer scalar, optional, default value 1000): the maximum
    #   number of iterations
    #
    # Output:
    #
    # - v (real scalar): the best function value found so far (possibly the
    #   optimal one)
    #
    # - x ([n x 1] real column vector, optional): the best solution found so
    #   far (possibly the optimal one)
    #
    # - status (string, optional): a string describing the status of the
    #   algorithm at termination, with the following possible values:
    #
    #   = 'optimal': the algorithm terminated having proven that x is an
    #     (approximately) optimal solution, i.e., the norm of the gradient at x
    #     is less than the required threshold
    #
    #   = 'stopped': the algorithm terminated having exhausted the maximum
    #     number of iterations: x is the bast solution found so far, but not
    #     necessarily the optimal one

    def __init__(self, f, eps=1e-6, max_iter=1000, verbose=False, plot=False):
        super().__init__(f, eps, max_iter, verbose, plot)

    def minimize(self):

        v = self.f.function(self.wrt)

        # because all constraints are box ones, the active set is logically
        # partitioned onto the set of lower and upper bound constraints that are
        # active, L and U respectively. Of course, L and U have to be disjoint.
        # Since we start from the middle of the box, both the initial active sets
        # are empty
        L = np.full(self.f.n, False)
        U = np.full(self.f.n, False)

        # the set of "active variables", those that do *not* belong to any of the
        # two active sets and therefore are "free", is therefore the complement to
        # 1 : n of L union U; since L and U are empty now, A = 1 : n
        A = np.full(self.f.n, True)

        if self.verbose:
            print('iter\tf(x)\t\t|B|\tI/O')

        if self.plot and self.n == 2:
            surface_plot, contour_plot, contour_plot, contour_axes = self.f.plot()

        while True:
            if self.verbose:
                print('{:4d}\t{:1.4e}\t{:d}\t'.format(self.iter, v, sum(L) + sum(U)), end='')

            if self.iter >= self.max_iter:
                status = 'stopped'
                break

            # solve the unconstrained problem restricted to A the problem reads:
            #
            #  min { (1/2) x_A^T Q_{AA} x_A + (q_A + u_U^T Q_{UA}) x_A }
            #    [ + (1/2) x_U^T Q_{UU} x_U ]
            #
            # and therefore the optimal solution is:
            #
            #   x_A* = -Q_{AA}^{-1} (q_A + u_U^T Q_{UA})
            #
            # not that this actually is a constrained problem subject to equality
            # constraints, but in our case equality constraints just fix variables
            # (and anyway, any QP problem with equality constraints reduces to an
            # unconstrained one)

            xs = np.zeros(self.f.n)
            xs[U] = self.f.ub[U]

            # use the LDL^T Cholesky symmetric indefinite factorization to solve the
            # linear system since Q_{AA} is symmetric but could be not positive definite
            xs[A] = ldl_solve(ldl(self.f.Q[A, :][:, A]), -(self.f.q[A] - self.f.Q[A, :][:, U].dot(self.f.ub[U])))

            if np.logical_and(xs[A] <= self.f.ub[A] + 1e-12, xs[A] >= -1e-12).all():
                # the solution of the unconstrained problem is actually feasible

                # move the current point right there
                self.wrt = np.copy(xs)

                # compute function value and gradient
                v, g = self.f.function(self.wrt), self.f.jacobian(self.wrt)

                h = np.nonzero(np.logical_and(L, g < -1e-12))[0]
                if h.size > 0:
                    uppr = False
                else:
                    h = np.nonzero(np.logical_and(U, g > 1e-12))[0]
                    uppr = True

                if not h.size > 0:
                    status = 'optimal'
                    break
                else:
                    h = h[0]  # that's probably Bland's anti-cycle rule
                    A[h] = True
                    if uppr:
                        U[h] = False
                        if self.verbose:
                            print('O {:d}(U)'.format(h))
                    else:
                        L[h] = False
                        if self.verbose:
                            print('O {:d}(L)\n'.format(h))
            else:
                # the solution of the unconstrained problem is not feasible
                # this means that d = xs - self.wrt is a descent direction, use it
                # of course, only the "free" part really needs to be computed

                d = np.zeros(self.f.n)
                d[A] = xs[A] - self.wrt[A]

                # first, compute the maximum feasible step size max_t such that:
                #   0 <= self.wrt[i] + max_t d[i] <= u[i]   for all i

                idx = np.logical_and(A, d > 0)  # positive gradient entries
                max_t = min((self.f.ub[idx] - self.wrt[idx]) / d[idx], default=np.inf)
                idx = np.logical_and(A, d < 0)  # negative gradient entries
                max_t = min(max_t, min(-self.wrt[idx] / d[idx], default=np.inf))

                # it is useless to compute the optimal t, because we know already
                # that it is 1, whereas max_t necessarily is < 1
                self.wrt += max_t * d

                # compute function value
                v = self.f.function(self.wrt)

                # update the active set(s)
                nL = np.logical_and(A, self.wrt <= 1e-12)
                L[nL] = True
                A[nL] = False

                nU = np.logical_and(A, self.wrt >= self.f.ub - 1e-12)
                U[nU] = True
                A[nU] = False

                if self.verbose:
                    print('I {:d}+{:d}'.format(sum(nL), sum(nU)))

                # plot the trajectory
                if self.plot and self.n == 2:
                    p_xy = np.vstack((self.wrt - max_t * d, self.wrt)).T
                    contour_axes.quiver(p_xy[0, :-1], p_xy[1, :-1], p_xy[0, 1:] - p_xy[0, :-1],
                                        p_xy[1, 1:] - p_xy[1, :-1], scale_units='xy', angles='xy', scale=1, color='k')

            self.iter += 1

        if self.verbose:
            print()
        if self.plot and self.n == 2:
            plt.show()
        return self.wrt, v, status
