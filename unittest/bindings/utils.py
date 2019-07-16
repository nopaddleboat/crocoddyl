import crocoddyl
import numpy as np
import scipy.linalg as scl


def a2m(a):
    return np.matrix(a).T


def m2a(m):
    return np.array(m).squeeze()


def rev_enumerate(l):
    return reversed(list(enumerate(l)))


def raiseIfNan(A, error=None):
    if error is None:
        error = scl.LinAlgError("NaN in array")
    if np.any(np.isnan(A)) or np.any(np.isinf(A)) or np.any(abs(np.asarray(A)) > 1e30):
        raise error


class StateVectorDerived(crocoddyl.StateAbstract):
    def __init__(self, nx):
        crocoddyl.StateAbstract.__init__(self, nx, nx)

    def zero(self):
        return np.matrix(np.zeros(self.nx)).T

    def rand(self):
        return np.matrix(np.random.rand(self.nx)).T

    def diff(self, x0, x1):
        return x1 - x0

    def integrate(self, x, dx):
        return x + dx

    def Jdiff(self, x1, x2, firstsecond='both'):
        assert (firstsecond in ['first', 'second', 'both'])
        if firstsecond == 'both':
            return [self.Jdiff(x1, x2, 'first'), self.Jdiff(x1, x2, 'second')]

        J = np.zeros([self.ndx, self.ndx])
        if firstsecond == 'first':
            J[:, :] = -np.eye(self.ndx)
        elif firstsecond == 'second':
            J[:, :] = np.eye(self.ndx)
        return J

    def Jintegrate(self, x, dx, firstsecond='both'):
        assert (firstsecond in ['first', 'second', 'both'])
        if firstsecond == 'both':
            return [self.Jintegrate(x, dx, 'first'), self.Jintegrate(x, dx, 'second')]
        return np.eye(self.ndx)


class UnicycleDerived(crocoddyl.ActionModelAbstract):
    def __init__(self):
        crocoddyl.ActionModelAbstract.__init__(self, crocoddyl.StateVector(3), 2, 5)
        self.dt = .1
        self.costWeights = [10., 1.]

    def calc(self, data, x, u=None):
        if u is None:
            u = self.unone
        v, w = m2a(u)
        px, py, theta = m2a(x)
        c, s = np.cos(theta), np.sin(theta)
        # Rollout the dynamics
        data.xnext = a2m([px + c * v * self.dt, py + s * v * self.dt, theta + w * self.dt])
        # Compute the cost value
        data.costResiduals = np.vstack([self.costWeights[0] * x, self.costWeights[1] * u])
        data.cost = .5 * sum(m2a(data.costResiduals)**2)

    def calcDiff(self, data, x, u=None, recalc=True):
        if u is None:
            u = self.unone
        if recalc:
            self.calc(data, x, u)
        v, w = m2a(u)
        px, py, theta = m2a(x)
        # Cost derivatives
        data.Lx = a2m(m2a(x) * ([self.costWeights[0]**2] * self.nx))
        data.Lu = a2m(m2a(u) * ([self.costWeights[1]**2] * self.nu))
        data.Lxx = np.diag([self.costWeights[0]**2] * self.nx)
        data.Luu = np.diag([self.costWeights[1]**2] * self.nu)
        # Dynamic derivatives
        c, s, dt = np.cos(theta), np.sin(theta), self.dt
        v, w = m2a(u)
        data.Fx = np.matrix([[1, 0, -s * v * dt], [0, 1, c * v * dt], [0, 0, 1]])
        data.Fu = np.matrix([[c * self.dt, 0], [s * self.dt, 0], [0, self.dt]])


class DDPDerived(crocoddyl.SolverAbstract):
    def __init__(self, shootingProblem):
        crocoddyl.SolverAbstract.__init__(self, shootingProblem)
        self.allocateData()  # TODO remove it?

        self.isFeasible = False  # Change it to true if you know that datas[t].xnext = xs[t+1]
        self.alphas = [2**(-n) for n in range(10)]
        self.th_grad = 1e-12

        self.x_reg = 0
        self.u_reg = 0
        self.regFactor = 10
        self.regMax = 1e9
        self.regMin = 1e-9
        self.th_step = .5

    def calc(self):
        self.cost = self.problem.calcDiff(self.xs, self.us)
        if not self.isFeasible:
            # Gap store the state defect from the guess to feasible (rollout) trajectory, i.e.
            #   gap = x_rollout [-] x_guess = DIFF(x_guess, x_rollout)
            self.gaps[0] = self.problem.runningModels[0].State.diff(self.xs[0], self.problem.initialState)
            for i, (m, d, x) in enumerate(zip(self.problem.runningModels, self.problem.runningDatas, self.xs[1:])):
                self.gaps[i + 1] = m.State.diff(x, d.xnext)

        return self.cost

    def computeDirection(self, recalc=True):
        if recalc:
            self.calc()
        self.backwardPass()
        return [np.nan] * (self.problem.T + 1), self.k, self.Vx

    def stoppingCriteria(self):
        return sum([np.asscalar(q.T * q) for q in self.Qu])

    def expectedImprovement(self):
        d1 = sum([np.asscalar(q.T * k) for q, k in zip(self.Qu, self.k)])
        d2 = sum([-np.asscalar(k.T * q * k) for q, k in zip(self.Quu, self.k)])
        return np.matrix([d1, d2]).T

    def tryStep(self, stepLength=1):
        self.forwardPass(stepLength)
        return self.cost - self.cost_try

    def solve(self, init_xs=[], init_us=[], maxiter=100, isFeasible=False, regInit=None):
        self.setCandidate(init_xs, init_us, isFeasible)
        self.x_reg = regInit if regInit is not None else self.regMin
        self.u_reg = regInit if regInit is not None else self.regMin
        self.wasFeasible = False
        for i in range(maxiter):
            recalc = True
            while True:
                try:
                    self.computeDirection(recalc=recalc)
                except ArithmeticError:
                    recalc = False
                    self.increaseRegularization()
                    if self.x_reg == self.regMax:
                        return self.xs, self.us, False
                    else:
                        continue
                break
            d = self.expectedImprovement()
            d1, d2 = np.asscalar(d[0]), np.asscalar(d[1])

            for a in self.alphas:
                try:
                    self.dV = self.tryStep(a)
                except ArithmeticError:
                    continue
                self.dV_exp = a * (d1 + .5 * d2 * a)
                if d1 < self.th_grad or not self.isFeasible or self.dV > self.th_acceptStep * self.dV_exp:
                    # Accept step
                    self.wasFeasible = self.isFeasible
                    self.setCandidate(self.xs_try, self.us_try, True)
                    self.cost = self.cost_try
                    break
            if a > self.th_step:
                self.decreaseRegularization()
            if a == self.alphas[-1]:
                self.increaseRegularization()
                if self.x_reg == self.regMax:
                    return self.xs, self.us, False
            self.stepLength = a
            self.iter = i
            self.stop = self.stoppingCriteria()
            # TODO @Carlos bind the callbacks
            # if self.callback is not None:
            #     [c(self) for c in self.callback]

            if self.wasFeasible and self.stop < self.th_stop:
                return self.xs, self.us, True

        # Warning: no convergence in max iterations
        return self.xs, self.us, False

    def increaseRegularization(self):
        self.x_reg *= self.regFactor
        if self.x_reg > self.regMax:
            self.x_reg = self.regMax
        self.u_reg = self.x_reg

    def decreaseRegularization(self):
        self.x_reg /= self.regFactor
        if self.x_reg < self.regMin:
            self.x_reg = self.regMin
        self.u_reg = self.x_reg

    # DDP Specific
    def allocateData(self):
        self.Vxx = [a2m(np.zeros([m.ndx, m.ndx])) for m in self.models()]
        self.Vx = [a2m(np.zeros([m.ndx])) for m in self.models()]

        self.Q = [a2m(np.zeros([m.ndx + m.nu, m.ndx + m.nu])) for m in self.problem.runningModels]
        self.q = [a2m(np.zeros([m.ndx + m.nu])) for m in self.problem.runningModels]
        self.Qxx = [Q[:m.ndx, :m.ndx] for m, Q in zip(self.problem.runningModels, self.Q)]
        self.Qxu = [Q[:m.ndx, m.ndx:] for m, Q in zip(self.problem.runningModels, self.Q)]
        self.Qux = [Qxu.T for m, Qxu in zip(self.problem.runningModels, self.Qxu)]
        self.Quu = [Q[m.ndx:, m.ndx:] for m, Q in zip(self.problem.runningModels, self.Q)]
        self.Qx = [q[:m.ndx] for m, q in zip(self.problem.runningModels, self.q)]
        self.Qu = [q[m.ndx:] for m, q in zip(self.problem.runningModels, self.q)]

        self.K = [np.matrix(np.zeros([m.nu, m.ndx])) for m in self.problem.runningModels]
        self.k = [a2m(np.zeros([m.nu])) for m in self.problem.runningModels]

        self.xs_try = [self.problem.initialState] + [np.nan * self.problem.initialState] * self.problem.T
        self.us_try = [np.nan] * self.problem.T
        self.gaps = [a2m(np.zeros(self.problem.runningModels[0].ndx))
                     ] + [a2m(np.zeros(m.ndx)) for m in self.problem.runningModels]

    def backwardPass(self):
        self.Vx[-1][:] = self.problem.terminalData.Lx
        self.Vxx[-1][:, :] = self.problem.terminalData.Lxx

        if self.x_reg != 0:
            ndx = self.problem.terminalModel.ndx
            self.Vxx[-1][range(ndx), range(ndx)] += self.x_reg

        for t, (model, data) in rev_enumerate(zip(self.problem.runningModels, self.problem.runningDatas)):
            self.Qxx[t][:, :] = data.Lxx + data.Fx.T * self.Vxx[t + 1] * data.Fx
            self.Qxu[t][:, :] = data.Lxu + data.Fx.T * self.Vxx[t + 1] * data.Fu
            self.Quu[t][:, :] = data.Luu + data.Fu.T * self.Vxx[t + 1] * data.Fu
            self.Qx[t][:] = data.Lx + data.Fx.T * self.Vx[t + 1]
            self.Qu[t][:] = data.Lu + data.Fu.T * self.Vx[t + 1]
            if not self.isFeasible:
                # In case the xt+1 are not f(xt,ut) i.e warm start not obtained from roll-out.
                relinearization = self.Vxx[t + 1] * self.gaps[t + 1]
                self.Qx[t][:] += data.Fx.T * relinearization
                self.Qu[t][:] += data.Fu.T * relinearization

            if self.u_reg != 0:
                self.Quu[t][range(model.nu), range(model.nu)] += self.u_reg

            self.computeGains(t)

            if self.u_reg == 0:
                self.Vx[t][:] = self.Qx[t] - self.K[t].T * self.Qu[t]
            else:
                self.Vx[t][:] = self.Qx[t] - 2 * self.K[t].T * self.Qu[t] + self.K[t].T * self.Quu[t] * self.k[t]
            self.Vxx[t][:, :] = self.Qxx[t] - self.Qxu[t] * self.K[t]
            self.Vxx[t][:, :] = 0.5 * (self.Vxx[t][:, :] + self.Vxx[t][:, :].T)  # ensure symmetric

            if self.x_reg != 0:
                self.Vxx[t][range(model.ndx), range(model.ndx)] += self.x_reg
            raiseIfNan(self.Vxx[t], ArithmeticError('backward error'))
            raiseIfNan(self.Vx[t], ArithmeticError('backward error'))

    def computeGains(self, t):
        try:
            if self.Quu[t].shape[0] > 0:
                Lb = scl.cho_factor(self.Quu[t])
                self.K[t][:, :] = scl.cho_solve(Lb, self.Qux[t])
                self.k[t][:] = scl.cho_solve(Lb, self.Qu[t])
            else:
                pass
        except scl.LinAlgError:
            raise ArithmeticError('backward error')

    def forwardPass(self, stepLength, warning='ignore'):
        # Argument warning is also introduce for debug: by default, it masks the numpy warnings
        #    that can be reactivated during debug.
        xs, us = self.xs, self.us
        xtry, utry = self.xs_try, self.us_try
        ctry = 0
        for t, (m, d) in enumerate(zip(self.problem.runningModels, self.problem.runningDatas)):
            utry[t] = us[t] - self.k[t] * stepLength - np.dot(self.K[t], m.State.diff(xs[t], xtry[t]))
            with np.warnings.catch_warnings():
                np.warnings.simplefilter(warning)
                m.calc(d, xtry[t], utry[t])
                xnext, cost = d.xnext, d.cost
            xtry[t + 1] = xnext.copy()  # not sure copy helpful here.
            ctry += cost
            raiseIfNan([ctry, cost], ArithmeticError('forward error'))
            raiseIfNan(xtry[t + 1], ArithmeticError('forward error'))
        with np.warnings.catch_warnings():
            np.warnings.simplefilter(warning)
            self.problem.terminalModel.calc(self.problem.terminalData, xtry[-1])
            ctry += self.problem.terminalData.cost
        raiseIfNan(ctry, ArithmeticError('forward error'))
        self.cost_try = ctry
        return xtry, utry, ctry
