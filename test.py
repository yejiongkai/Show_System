import sys, time
from datetime import datetime
import pyqtgraph as pg
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QListWidget, QMainWindow, QApplication, QHBoxLayout, QStackedWidget, QListWidgetItem, \
    QDialog, QComboBox, QTextEdit, QPushButton, QFrame, QVBoxLayout
from PyQt5.Qt import QHostAddress
import numpy as np
from MyServer import MyServer
from pyqtgraph import GraphicsLayoutWidget
import os


class Server_Connect(QDialog):
    def __init__(self, parent=None):
        super(Server_Connect, self).__init__(parent)
        self.font = QFont('New Roman', 15)
        self.setFont(self.font)
        self.server = MyServer()
        # self.server.newSocket.connect()
        # self.server.newInfo.connect()
        self.setupUI()

    def setupUI(self):
        self.combobox = QComboBox(self)
        self.combobox.setFixedHeight(30)
        self.combobox.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.combobox.setEditable(True)
        self.combobox.lineEdit().setAlignment(Qt.AlignCenter)
        self.combotext = ['1111']
        self.combobox.addItems(self.combotext)

        self.TextEdit = QTextEdit(self)
        self.TextEdit.setReadOnly(True)

        self.Connect = QPushButton('监听', self)
        self.Connect.setFixedHeight(30)
        self.Connect.clicked.connect(self.Socket_Init)
        self.Connect.setFocusPolicy(Qt.NoFocus)

        seq = 4
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 10)
        layout.addStretch(seq // 4)

        h1 = QHBoxLayout()
        h1.addWidget(self.combobox, 4 * seq)
        h1.addWidget(self.Connect, seq)

        layout.addWidget(self.TextEdit, 5 * seq)
        layout.addLayout(h1, seq)

    def Socket_Init(self):
        if not self.server.isListening():
            port = int(self.combobox.currentText())
            self.server.listen(QHostAddress.Any, port)
            self.Connect.setText('关闭')
            self.combobox.setEnabled(False)
        else:
            self.server.close()
            self.Connect.setText('监听')
            self.combobox.setEnabled(True)


class Curve(QDialog):
    def __init__(self, id, parent=None):
        super(Curve, self).__init__(parent)
        self.id = id
        self.graph = GraphicsLayoutWidget(self)
        h = QHBoxLayout(self)
        h.addWidget(self.graph)
        self.init()

        self.id, self.V, self.A, self.KW, self.factor, self.work_state, self.bad_state = None, [], [], [], [], 0, 0
        self.record_time = []
        self.record_badtime = []
        self.A_thresh = 0.3

        # self.timer = QTimer()
        # self.timer.timeout.connect(self.Update)
        # self.timer.start(50)

    def init(self):
        self.bottomAxis_list = [pg.AxisItem(orientation='bottom') for i in range(4)]
        axis_style = {'color': '#FFC107', 'font-size': '16pt'}
        self.plot_A = self.graph.addPlot(0, 0, axisItems={'bottom': self.bottomAxis_list[0]})
        self.plot_A.setLabel('bottom', 'A', **axis_style)
        self.plot_V = self.graph.addPlot(1, 0, axisItems={'bottom': self.bottomAxis_list[1]})
        self.plot_V.setLabel('bottom', 'V', **axis_style)
        self.plot_KW = self.graph.addPlot(2, 0, axisItems={'bottom': self.bottomAxis_list[2]})
        self.plot_KW.setLabel('bottom', 'KW', **axis_style)
        self.plot_factor = self.graph.addPlot(3, 0, axisItems={'bottom': self.bottomAxis_list[3]})
        self.plot_factor.setLabel('bottom', 'factor', **axis_style)

        for plot in [self.plot_A, self.plot_V, self.plot_KW, self.plot_factor]:
            plot.getAxis("bottom").setStyle(tickFont=QFont("Times", 12), tickTextOffset=10)
            plot.getAxis("left").setStyle(tickFont=QFont("Times", 12), tickTextOffset=10)
            plot.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)

        self.curve_A = self.plot_A.plot(pen=pg.mkPen(color='gray', width=4))
        self.cure_A_thresh = self.plot_A.plot(pen=pg.mkPen(color='red', width=2))
        self.curve_V = self.plot_V.plot(pen=pg.mkPen(color='gray', width=4))
        self.curve_KW = self.plot_KW.plot(pen=pg.mkPen(color='gray', width=4))
        self.curve_factor = self.plot_factor.plot(pen=pg.mkPen(color='gray', width=4))

        # self.plot.setXRange(-100, 100)
        # self.plot.setMouseEnabled(x=True, y=True)
        # self.plot.showAxes(True,
        #                    showValues=(True, True, True, True),
        #                    size=20)

    def Update_State(self, A):  # 0 正常   1 待机   2 停机
        if A == 0:
            self.work_state = 2
            tmp_bad_state = 1
        elif A < self.A_thresh:
            self.work_state = 1
            tmp_bad_state = 1
        else:
            self.work_state = 0
            tmp_bad_state = 0
        if self.bad_state != tmp_bad_state:
            with open("./logs/{}_log.txt".format(self.id), "a+") as f:
                if self.bad_state == 0:
                    self.record_badtime.append([self.record_time[-1]])
                    f.writelines(["Error:", "Start_Time:{}".format(self.record_time[-1]),
                                         "id:{}|A:{}|V:{}|KW:{}|factor:{}|state:{}".format(self.id, self.A[-1], self.V[-1], self.KW[-1],
                                                                                  self.factor[-1], self.work_state), "\n"])
                else:
                    self.record_badtime[-1].append(self.record_time[-1])
                    f.writelines(["Recover:", "End_Time:{}".format(self.record_time[-1]),
                                         "id:{}|A:{}|V:{}|KW:{}|factor:{}|state:{}".format(self.id, self.A[-1], self.V[-1], self.KW[-1],
                                                                                  self.factor[-1], self.work_state), "\n"])
                self.bad_state = tmp_bad_state

    def Update(self, info):
        for i in range(0, len(info), 5):
            id, A, V, KW, factor = info[i:i+5]
            if not self.id:
                self.id = id
                address = "./logs/{}_log.txt".format(self.id)
                if not os.path.exists(address):
                    open(address, "w+")

            self.A.append(A)
            self.V.append(V)
            self.KW.append(KW)
            self.factor.append(factor)
            self.record_time.append(datetime.now().strftime("%H:%M:%S"))
            for axis in self.bottomAxis_list:
                axis.setTicks([dict(enumerate(self.record_time)).items()])

            if len(self.record_time) > 10:
                for plot in [self.plot_A, self.plot_V, self.plot_KW, self.plot_factor]:
                    plot.setXRange(len(self.record_time)-11, len(self.record_time)-1)

            self.Update_State(A)

            self.curve_A.setData(self.A)
            self.cure_A_thresh.setData([self.A_thresh] * len(self.A))
            self.curve_V.setData(self.V)
            self.curve_KW.setData(self.KW)
            self.curve_factor.setData(self.factor)


class MainWidow(QFrame):
    def __init__(self):
        super(MainWidow, self).__init__()
        self.device_dict = dict()
        self.server = Server_Connect()
        self.server.server.newSocket.connect(self.newDevice)
        self.server.server.newInfo.connect(self.newInformation)
        self.setupUi()

    def setupUi(self):
        with open('./parameter/style.qss', 'r') as f:  # 导入QListWidget的qss样式
            self.list_style = f.read()

        with open('./parameter/Ubuntu.qss', 'r', encoding='utf-8') as f:
            self.setStyleSheet(f.read())

        self.setGeometry(400, 100, 1200, 800)

        self.main_layout = QHBoxLayout(self)  # 窗口的整体布局
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.left_widget = QListWidget()  # 左侧选项列表
        self.left_widget.setStyleSheet(self.list_style)
        self.main_layout.addWidget(self.left_widget)

        self.right_widget = QStackedWidget()
        self.main_layout.addWidget(self.right_widget)

        self.left_widget.currentRowChanged.connect(self.right_widget.setCurrentIndex)  # list和右侧窗口的index对应绑定

        self.left_widget.setFrameShape(QListWidget.NoFrame)  # 去掉边框

        self.left_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隐藏滚动条
        self.left_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.item = QListWidgetItem("服务器启动", self.left_widget)
        self.item.setSizeHint(QSize(30, 50))
        self.item.setTextAlignment(Qt.AlignCenter)  # 居中显示
        self.right_widget.addWidget(self.server)
        self.left_widget.setCurrentRow(0)

    def newDevice(self, id):
        device = Curve(id, self)
        self.device_dict[id] = device
        item = QListWidgetItem(str(id), self.left_widget)
        item.setSizeHint(QSize(30, 50))
        item.setTextAlignment(Qt.AlignCenter)  # 居中显示
        self.right_widget.addWidget(device)
        self.left_widget.setCurrentRow(self.left_widget.count() - 1)

    def newInformation(self, id, info):
        device = self.device_dict.get(id)
        self.server.TextEdit.append("id:{}|A:{}|V:{}|KW:{}|factor:{}".format(*info))
        if device:
            device.Update(info)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWidow()
    window.show()
    sys.exit(app.exec_())
