# coding:utf-8

# 导入matplotlib模块并使用Qt5Agg
import matplotlib

matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5 import QtCore, QtWidgets, QtGui
import matplotlib.pyplot as plt
import numpy as np
import sys


class Wave(QtWidgets.QDialog):
    def __init__(self, parent=None):
        # 父类初始化方法
        super(Wave, self).__init__(parent)
        self.Close = False
        self.A, self.k = 0, 0
        # 几个QWidgets
        self.figure = Figure()
        self.ax = self.figure.add_axes([0.1, 0.1, 0.8, 0.8])
        self.canvas = FigureCanvas(self.figure)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.thread = QtCore.QThread(self)
        self.thread.run = self.Plot
        self.thread.start()

    def Plot(self):
        fun = lambda a, k, x, t: (0.5 * (-k) * np.power(x, 2)) * np.sin(t * a)
        while not self.Close:
            if self.k == 0:
                for t in np.linspace(0, (np.pi * 2 / self.A) if self.A != 0 else 1, (100 // self.A) if self.A != 0 else 1):
                    x = np.linspace(0, np.pi * 20, 50)
                    # p_x = np.linspace(0, np.pi * 20, 4)
                    self.ax.clear()
                    self.ax.plot(x, fun(self.A, 5, x, t))
                    # self.ax.plot(p_x, fun(self.A, 5, p_x, t), linestyle='-')
                    self.ax.set_ylim(-18000, 18000)
                    self.ax.set_xlim(0, 20 * np.pi + 2)
                    self.ax.set_xticks([])
                    self.ax.set_yticks([])
                    self.ax.relim()
                    self.ax.autoscale_view()
                    self.canvas.draw()
                    plt.pause(0.01)

            else:
                for t in np.linspace(0, (np.pi / self.A) if self.A != 0 else 1, (50//self.A) if self.A != 0 else 1):
                    x = np.linspace(0, np.pi * 20, 50)
                    # p_x = np.linspace(0, np.pi * 20, 4)
                    self.ax.clear()
                    self.ax.plot(x, fun(self.A, self.k, x, t))
                    # self.ax.plot(p_x, fun(self.A, self.k, p_x, t), linestyle='--')
                    self.ax.set_ylim(-18000, 18000)
                    self.ax.set_xlim(0, 20 * np.pi + 2)
                    self.ax.set_xticks([])
                    self.ax.set_yticks([])
                    self.ax.relim()
                    self.ax.autoscale_view()
                    self.canvas.draw()
                    plt.pause(0.01)


# 运行程序
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    main_window = Wave()
    main_window.A = 2
    main_window.k = 10
    main_window.show()
    app.exec()
