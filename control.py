import sys
from PyQt5.QtWidgets import QListWidget, QStackedWidget, QListWidgetItem, QHBoxLayout, QApplication, QFrame, QMenu
from PyQt5.QtCore import QSize, Qt, QPoint
from PyQt5.QtGui import QCursor
from Module.Route import Drawer
from Module.Servo_Control import Servo_Control
from Module.QMoveWidget import QMoveWidget
from Module.VideoWidget import VideoWidget
from Module.Wave import Wave
from Module.QShow import Show
from Module.Sensor_Show import Sensor
import os
import time
from datetime import datetime

root = os.path.curdir

sys.path.append(os.path.join(root, "Module"))
sys.path.append(os.path.join(root, "parameter"))


class CenterWidget(QFrame):

    def __init__(self):
        super(CenterWidget, self).__init__()
        self.setObjectName('Mermaid')
        self.setWindowTitle('Mermaid')
        self.socket = None
        self._setup_ui()

    def _setup_ui(self):
        with open('./parameter/style.qss', 'r') as f:  # 导入QListWidget的qss样式
            self.list_style = f.read()

        with open('./parameter/Ubuntu.qss', 'r', encoding='utf-8') as f:
            self.setStyleSheet(f.read())

        self.setGeometry(400, 400, 800, 600)

        self.main_layout = QHBoxLayout(self)  # 窗口的整体布局
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.left_widget = QListWidget()  # 左侧选项列表
        self.left_widget.setStyleSheet(self.list_style)
        self.main_layout.addWidget(self.left_widget)

        self.right_widget = QStackedWidget()
        self.main_layout.addWidget(self.right_widget)

        '''加载界面ui'''

        self.left_widget.currentRowChanged.connect(self.right_widget.setCurrentIndex)  # list和右侧窗口的index对应绑定

        self.left_widget.setFrameShape(QListWidget.NoFrame)  # 去掉边框

        self.left_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隐藏滚动条
        self.left_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        list_str = ['网络连接', '运行控制', '规划路径', '轨迹仿真']

        self.Servo_Control = Servo_Control()
        self.Servo_Control.Socket_Connect.connect(self.Socket_Connect)
        self.Servo_Control.Socket_Disconnect.connect(self.Socket_Disconnect)
        self.Servo_Control.Socket_Send.connect(self.Socket_Send)

        self.Wave = Wave(self)

        self.Sensor = Sensor(self)

        self.Show = Show(self)
        self.Show.setContextMenuPolicy(3)
        self.Show.customContextMenuRequested[QPoint].connect(lambda: self.showContextMenu(self.Show))
        self.Show.contextMenu = QMenu()

        self.Drawer = Drawer(self)
        self.Drawer.Order.connect(self.Socket_Send)

        self.Move = QMoveWidget(self.Servo_Control, self.Wave, self)
        self.Move.Order.connect(self.Socket_Send)

        self.VideoModule = VideoWidget(self)
        self.VideoModule.Order.connect(self.Socket_Send)

        list_module = [self.Servo_Control, self.Move, self.Drawer, self.Show]

        for i in range(len(list_str)):
            self.item = QListWidgetItem(list_str[i], self.left_widget)  # 左侧选项的添加
            self.item.setSizeHint(QSize(30, 50))
            self.item.setTextAlignment(Qt.AlignCenter)  # 居中显示
            self.right_widget.addWidget(list_module[i])
        self.left_widget.setCurrentRow(0)

    def showContextMenu(self, cls):
        '''''
        右键点击显示控件右键菜单
        '''
        # 菜单定位
        cls.contextMenu.exec_(QCursor.pos())

    def Socket_Connect(self):
        self.socket = self.Servo_Control.Socket
        self.socket.readyRead.connect(self.Socket_Recv)

    def Socket_Disconnect(self):
        self.socket = None
        # self.Show.A, self.Show.k = 0, 0
        # self.Wave.A, self.Wave.k = 0, 0

    def Socket_Send(self, value: str):
        if self.socket and self.socket.state() == 3:
            self.socket.write(value.encode('utf-8'))
            time.sleep(0.01)

    def Socket_Recv(self):
        if self.socket.state() == 3:
            data = self.socket.readLine(1024).decode('utf-8')[:-1]
            if data:
                if data[0] == "&":
                    try:
                        value = eval(data[1:])
                    except Exception as e:
                        return
                    tmp, acc_x, acc_y, acc_z, g_x, g_z, g_y = value[:7]
                    acc_x /= (16384 / 9.8)
                    acc_y /= (16384 / 9.8)
                    acc_z /= (16384 / 9.8)
                    g_x /= 10
                    g_y /= 10
                    g_z /= 10
                    # if isinstance(data[1], tuple) and len(data[1]) == 3:
                    #     # self.num += 1
                    #     self.Show.A, self.Show.k, _ = data[1]
                    #     self.Wave.A, self.Wave.k, _ = data[1]
                    #     self.Socket.A, self.Socket.k, self.Socket.c = data[1]
                    self.Sensor.Update(list(map(lambda x: round(x, 2), (tmp, acc_x, acc_y, acc_z, g_x, g_y, g_z))))
                else:
                    self.Servo_Control.Recv.append('{}:{}'.format(datetime.now().strftime("%m-%d %H:%M:%S"), data))


def main():
    app = QApplication(sys.argv)

    main_wnd = CenterWidget()
    main_wnd.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
