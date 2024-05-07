from Module.Route_Mode.Function import *
import math
import numpy as np


class Control(object):
    def __init__(self, model):
        self.Model = model  # Fish_Model(0, 0, 0, 1, 0.5, 0.1)
        self.LQR = LQR(q=30, r=5, n=100, esp=1e-4)

    def Set_Model(self, v, L, dt):
        self.Model.v = v
        self.Model.L = L
        self.Model.dt = dt

    def normalize_angle(self, angle):
        """
        Normalize an angle to [-pi, pi].

        :param angle: (float)
        :return: (float) Angle in radian in [-pi, pi]
        copied from https://atsushisakai.github.io/PythonRobotics/modules/path_tracking/stanley_control/stanley_control.html
        """
        while angle > np.pi:
            angle -= 2.0 * np.pi

        while angle < -np.pi:
            angle += 2.0 * np.pi

        return angle

    def run(self, path, d_t) -> np.array:
        length = len(path)
        new_path = np.zeros((length, 4))
        new_path[:, :2] = path
        for i in range(length):
            if i == 0:
                dx = path[i + 1, 0] - path[i, 0]
                dy = path[i + 1, 1] - path[i, 1]
                ddx = path[2, 0] + path[0, 0] - path[1, 0]
                ddy = path[2, 1] + path[0, 1] - 2 * path[1, 1]
            elif i == (length - 1):
                dx = path[i, 0] - path[i - 1, 0]
                dy = path[i, 1] - path[i - 1, 1]
                ddx = path[i, 0] + path[i - 2, 0] - 2 * path[i - 1, 0]
                ddy = path[i, 1] + path[i - 2, 1] - 2 * path[i - 1, 1]
            else:
                dx = path[i + 1, 0] - path[i, 0]
                dy = path[i + 1, 1] - path[i, 1]
                ddx = path[i + 1, 0] + path[i - 1, 0] - 2 * path[i, 0]
                ddy = path[i + 1, 1] + path[i - 1, 1] - 2 * path[i, 1]
            new_path[i, 2] = math.atan2(dy, dx)  # yaw
            # 计算曲率:设曲线r(t) =(x(t),y(t)),则曲率k=(x'y" - x"y')/((x')^2 + (y')^2)^(3/2).
            # 参考：https://blog.csdn.net/weixin_46627433/article/details/123403726
            new_path[i, 3] = (ddy * dx - ddx * dy) / ((dx ** 2 + dy ** 2) ** (3 / 2))  # 曲率k计算

        alpha = math.atan2(
            path[1, 1] - path[0, 1], path[1, 0] - path[0, 0])
        self.Model.x, self.Model.y, self.Model.psi = path[0, 0], path[0, 1], alpha
        output = [(self.Model.x, self.Model.y)]
        distance, ind, cur_ind = np.inf, 1, 1
        m = 500
        while True:
            if m == 0:
                break
            print(ind, cur_ind, length, distance)
            robot_state = (self.Model.x, self.Model.y, self.Model.psi, self.Model.v)
            distance = np.linalg.norm(new_path[ind, :2] - robot_state[:2])

            d_x = [new_path[i, 0] - robot_state[0] for i in range(length)]
            d_y = [new_path[i, 1] - robot_state[1] for i in range(length)]
            d = [np.sqrt(d_x[i] ** 2 + d_y[i] ** 2) for i in range(len(d_x))]
            ind = max(np.argmin(d), ind)  # 最近目标点索引
            if ind == length - 1 and distance < d_t:
                break
            # elif ind != length - 1 and distance < d_t:
            #     ind += 1
            if cur_ind == ind:
                m -= 1
            else:
                cur_ind = ind
                m = 500
            yaw = new_path[ind, 2]
            k = new_path[ind, 3]

            print(yaw, k)
            # angle = self.normalize_angle(yaw - math.atan2(
            #     new_path[ind, 1] - robot_state[1], new_path[ind, 0] - robot_state[0]))
            # e = distance  # 误差
            # if angle < 0:
            #     e *= -1
            ref_delta = math.atan2(self.Model.L * k, 1)  # 车道曲率*车辆轴距等于车辆从当前位置行驶到前方车道曲率所示位置所需要的车轮转角斜率
            self.LQR.A, self.LQR.B = self.Model.state_space(ref_delta, yaw)
            x = robot_state[0:3] - new_path[ind, 0:3]
            delta = self.LQR.cal_output(x)
            delta = delta + ref_delta

            self.Model.update_state(0, delta)  # 加速度设为0，恒速
            output.append((self.Model.x, self.Model.y))
        return output

