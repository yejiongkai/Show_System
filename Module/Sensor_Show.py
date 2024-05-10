from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout, QHBoxLayout, QApplication
from PyQt5.QtCore import Qt
from collections import deque
import sys
from pyqtgraph import GraphicsLayoutWidget
import pyqtgraph as pg
import numpy as np


class Sensor(QDialog):

    def __init__(self, parent=None):
        super(Sensor, self).__init__(parent)
        self.acc_boxes = []
        self.gyro_boxes = []
        self.acc_max = 10
        self.tmps = deque(maxlen=20)
        self.SetupUI()

    def SetupUI(self):
        pg.setConfigOption('background', '#00000000')  # 设置背景色为黑色
        pg.setConfigOption('foreground', 'k')  # 设置前景色为白色
        pg.setConfigOptions(antialias=True)  # 开启抗锯齿效果
        # self.setStyleSheet('QWidget {background: palette(window);font-family: "Segoe UI";font-size: 18px;}')
        box_width = 0.1

        self.graph = GraphicsLayoutWidget(self)

        self.bottomAxis_list = [pg.AxisItem(orientation='bottom') for i in range(7)]
        axis_style = {'color': 'black', 'font-size': '12pt', 'showValues': 'false'}
        self.plot_temp = self.graph.addPlot(0, 0, 1, 6, axisItems={'bottom': self.bottomAxis_list[0]})
        self.plot_temp.setLabel('bottom', '温度', **axis_style)
        self.curve_temp = self.plot_temp.plot(pen=pg.mkPen(color='#0080aa', width=1))

        self.box_acc_x = pg.BarGraphItem(x=[0], height=[0], width=box_width, brush='g')
        self.box_acc_y = pg.BarGraphItem(x=[0], height=[0], width=box_width, brush='g')
        self.box_acc_z = pg.BarGraphItem(x=[0], height=[0], width=box_width, brush='g')
        self.box_gyro_x = pg.BarGraphItem(x=[0], height=[0], width=box_width, brush='r')
        self.box_gyro_y = pg.BarGraphItem(x=[0], height=[0], width=box_width, brush='r')
        self.box_gyro_z = pg.BarGraphItem(x=[0], height=[0], width=box_width, brush='r')

        self.acc_x = self.graph.addPlot(2, 0, 1, 1, axisItems={'bottom': self.bottomAxis_list[1]})
        self.acc_x_label = self.graph.addLabel("a_X", 1, 0, 1, 1)
        self.acc_y = self.graph.addPlot(2, 1, 1, 1, axisItems={'bottom': self.bottomAxis_list[2]})
        self.acc_y_label = self.graph.addLabel("a_Y", 1, 1, 1, 1)
        self.acc_z = self.graph.addPlot(2, 2, 1, 1, axisItems={'bottom': self.bottomAxis_list[3]})
        self.acc_z_label = self.graph.addLabel("a_Z", 1, 2, 1, 1)
        self.gyro_x = self.graph.addPlot(2, 3, 1, 1, axisItems={'bottom': self.bottomAxis_list[4]})
        self.gyro_x_label = self.graph.addLabel("g_X", 1, 3, 1, 1)
        self.gyro_y = self.graph.addPlot(2, 4, 1, 1, axisItems={'bottom': self.bottomAxis_list[5]})
        self.gyro_y_label = self.graph.addLabel("g_Y", 1, 4, 1, 1)
        self.gyro_z = self.graph.addPlot(2, 5, 1, 1, axisItems={'bottom': self.bottomAxis_list[6]})
        self.gyro_z_label = self.graph.addLabel("g_Z", 1, 5, 1, 1)
        self.acc_x.setLabel('bottom', 'a_X', **axis_style)
        self.acc_y.setLabel('bottom', 'a_Y', **axis_style)
        self.acc_z.setLabel('bottom', 'a_Z', **axis_style)
        self.gyro_x.setLabel('bottom', 'g_X', **axis_style)
        self.gyro_y.setLabel('bottom', 'g_Y', **axis_style)
        self.gyro_z.setLabel('bottom', 'g_Z', **axis_style)
        self.acc_x.addItem(self.box_acc_x)
        self.acc_y.addItem(self.box_acc_y)
        self.acc_z.addItem(self.box_acc_z)
        self.gyro_x.addItem(self.box_gyro_x)
        self.gyro_y.addItem(self.box_gyro_y)
        self.gyro_z.addItem(self.box_gyro_z)
        self.acc_boxes.append(self.acc_x)
        self.acc_boxes.append(self.acc_y)
        self.acc_boxes.append(self.acc_z)
        self.gyro_boxes.append(self.gyro_x)
        self.gyro_boxes.append(self.gyro_y)
        self.gyro_boxes.append(self.gyro_z)
        self.plot_temp.getAxis('bottom').setStyle(showValues=False)
        # self.plot_temp.getAxis('left').setStyle(showValues=False)
        self.plot_temp.setMouseEnabled(x=False, y=False)
        self.plot_temp.setMenuEnabled(False)
        self.plot_temp.setYRange(10, 40)
        for box in self.acc_boxes:
            box.setXRange(-0.2, 0.2)
            box.setYRange(-12, 12)
            box.setMouseEnabled(x=False, y=False)
            box.setMenuEnabled(False)
            box.hideButtons()
            box.getAxis('bottom').setStyle(showValues=False)
            box.getAxis('left').setStyle(showValues=False)
        for box in self.gyro_boxes:
            box.setXRange(-0.2, 0.2)
            box.setYRange(-12, 12)
            box.setMouseEnabled(x=False, y=False)
            box.setMenuEnabled(False)
            box.hideButtons()
            box.getAxis('bottom').setStyle(showValues=False)
            box.getAxis('left').setStyle(showValues=False)

        v = QVBoxLayout()
        v.addWidget(self.graph)
        self.setMinimumSize(320, 240)
        self.setLayout(v)

    def Update(self, values):
        tmp, acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z = values
        show_acc_x = 10 * acc_x / self.acc_max
        show_acc_y = 10 * acc_y / self.acc_max
        show_acc_z = 10 * acc_z / self.acc_max
        show_gyro_x = 10 * gyro_x / 90
        show_gyro_y = 10 * gyro_y / 90
        show_gyro_z = 10 * gyro_z / 90
        self.tmps.append(tmp)
        self.box_acc_x.setOpts(height=show_acc_x)

        self.acc_x_label.setText(str(acc_x))
        self.box_acc_y.setOpts(height=show_acc_y)
        self.acc_y_label.setText(str(acc_y))
        self.box_acc_z.setOpts(height=show_acc_z)
        self.acc_z_label.setText(str(acc_z))
        self.box_gyro_x.setOpts(height=show_gyro_x)
        self.gyro_x_label.setText(str(gyro_x))
        self.box_gyro_y.setOpts(height=show_gyro_y)
        self.gyro_y_label.setText(str(gyro_y))
        self.box_gyro_z.setOpts(height=show_gyro_z)
        self.gyro_z_label.setText(str(gyro_z))
        self.curve_temp.setData(self.tmps)


if __name__ == "__main__":
    import time
    values = [30, 5, 0, -10, 30, 40, -60]
    app = QApplication(sys.argv)
    demo = Sensor()
    demo.show()
    for i in range(100):
        demo.Update(values)
    sys.exit(demo.exec_())
