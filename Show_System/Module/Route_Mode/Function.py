import numpy as np
import math
from time import sleep
from time import time

'------------------ Control  -----------------'


# 位置式
class PID_posi:
    """位置式实现1
    """

    def __init__(self, kp, ki, kd, target, upper=1., lower=-1.):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.err = 0
        self.err_last = 0
        self.err_all = 0
        self.target = target
        self.upper = upper
        self.lower = lower
        self.value = 0

    def cal_output(self, state):
        self.err = self.target - state
        # self.err =state-self.target
        self.value = self.kp * self.err + self.ki * \
                     self.err_all + self.kd * (self.err - self.err_last)
        self.update()
        return self.value

    def update(self):
        self.err_last = self.err
        self.err_all = self.err_all + self.err
        if self.value > self.upper:
            self.value = self.upper
        elif self.value < self.lower:
            self.value = self.lower

    def auto_adjust(self, Kpc, Tc):
        self.kp = Kpc * 0.6
        self.ki = self.kp / (0.5 * Tc)
        self.kd = self.kp * (0.125 * Tc)
        return self.kp, self.ki, self.kd

    def set_pid(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd

    def reset(self):
        self.err = 0
        self.err_last = 0
        self.err_all = 0

    def set_target(self, target):
        self.target = target


class PID_posi_2:
    """位置式实现2
    """

    def __init__(self, k=(1, 0, 0), target=1.0, upper=1.0, lower=-1.0):
        self.kp, self.ki, self.kd = k

        self.e = 0  # error
        self.pre_e = 0  # previous error
        self.sum_e = 0  # sum of error

        self.target = target  # target
        self.upper_bound = upper  # upper bound of output
        self.lower_bound = lower  # lower bound of output

    def set_target(self, target):
        self.target = target

    def set_k(self, k):
        self.kp, self.ki, self.kd = k

    def set_bound(self, upper, lower):
        self.upper_bound = upper
        self.lower_bound = lower

    def cal_output(self, state):  # calculate output
        self.e = self.target - state
        u = self.e * self.kp + self.sum_e * \
            self.ki + (self.e - self.pre_e) * self.kd
        if u < self.lower_bound:
            u = self.lower_bound
        elif u > self.upper_bound:
            u = self.upper_bound

        self.pre_e = self.e
        self.sum_e += self.e
        # print(self.sum_e)
        return u

    def reset(self):
        # self.kp = 0
        # self.ki = 0
        # self.kd = 0

        self.e = 0
        self.pre_e = 0
        self.sum_e = 0
        # self.target = 0

    def set_sum_e(self, sum_e):
        self.sum_e = sum_e


# 增量式
class PID_inc:
    """增量式实现
    """

    def __init__(self, k, target, upper=1., lower=-1.):
        self.kp, self.ki, self.kd = k
        self.err = 0
        self.err_last = 0
        self.err_ll = 0
        self.target = target
        self.upper = upper
        self.lower = lower
        self.value = 0
        self.inc = 0

    def cal_output(self, state):
        self.err = self.target - state
        self.inc = self.kp * (self.err - self.err_last) + self.ki * self.err + self.kd * (
                self.err - 2 * self.err_last + self.err_ll)
        self._update()
        return self.value

    def _update(self):
        self.err_ll = self.err_last
        self.err_last = self.err
        self.value = self.value + self.inc
        if self.value > self.upper:
            self.value = self.upper
        elif self.value < self.lower:
            self.value = self.lower

    def set_target(self, target):
        self.target = target

    def set_k(self, k):
        self.kp, self.ki, self.kd = k

    def set_bound(self, upper, lower):
        self.upper_bound = upper
        self.lower_bound = lower


class LQR:
    def __init__(self, q, r, n, esp):
        self.Q = np.eye(3)*q
        self.R = np.eye(2)*r
        self.N = n
        self.A = None
        self.B = None
        self.esp = esp

    def cal_output(self, x):
        P = self.cal_Ricatti()

        K = -np.linalg.pinv(self.R + self.B.T @ P @ self.B) @ self.B.T @ P @ self.A
        u = K @ x
        u_star = u.copy()  # u_star = [[v-ref_v,delta-ref_delta]]
        return u_star[0, 1]

    def cal_Ricatti(self):
        """解代数里卡提方程

        Args:
            A (_type_): 状态矩阵A
            B (_type_): 状态矩阵B
            Q (_type_): Q为半正定的状态加权矩阵, 通常取为对角阵；Q矩阵元素变大意味着希望跟踪偏差能够快速趋近于零；
            R (_type_): R为正定的控制加权矩阵，R矩阵元素变大意味着希望控制输入能够尽可能小。

        Returns:
            _type_: _description_
        """
        # 设置迭代初始值
        Qf = self.Q
        P = Qf
        # 循环迭代
        for t in range(self.N):
            P_ = self.Q + self.A.T @ P @ self.A - self.A.T @ P @ self.B @\
                 np.linalg.pinv(self.R + self.B.T @ P @ self.B) @ self.B.T @ P @ self.A
            if abs(P_ - P).max() < self.esp:
                break
            P = P_
        return P


'--------------------- Model --------------------'


class Fish_Model:
    """
    假设控制量为转向角delta_f和加速度a
    """

    def __init__(self, x, y, psi, v, L, dt):
        self.x = x
        self.y = y
        self.psi = psi
        self.v = v
        self.L = L
        # 实现是离散的模型
        self.dt = dt

    def update_state(self, a, delta_f):
        self.x = self.x + self.v * math.cos(self.psi) * self.dt
        self.y = self.y + self.v * math.sin(self.psi) * self.dt
        self.psi = self.psi + self.v / self.L * math.tan(delta_f) * self.dt
        self.v = self.v + a * self.dt

    def get_state(self):
        return self.x, self.y, self.psi, self.v

    def state_space(self, ref_delta, ref_yaw):
        """将模型离散化后的状态空间表达

        Args:
            delta (_type_): 参考输入

        Returns:
            _type_: _description_
        """
        A = np.matrix([
            [1.0, 0.0, -self.v * self.dt * math.sin(ref_yaw)],
            [0.0, 1.0, self.v * self.dt * math.cos(ref_yaw)],
            [0.0, 0.0, 1.0]])

        B = np.matrix([
            [self.dt * math.cos(ref_yaw), 0],
            [self.dt * math.sin(ref_yaw), 0],
            [self.dt * math.tan(ref_delta) / self.L, self.v * self.dt /
             (self.L * math.cos(ref_delta) * math.cos(ref_delta))]
        ])   # 对 V 和 ref_delta 求导
        return A, B
