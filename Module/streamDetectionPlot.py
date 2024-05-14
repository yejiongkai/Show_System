import numpy as np
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt


class streamDetectionPlot(FigureCanvas):
    # Initial the figure parameters
    def __init__(self, X, Y, Z, Role, V):
        # Turn the interactive mode on
        # initial the figure
        self.fig = Figure(figsize=(15, 8), dpi=80)
        # self.fig = plt.figure(figsize=(15, 8), num=1)
        self.fig.subplots_adjust(bottom=-0.1, top=1.1, left=0, right=1)
        # plt.ion()
        # initial the plot variable
        self.pause = False
        self.num = 80
        self.fontsize = 12
        self.x = X.copy()
        self.y = Y.copy()
        self.z = Z.copy()
        self.v = V.copy()
        self.role = Role.copy()
        if Role[0] == 90:
            self.k = 0
        elif Role[0] == 0 or Role[0] == 360:
            self.k = None
        else:
            self.k = 1 / np.tan(Role[0] * np.pi / 180)
        self.intercept = Y[0] - self.k * X[0] if self.k is not None else X[0]
        self.sea_height = Z[0]
        self.sea_visible = True
        self.highlightListTurnOn = True
        self.xRange = [0, 1]
        self.yRange = [0, 1]
        self.zRange = [0, 1]
        self.tableValue = [[0, 0]]

        # fig.subplots_adjust(left=-0.3, right=0.8, bottom=0.1, top=0.9)
        self.loadingGraph = self.fig.add_subplot(111, projection='3d')
        self.initPlot()
        super(streamDetectionPlot, self).__init__(self.fig)

    # define the initial plot method
    def initPlot(self):
        # initial two lines
        self.loadingGraph.grid(True)

        # Set the title
        # self.loadingGraph.set_title("运动轨迹(东北天坐标系)")

        # set the x/y label of the first graph
        # self.loadingGraph.set_xlabel("正东")
        # self.loadingGraph.set_ylabel("正北")
        # self.loadingGraph.set_zlabel("天")

        self.cur_label = "x:{:.5f}\ny:{:.5f}\nz:{:.5f}\nv:{:.5f}".format(self.x[-1], self.y[-1], self.z[-1],
                                                                         np.linalg.norm(self.v[-1]))
        self.last_label = self.cur_label
        self.last_text = self.loadingGraph.text(self.x[-1], self.y[-1], self.z[-1], self.cur_label, fontsize=self.fontsize,
                                                horizontalalignment='right', verticalalignment='bottom')
        self.cur_text = self.loadingGraph.text(self.x[-1], self.y[-1], self.z[-1], self.cur_label, fontsize=self.fontsize,
                                               horizontalalignment='right', verticalalignment='bottom')

        self.Trace_Line, = self.loadingGraph.plot(self.x, self.y, self.z, color="red", label="LoadingValue")
        self.Begin_Cur_Line, = self.loadingGraph.plot(self.x, self.y, self.z, color="blue", label="LoadingValue")
        self.Speed_Quiver = self.loadingGraph.quiver(self.x[-1], self.y[-1], self.z[-1], self.v[-1][0], self.v[-1][1],
                                                     self.v[-1][2], color='green')

        self.cur_dot = self.loadingGraph.scatter(self.x[-1], self.y[-1], self.z[-1], color='green')
        self.last_dot = self.loadingGraph.scatter(self.x[-1], self.y[-1], self.z[-1], color='green')

        x_min, x_max = self.loadingGraph.get_xlim()
        y_min, y_max = self.loadingGraph.get_ylim()
        z_min, z_max = self.loadingGraph.get_zlim()
        self.X = np.linspace(x_min, x_max, 2)
        self.Y = np.linspace(y_min, y_max, 2)
        self.Z = np.linspace(z_min, z_max, 2)

        # if self.k is not None:
        #     if abs(self.k) > 1:
        #         self.Y_, self.Z_ = np.meshgrid(self.Y, self.Z)
        #         self.Surface = self.loadingGraph.plot_surface(X=(self.Y_ - self.intercept) / self.k, Y=self.Y_,
        #                                                       Z=self.Z_, color='yellow', alpha=0.5)
        #     else:
        #         self.X_, self.Z_ = np.meshgrid(self.X, self.Z)
        #         self.Surface = self.loadingGraph.plot_surface(X=self.X_, Y=self.X_ * self.k + self.intercept,
        #                                                       Z=self.Z_,
        #                                                       color='yellow', alpha=0.5)
        # else:
        #     self.Y_, self.Z_ = np.meshgrid(self.Y, self.Z)
        #     self.Surface = self.loadingGraph.plot_surface(X=self.intercept, Y=self.Y_, Z=self.Z_,
        #                                                   color='yellow', alpha=0.5)

        self.X_, self.Y_ = np.meshgrid(self.X, self.Y)
        self.Sea = self.loadingGraph.plot_surface(X=self.X_, Y=self.Y_, Z=np.full_like(self.X_ , self.sea_height),
                                                  color='blue', alpha=0.3)
        # self.Sea_down = self.loadingGraph.plot_surface(X=self.X_, Y=self.Y_, Z=np.full_like(self.X_ , z_min),
        #                                           color='blue', alpha=0.3)
        # self.Sea_Forward = self.loadingGraph.plot_surface(X=self.X_, Y=self.Y_, Z=np.full_like(self.Y_ , x_min),
        #                                           color='blue', alpha=0.3)
        # self.Sea_Back = self.loadingGraph.plot_surface(X=self.X_, Y=self.Y_, Z=np.full_like(self.Y_, x_max),
        #                                                   color='blue', alpha=0.3)
        # self.Sea_Left = self.loadingGraph.plot_surface(X=self.X_, Y=self.Y_, Z=np.full_like(self.Y_, y_min),
        #                                                   color='blue', alpha=0.3)
        # self.Sea_Right = self.loadingGraph.plot_surface(X=self.X_, Y=self.Y_, Z=np.full_like(self.Y_, y_max),
        #                                                color='blue', alpha=0.3)

    # define the output method
    def DetectionPlot(self, x, y, z, role, v):
        if self.pause:
            return
        # Pause Button setting
        # update the plot value of the graph
        self.x = x.copy()
        self.y = y.copy()
        self.z = z.copy()
        self.role = role.copy()
        self.v = v.copy()
        num = self.num

        # -------------------运动轨迹和首位线----------------#

        self.Trace_Line.set_data_3d(self.x, self.y, self.z)
        self.Begin_Cur_Line.set_data_3d([self.x[0], self.x[-1]], [self.y[0], self.y[-1]], [self.z[0], self.z[-1]])

        # ---------------------标签和点----------------------#

        # self.text.remove()
        # cur_label = "x:{:.5f}\ny:{:.5f}\nz:{:.5f}\nv:{:.5f}".format(self.x[-1], self.y[-1], self.z[-1],
        #                                                             np.linalg.norm(self.v[-1]))
        # self.text = self.loadingGraph.text(self.x[-1], self.y[-1], self.z[-1], cur_label, fontsize=8,
        #                                    horizontalalignment='right', verticalalignment='bottom')
        self.cur_label = "x:{:.5f}\ny:{:.5f}\nz:{:.5f}\nv:{:.5f}".format(self.x[-1], self.y[-1], self.z[-1],
                                                                         np.linalg.norm(self.v[-1]))
        self.cur_text.set(x=self.x[-1], y=self.y[-1], z=self.z[-1], text=self.cur_label)
        self.cur_dot.remove()
        self.cur_dot = self.loadingGraph.scatter(self.x[-1], self.y[-1], self.z[-1], color='green')

        if len(self.x) > self.num:
            self.last_label = "x:{:.5f}\ny:{:.5f}\nz:{:.5f}\nv:{:.5f}".format(self.x[-num - 1], self.y[-num - 1],
                                                                              self.z[-num - 1],
                                                                              np.linalg.norm(self.v[-num - 1]))
            self.last_text.set(x=self.x[-num - 1], y=self.y[-num - 1], z=self.z[-num - 1], text=self.last_label)
            self.last_dot.remove()
            self.last_dot = self.loadingGraph.scatter(self.x[-num - 1], self.y[-num - 1], self.z[-num - 1],
                                                      color='green')
        else:
            self.last_label = "x:{:.5f}\ny:{:.5f}\nz:{:.5f}\nv:{:.5f}".format(self.x[0], self.y[0], self.z[0],
                                                                              np.linalg.norm(self.v[0]))
            self.last_text.set(x=self.x[0], y=self.y[0], z=self.z[0], text=self.last_label)
            self.last_dot.remove()
            self.last_dot = self.loadingGraph.scatter(self.x[0], self.y[0], self.z[0], color='green')

        # --------------------速度箭头-------------------#
        self.Speed_Quiver.remove()
        self.Speed_Quiver = self.loadingGraph.quiver(self.x[-1], self.y[-1], self.z[-1], self.v[-1][0],
                                                     self.v[-1][1], self.v[-1][2], color='green')

        # ----------------------平面----------------——#

        # self.Surface.remove()
        x_min, x_max = self.loadingGraph.get_xlim()
        y_min, y_max = self.loadingGraph.get_ylim()
        z_min, z_max = self.loadingGraph.get_zlim()
        self.X = np.linspace(x_min, x_max, 10)
        self.Y = np.linspace(y_min, y_max, 10)
        self.Z = np.linspace(z_min, z_max, 10)

        # if self.k is not None:
        #     if abs(self.k) > 1:
        #         self.Y_, self.Z_ = np.meshgrid(self.Y, self.Z)
        #         self.Surface = self.loadingGraph.plot_surface(X=(self.Y_ - self.intercept) / self.k, Y=self.Y_,
        #                                                       Z=self.Z_, color='yellow', alpha=0.5, rstride=5,
        #                                                       cstride=5)
        #     else:
        #         self.X_, self.Z_ = np.meshgrid(self.X, self.Z)
        #         self.Surface = self.loadingGraph.plot_surface(X=self.X_, Y=self.X_ * self.k + self.intercept,
        #                                                       Z=self.Z_,
        #                                                       color='yellow', alpha=0.5, rstride=5, cstride=5)
        # else:
        #     self.Y_, self.Z_ = np.meshgrid(self.Y, self.Z)
        #     self.Surface = self.loadingGraph.plot_surface(X=self.intercept, Y=self.Y_, Z=self.Z_,
        #                                                   color='yellow', alpha=0.5, rstride=5, cstride=5)

        # if self.sea_visible:
        self.Sea.remove()
        self.X_, self.Y_ = np.meshgrid(self.X, self.Y)
        self.Sea = self.loadingGraph.plot_surface(X=self.X_, Y=self.Y_, Z=np.full_like(self.X_, self.sea_height),
                                                  color='blue', alpha=0.3, rstride=5, cstride=5)

        # --------------------自动调整区间--------------------#
        self.xRange = [min(self.x), max(self.x)]  # datetime style
        self.yRange = [min(self.y), max(self.y)]
        self.zRange = [min(self.z), max(self.z)]
        range = [min(self.xRange[0], self.yRange[0]), max(self.xRange[1], self.yRange[1])]
        # self.loadingGraph.set_ylim(
        #     min(self.yRange) - 10, max(self.yRange) + 10)
        # self.loadingGraph.set_xlim(
        #     min(self.xRange) - 10, max(self.xRange) + 10)
        self.loadingGraph.set_ylim(range[0] - 10, range[1] + 10)
        self.loadingGraph.set_xlim(range[0] - 10, range[1] + 10)
        self.loadingGraph.set_zlim(
            min(self.zRange) - 10, max(self.zRange) + 10)
        self.loadingGraph.relim()
        self.loadingGraph.autoscale_view()

        # plt.draw()
        # plt.pause(0.02)
        # plot pause 0.0001 second and then plot the next one.

    # Define the slider update function
    """
    def update(self, val):
        # self.sb = self.ssb.val
        self.loadingGraph.axis(
            [self.xmin_time, self.xmax_time, min(self.y), max(self.y)])
        fig.canvas.draw_idle()
    """

    # Define the pause button function
    def setpause(self, event):
        self.pause = not self.pause

    def setSea(self, event):
        if self.sea_visible is False:
            x_min, x_max = self.loadingGraph.get_xlim()
            y_min, y_max = self.loadingGraph.get_ylim()
            self.X = np.linspace(x_min, x_max, 10)
            self.Y = np.linspace(y_min, y_max, 10)
            self.X_, self.Y_ = np.meshgrid(self.X, self.Y)
            self.Sea = self.loadingGraph.plot_surface(X=self.X_, Y=self.Y_, Z=self.X_ * 0 + self.sea_height,
                                                      color='blue', alpha=0.3, rstride=5, cstride=5)
        else:
            self.Sea.remove()
        self.sea_visible = not self.sea_visible

    def mousePressEvent(self, event):
        self.pause = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.pause = False

    # Turn off the ion and show the plot.
    def close(self):
        pass
        # plt.ioff()
        # plt.show()