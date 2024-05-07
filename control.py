import sys
from PyQt5.QtWidgets import QListWidget, QStackedWidget, QListWidgetItem, QHBoxLayout, QApplication, QFrame
from PyQt5.QtCore import QSize, Qt
from Module.Route import Drawer
from Module.Servo_Control import Servo_Control
from Module.QMoveWidget import QMoveWidget
from Module.VideoWidget import VideoWidget
from Module.QWave import Wave
from Module.QShow import Show
import os

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

        list_str = ['网络连接', '运行控制', '规划路径']

        self.Wave = Wave(self)

        self.Show = Show(self)

        self.Drawer = Drawer(self)
        self.Drawer.Order.connect(self.Socket_Send)

        self.Move = QMoveWidget(self)
        self.Move.Order.connect(self.Socket_Send)

        self.VideoModule = VideoWidget(self)
        self.VideoModule.Order.connect(self.Socket_Send)

        self.Servo_Control = Servo_Control()
        self.Servo_Control.Socket_Connect.connect(self.Socket_Connect)
        self.Servo_Control.Socket_Disconnect.connect(self.Socket_Disconnect)
        self.Servo_Control.Socket_Send.connect(self.Socket_Send)

        list_module = [self.Servo_Control, self.Move, self.Drawer]

        for i in range(len(list_str)):
            self.item = QListWidgetItem(list_str[i], self.left_widget)  # 左侧选项的添加
            self.item.setSizeHint(QSize(30, 50))
            self.item.setTextAlignment(Qt.AlignCenter)  # 居中显示
            self.right_widget.addWidget(list_module[i])
        self.left_widget.setCurrentRow(0)

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

    def Socket_Recv(self):
        if self.socket.state() == 3:
            data = self.socket.read(1024)[:-1].decode('utf-8').strip('\n')
            if data:
                self.Socket.TextEdit.append('Receive: {}'.format(data))
                try:
                    data = eval(data)
                except Exception as e:
                    return
                if 'Order' in data:
                    return
                if 'position' in data:
                    try:
                        _, arg = eval(data)
                    except SyntaxError as e:
                        return
                    self.Track.position.emit(arg)
                if isinstance(data[1], tuple) and len(data[1]) == 3:
                    # self.num += 1
                    self.Show.A, self.Show.k, _ = data[1]
                    self.Wave.A, self.Wave.k, _ = data[1]
                    self.Socket.A, self.Socket.k, self.Socket.c = data[1]


def main():
    app = QApplication(sys.argv)

    main_wnd = CenterWidget()
    main_wnd.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()