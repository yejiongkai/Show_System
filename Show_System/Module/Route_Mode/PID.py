from Module.Route_Mode.Function import *
import math
import numpy as np


class Control(object):
    def __init__(self, model):
        self.Model = model  # Fish_Model(0, 0, 0, 1, 0.5, 0.1)
        self.PID = PID_posi_2(k=[3, 0.01, 20], target=0, upper=np.pi/6, lower=-np.pi/6)

    def Set_PID(self, k=(5, 0, 0), target=1.0, upper=1.0, lower=-1.0):
        self.PID.set_k(k)
        self.PID.set_target(target)
        self.PID.setbound(upper, lower)

    def Set_Model(self, v, L, dt):
        self.Model.v = v
        self.Model.L = L
        self.Model.dt = dt

    def run(self, path, d_t) -> np.array:
        alpha = math.atan2(
            path[1, 1] - path[0, 1], path[1, 0] - path[0, 0])
        self.Model.x, self.Model.y, self.Model.psi = path[0, 0], path[0, 1], alpha
        output = [(self.Model.x, self.Model.y)]
        length = len(path)
        distance, ind = np.inf, 1
        error = 0
        while True:
            robot_state = (self.Model.x, self.Model.y)
            if ind == length - 1 and distance < d_t:
                break
            elif ind != length - 1 and distance < d_t:
                ind += 1
                error = 0
            else:
                error += 1
                if error >= 1/(self.Model.dt*self.Model.v) * 100:
                    break

            distance = np.linalg.norm(path[ind] - robot_state)
            alpha = math.atan2(
                path[ind, 1] - robot_state[1], path[ind, 0] - robot_state[0])
            # l_d = k*ugv.v+c  # 前视距离
            theta_e = alpha - self.Model.psi
            # e_y = -distance * math.sin(theta_e)  # 与博客中公式相比多了个负号，我目前还不是太理解，暂时先放着
            e_y = -distance*np.sign(math.sin(theta_e))  # 第二种误差表示
            # e_y = robot_state[1]-refer_path[ind, 1] #第三种误差表示
            delta_f = self.PID.cal_output(e_y)
            # print(e_y)
            # print(alpha)
            self.Model.update_state(0, delta_f)  # 加速度设为0
            output.append((self.Model.x, self.Model.y))
        return output
