from Module.Route_Mode.Function import *
import math
import numpy as np


class Control(object):
    def __init__(self, model):
        self.Model = model  # Fish_Model(0, 0, 0, 1, 0.5, 0.1)

    def Set_Model(self, v, L, dt):
        self.Model.v = v
        self.Model.L = L
        self.Model.dt = dt

    def Pure_Pursuit_Control(self, robot_state, current_ref_point, l_d):
        """pure pursuit

        Args:
            robot_state (_type_): 车辆位置
            current_ref_point (_type_): 当前参考路点
            l_d：前视距离
        return:返回前轮转向角delta
        """
        alpha = math.atan2(current_ref_point[1] - robot_state[1],
                           current_ref_point[0] - robot_state[0]) - self.Model.psi
        delta = math.atan2(2 * self.Model.L * np.sin(alpha), l_d)
        return delta

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
                if error >= 1/self.Model.dt * 1000:
                    break

            distance = np.linalg.norm(path[ind] - robot_state)
            delta_f = self.Pure_Pursuit_Control(robot_state, path[ind], distance)
            self.Model.update_state(0, delta_f)  # 加速度设为0
            output.append((self.Model.x, self.Model.y))
        return output
