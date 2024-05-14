# coding:utf-8
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5 import QtCore, QtWidgets, QtGui
import matplotlib.pyplot as plt
import numpy as np
import sys
import matplotlib

# matplotlib.use('Qt5Agg')


LB = 0.45                   # 鱼体长，m为单位
LT = 0.20                   # 鱼尾长，m为单位
steer_num = 2               # 舵机数/关节数
lamb = 1.5 * LB             # 鱼体波波长，大于等于鱼体长为佳
k = 2 * np.pi / lamb        # 鱼体波波数


# ============= 鱼体波函数 =============
# input
#              x：到鱼头的距离
#              t：经过的时间
#              c1：鱼体包络线的一阶参数
#              c2：鱼体包络线的二阶参数
# output
#              yb：x处鱼体横向位移（波幅）
# ====================================
# 注：y峰值即尾鳍摆动轴波幅为0.075~0.1倍体长LB

# 双侧摆动，用于双尾同步动作
def wave_function(x, t, c1, c2, T, sym=1):
    ome = 2 * np.pi / T
    yb = sym * (c1 * x + c2 * np.power(x, 2)) * np.sin(k * x + ome * t)
    return yb


# # 单侧摆动，用于双尾对称动作
# def wave_function_single(x, t, c1, c2, ome, sym=1):
#     yb = sym * (c1 * x + c2 * np.power(x, 2)) * np.abs(np.sin(k * x + ome * t))
#     return yb


# 计算转动角度
def angle_calculation(x, y, angle_0):
    grad = np.zeros((x.shape[0]-1,))
    for i in range(grad.shape[0]):
        grad[i] = (y[i+1] - y[i]) / (x[i+1] - x[i])
    angle = np.arctan(grad) * 180 / np.pi
    delta_angle = angle - angle_0
    return delta_angle, angle


class Wave(QtWidgets.QDialog):
    def __init__(self, mode="stop", c1_amp=1.7, T=3, parent=None):
        # 父类初始化方法
        super(Wave, self).__init__(parent)
        self.Close = False
        self.c1 = 0.23            # 鱼体波拟合曲线一次项系数，固定
        self.c2 = 0.2             # 鱼体波拟合曲线二次项系数，固定
        self.mode = mode
        self.TC = 0.1             # 控制周期，s为单位
        # c1_amp
        if 1.5 >= c1_amp >= 0.7:
            self.c1_amp = c1_amp
        elif c1_amp < 0.7:
            self.c1_amp = 0.7
        else:
            self.c1_amp = 1.5
        # symbol
        self.symbol = 1
        # T
        if T < 1.8:
            self.T = 1.8
        else:
            self.T = T
        # 几个QWidgets
        self.figure = Figure()
        self.ax = self.figure.add_axes([0, 0, 1, 1])
        self.canvas = FigureCanvas(self.figure)
        self.figure.set_alpha(1)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.thread = QtCore.QThread(self)
        self.thread.run = self.Plot
        self.thread.start()

        self.x = np.array([0., 0.13, LT])
        self.l_angle_0 = np.array((self.x.shape[0]-1, ))
        self.l_delta_angle = np.array((self.x.shape[0]-1, ))
        self.r_angle_0 = np.array((self.x.shape[0]-1, ))
        self.r_delta_angle = np.array((self.x.shape[0]-1, ))

    def Plot(self):
        while not self.Close:
            if self.mode == 'sync_front':  # 同步
                c1_r, c1_l = self.c1, self.c1
                self.symbol = 1
            elif self.mode == 'async_front':  # 对称
                c1_r, c1_l = self.c1, self.c1
                self.symbol = -1
            elif self.mode == 'left':
                c1_r, c1_l = self.c1 * self.c1_amp, self.c1 / self.c1_amp
                self.symbol = 1
            elif self.mode == 'right':
                c1_r, c1_l = self.c1 / self.c1_amp, self.c1 * self.c1_amp
                self.symbol = 1
            else:
                c1_l, c1_r = 0, 0
                self.symbol = 1
            for t in np.linspace(start=0, stop=self.T, num=int(self.T/self.TC)):
                y1 = (wave_function(self.x, t, c1_r, self.c2, self.T, 1) if c1_r != 0 else np.zeros_like(self.x)) + 0.07
                y2 = (wave_function(self.x, t, c1_l, self.c2, self.T, self.symbol) if c1_l != 0 else np.zeros_like(self.x)) - 0.07
                # 计算角度
                self.r_delta_angle, self.r_angle_0 = angle_calculation(self.x, y1, self.r_angle_0)
                self.l_delta_angle, self.l_angle_0 = angle_calculation(self.x, y2, self.l_angle_0)
                self.ax.clear()
                self.ax.plot(self.x, y1, color='#FF4500')
                self.ax.plot(self.x, y2, color='#FF4500')
                self.ax.set_ylim(-LB, LB)
                self.ax.set_xlim(0, LB/2)
                self.ax.set_xticks([])
                self.ax.set_yticks([])
                self.ax.relim()
                self.ax.autoscale_view()
                self.canvas.draw()
                plt.pause(self.TC)


mode_list = ['sync_front', 'async_front', 'left', 'right', 'stop']


# 运行程序
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # 设定参数
    c1_amp = 1.5                # 调整转弯半径，0.7-1.5
    T = 1.8                       # 调整前进速度，>1.8
    mode = mode_list[2]
    main_window = Wave(mode, c1_amp, T)
    main_window.show()
    app.exec()

