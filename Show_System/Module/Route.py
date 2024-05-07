import os.path
import sys
import math
import time
import numpy as np
import Module.Route_Mode.PID as PID
import Module.Route_Mode.Pure as Pure
import Module.Route_Mode.LQR as LQR

from Module.Route_Mode.Function import Fish_Model
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QThread, QTimer
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QPen, QFont, QCursor, QPainterPathStroker
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog, QFileDialog,\
    QMenu, QAction, QInputDialog, QProgressDialog


class Route_Mode(object):
    def __init__(self, mode=None):
        self.mode = mode
        self.fish_model = Fish_Model(0, 0, 0, 1, 0.5, 0.1)
        self.mode_list = ['PID', 'Pure', 'LQR']
        self.distance_threshold = 20
        self.PID_Control = PID.Control(self.fish_model)
        self.Pure_Control = Pure.Control(self.fish_model)
        self.LQR_Control = LQR.Control(self.fish_model)
        self.path = []

    def Mean(self, path: np.ndarray, sep):
        cur_x, cur_y, self.path = path[0][0], path[0][1], [path[0]]
        for x, y in path[1:]:
            x_d, y_d = abs(cur_x - x), abs(cur_y - y)
            real_sep = math.sqrt(x_d**2 + y_d**2)
            if real_sep > sep:
                max_sep = int(real_sep / sep)
                for i in range(1, max_sep+1):
                    self.path.append((cur_x + i * (x - cur_x) // max_sep, cur_y + i * (y - cur_y) // max_sep))
                cur_x, cur_y = x, y

    def Grad2Angle(self):
        actions = np.array(self.path)
        actions = actions[1:] - actions[:-1]
        x, y = actions[:, 0].copy(), actions[:, 1].copy()
        actions = y / x
        actions[actions == np.inf] = 99999
        actions[actions == -np.inf] = -99999
        actions = np.arctan(actions)
        actions[np.logical_and(actions > 0, y < 0)] = np.pi + actions[np.logical_and(actions > 0, y < 0)]
        actions[np.logical_and(actions < 0, y > 0)] = np.pi + actions[np.logical_and(actions < 0, y > 0)]
        actions[np.logical_and(actions < 0, y < 0)] = 2 * np.pi + actions[np.logical_and(actions < 0, y < 0)]
        actions = actions * 180 / np.pi
        actions = actions[:-1] - actions[1:]
        actions[actions >= 180] = actions[actions >= 180] - 360
        actions[actions <= -180] = 360 + actions[actions <= -180]
        return actions

    def run(self, *args):
        output = None
        if self.mode == 'PID':
            output = self.PID_Control.run(np.array(self.path), self.distance_threshold)
        if self.mode == 'Pure':
            output = self.Pure_Control.run(np.array(self.path), self.distance_threshold)
        if self.mode == 'LQR':
            output = self.LQR_Control.run(np.array(self.path), self.distance_threshold)

        return output


class Drawer(QDialog):
    Order = pyqtSignal(str)

    def __init__(self, parent=None):
        super(QWidget, self).__init__()
        self.setMouseTracking(True)
        self.font = QFont('New Roman', 15)
        self.setFont(self.font)
        self.time = QTimer(self)
        self.time.timeout.connect(self.Straight_Line)
        self.A_k = []
        self.value_range = [10, 20, 30, 40, 50, 60, 70, 80]
        self.straight_points = []
        self.press = False
        self.press_pos = None
        self.press_begin = None
        self.press_Straight = False
        self.is_Straight = False
        self.is_route = False  # 是否进入路径行驶模式
        self.is_pause = False
        self.is_flash = True
        self.y_scale = 1
        self.path_mode = Route_Mode('Pure')
        self.thread = QThread(self)
        self.thread.run = self.Start
        # self.Order.connect(self.Send)  # 测试
        self.A_k_Init()
        self.UI_Init()

        self.stroker = QPainterPathStroker()
        self.stroker.setCapStyle(Qt.RoundCap)
        self.stroker.setJoinStyle(Qt.RoundJoin)
        self.stroker.setDashPattern(Qt.DashLine)
        self.stroker.setWidth(3)

    def A_k_Init(self):
        if os.path.exists('./parameter/A_k.txt'):
            with open('./parameter/A_k.txt', 'r+') as f:
                self.A_k = [eval(i[:-1]) for i in f.readlines()]
        else:
            with open('./parameter/A_k.txt', 'w') as f:
                self.A_k = [(3, 0), (2, 5), (2, 7), (3, 5), (3, 7), (3, 9), (4, 7), (4, 9), (5, 7)]
                f.writelines([str(i)+'\n' for i in self.A_k])

    def UI_Init(self):

        # palette = QtGui.QPalette()
        # # palette.setBrush(w.backgroundRole(), QtGui.QBrush(image)) #背景图片
        # palette.setColor(self.backgroundRole(), QColor(255, 255, 255))  # 背景颜色
        # self.setPalette(palette)
        # self.setAutoFillBackground(True)

        self.setContextMenuPolicy(3)
        self.customContextMenuRequested[QPoint].connect(self.showContextMenu)
        self.contextMenu = QMenu(self)

        set_fish_model = QMenu('设置模型参数', self)
        set_fish_model_v = QAction('设置速度', self)
        set_fish_model_v.triggered.connect(self.Set_Fish_V)
        set_fish_model_l = QAction('设置身长', self)
        set_fish_model_l.triggered.connect(self.Set_Fish_L)
        set_fish_model_t = QAction('设置间隔时间', self)
        set_fish_model_t.triggered.connect(self.Set_Fish_T)
        set_fish_model.addActions([set_fish_model_v, set_fish_model_l, set_fish_model_t])

        set_flash = QAction('显示动画', self)
        set_flash.setCheckable(True)
        set_flash.setChecked(self.is_flash)
        set_flash.triggered.connect(self.Set_Flash)

        set_Y_Scale = QAction('设置y轴比例', self)
        set_Y_Scale.triggered.connect(self.Set_Y_Scale)

        setDistanceThreshold = QAction('设置距离阈值', self)
        setDistanceThreshold.triggered.connect(self.SetDistanceThreshold)

        setPathMode = QAction('设置跟踪模式', self)
        setPathMode.triggered.connect(self.SetPathMode)

        self.contextMenu.addActions([set_flash, set_Y_Scale, setDistanceThreshold, setPathMode])
        self.contextMenu.addMenu(set_fish_model)

        self.setGeometry(400, 400, 600, 400)

        self.cur_position_label = QLabel('Coordinates:', self)

        self.start_route = QPushButton('开始', self)
        self.start_route.clicked.connect(self.Thread_Start)

        self.end_route = QPushButton('结束', self)
        self.end_route.clicked.connect(self.End)

        self.save = QPushButton('保存', self)
        self.save.clicked.connect(self.Save)

        self.load = QPushButton('加载', self)
        self.load.clicked.connect(self.Load)

        self.plan_path = QPainterPath()
        self.actual_path = QPainterPath()

        h = QHBoxLayout()
        h.addWidget(self.cur_position_label, 5)
        h.addWidget(self.save, 1)
        h.addWidget(self.load, 1)
        h.addWidget(self.start_route, 1)
        h.addWidget(self.end_route, 1)

        v = QVBoxLayout()
        v.addLayout(h, 1)
        v.addStretch(9)
        self.setLayout(v)

    def showContextMenu(self):
        '''''
        右键点击显示控件右键菜单
        '''
        # 菜单定位
        self.contextMenu.exec_(QCursor.pos())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(True)

        painter.setPen(QPen(QColor(0, 0, 0, 80), 5, Qt.SolidLine))
        painter.drawPath(self.plan_path)

        if self.is_route:
            painter.setPen(QPen(QColor(255, 0, 0, 255), 7, Qt.SolidLine))
            painter.drawPath(self.actual_path)

    def mousePressEvent(self, event):
        if not self.is_route:
            self.press = True
            if not self.press_Straight:
                self.is_Straight = False
                self.plan_path.clear()
                self.press_pos = event.pos()
                self.press_begin = event.pos()
                self.plan_path.clear()
                self.plan_path.moveTo(event.pos())
            self.update()

    def Straight_Line(self):
        if self.press_pos == self.mapFromGlobal(QCursor.pos()) and self.press_Straight is False and self.press:
            self.press_Straight = True
            self.is_Straight = True
            self.plan_path.clear()
            self.plan_path.moveTo(self.press_begin)
            self.plan_path.lineTo(self.press_pos)
            self.straight_points.append(self.press_begin)
            self.update()

    def mouseMoveEvent(self, event):
        if self.press or self.press_Straight:
            self.press_pos = event.pos()
            if not self.is_route:
                if self.press_Straight:
                    if self.straight_points:
                        self.plan_path.clear()
                        self.plan_path.moveTo(self.straight_points[0])
                        for i in range(1, len(self.straight_points)):
                            self.plan_path.lineTo(self.straight_points[i])
                        self.plan_path.lineTo(self.press_pos)
                        self.update()
                else:
                    self.plan_path.lineTo(event.pos())
                    self.update()

                    self.time.start(1000)

        self.cur_position_label.setText('Coordinates: {}, {}'.format(event.pos().x(), event.pos().y()))

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        if not self.is_route:
            if self.press_Straight:
                if a0.button() == Qt.RightButton:
                    self.straight_points = []
                    self.press = False
                    self.press_Straight = False
                    self.press_begin = None
                    self.press_pos = None
                else:
                    self.press_begin = self.press_pos
                    self.straight_points.append(self.press_begin)
            else:
                self.press = False
                self.press_Straight = False
                self.press_begin = None
                self.press_pos = None

            # self.plan_path = self.stroker.createStroke(self.plan_path)
            self.update()

    def Save(self):
        import pickle
        file, s = QFileDialog.getSaveFileName(self, 'Save Route', '.', 'Route(*.route);;Position(*.csv)')
        if file and not self.plan_path.isEmpty():
            route = []
            for i in range(self.plan_path.elementCount()):
                element = self.plan_path.elementAt(i)
                route.append((element.x, element.y))
            if s == 'Route(*.route)':
                with open(file, 'wb') as f:
                    pickle.dump(route, f)
            elif s == 'Position(*.csv)':
                import pandas as pd
                route_csv = pd.DataFrame(route, columns=['X', 'Y'])
                route_csv.to_csv(file, index=False)

    def Load(self):
        if not self.is_route:
            import pickle
            file, s = QFileDialog.getOpenFileName(self, 'Load Route', '.', 'Route(*.route);;Position(*.csv)')
            if file:
                if s == 'Route(*.route)':
                    with open(file, 'rb') as f:
                        route = pickle.load(f)
                elif s == 'Position(*.csv)':
                    import pandas as pd
                    with open(file, 'rb') as f:
                        route = pd.read_csv(f).values
                # route = np.zeros((300, 2))
                # route[:, 0] = np.linspace(100, 400, 300)  # x
                # route[:, 1] = 300 + 100 * np.sin(route[:, 0] / 20) + 25 * np.cos(
                #     route[:, 0] / 8.0)  # y
                # route = np.zeros((300, 2))
                self.press = False
                self.plan_path.clear()
                self.plan_path.moveTo(*route[0])
                for i in range(1, len(route)):
                    self.plan_path.lineTo(*route[i])
                self.update()

    def SetDistanceThreshold(self):
        value, ok = QInputDialog.getDouble(self, 'cur_threshold', '', value=self.path_mode.distance_threshold)
        if ok:
            self.path_mode.distance_threshold = value

    def SetPathMode(self):
        value, ok = QInputDialog.getItem(self, 'cur_mode', '', self.path_mode.mode_list,
                                         self.path_mode.mode_list.index(self.path_mode.mode))
        if ok:
            self.path_mode.mode = value

    def Set_Y_Scale(self):
        value, ok = QInputDialog.getDouble(self, 'cur_scale', '', max=10, min=0, decimals=4, value=self.y_scale)
        if ok:
            self.y_scale = value

    def Set_Flash(self, v):
        self.is_flash = v
        # flash_l = ['True', 'False']
        # value, ok = QInputDialog.getItem(self, '是否显示动画', '', flash_l, flash_l.index(str(self.is_flash)))
        # if ok:
        #     self.is_flash = eval(value)

    def Set_Fish_V(self):
        value, ok = QInputDialog.getDouble(self, 'cur_v', '', max=10, min=0, decimals=2,
                                           value=self.path_mode.fish_model.v)
        if ok:
            self.path_mode.fish_model.v = value

    def Set_Fish_L(self):
        value, ok = QInputDialog.getDouble(self, 'cur_l', '', max=10, min=0, decimals=2,
                                           value=self.path_mode.fish_model.L)
        if ok:
            self.path_mode.fish_model.L = value

    def Set_Fish_T(self):
        value, ok = QInputDialog.getDouble(self, 'cur_t', '', max=10, min=0, decimals=2,
                                           value=self.path_mode.fish_model.dt)
        if ok:
            self.path_mode.fish_model.dt = value

    def Start(self, speed=0.1):
        self.A_k_Init()
        path = [(self.plan_path.elementAt(i).x, self.plan_path.elementAt(i).y*self.y_scale)
                for i in range(self.plan_path.elementCount())]
        if len(path) < 2:
            return
        if self.is_Straight:
            self.path_mode.Mean(path, 2)
        else:
            self.path_mode.path = path
        path = np.array(self.path_mode.run())
        path[:, 1] /= self.y_scale
        actions = self.path_mode.Grad2Angle()
        '_________________________________________________________________________________'
        j = 0
        l = len(actions)
        lis = [[] for i in range(l)]
        a = np.zeros(shape=(l,))
        k = np.zeros(shape=(l,))
        lis[0] = [a[0], k[0]]
        lis[l - 1] = [a[l - 1], k[l - 1]]
        while j < len(actions) - 2:
            # 前进
            if -self.value_range[0] <= actions[j] <= self.value_range[0]:
                a[j + 1] = self.A_k[0][0]
                k[j + 1] = self.A_k[0][1]
            # 第一档
            elif self.value_range[0] < actions[j] <= self.value_range[1] or\
                    -self.value_range[1] < actions[j] <= -self.value_range[0]:
                a[j + 1] = self.A_k[1][0]
                k[j + 1] = self.A_k[1][1] * (abs(actions[j]) / actions[j])
            elif self.value_range[1] < actions[j] <= self.value_range[2] or\
                    -self.value_range[2] < actions[j] <= self.value_range[1]:
                a[j + 1] = self.A_k[2][0]
                k[j + 1] = self.A_k[2][1] * (abs(actions[j]) / actions[j])
            elif self.value_range[2] < actions[j] <= self.value_range[3] or\
                    -self.value_range[3] < actions[j] <= -self.value_range[2]:
                a[j + 1] = self.A_k[3][0]
                k[j + 1] = self.A_k[3][1] * (abs(actions[j]) / actions[j])
            elif self.value_range[3] < actions[j] <= self.value_range[4] or\
                    -self.value_range[4] < actions[j] <= -self.value_range[3]:
                a[j + 1] = self.A_k[4][0]
                k[j + 1] = self.A_k[4][1] * (abs(actions[j]) / actions[j])
            elif self.value_range[4] < actions[j] <= self.value_range[5] or\
                    -self.value_range[5] < actions[j] <= -self.value_range[4]:
                a[j + 1] = self.A_k[5][0]
                k[j + 1] = self.A_k[5][1] * (abs(actions[j]) / actions[j])
            elif self.value_range[5] < actions[j] <= self.value_range[6] or\
                    -self.value_range[6] < actions[j] <= -self.value_range[5]:
                a[j + 1] = self.A_k[6][0]
                k[j + 1] = self.A_k[6][1] * (abs(actions[j]) / actions[j])
            elif self.value_range[6] < actions[j] <= self.value_range[7] or -self.value_range[7] < actions[j] <= -self.value_range[6]:
                a[j + 1] = self.A_k[7][0]
                k[j + 1] = self.A_k[7][1] * (abs(actions[j]) / actions[j])
            elif self.value_range[7] < actions[j] or actions[j] < -self.value_range[7]:
                a[j + 1] = self.A_k[8][0]
                k[j + 1] = self.A_k[8][1] * (abs(actions[j]) / actions[j])
            lis[j + 1] = [a[j + 1], k[j + 1]]
            j += 1
        print(lis)
        '_________________________________________________________________________________'
        self.Order.emit(str((1 << 1, lis)) + '\n')
        self.actual_path.moveTo(*path[0])
        i = 1
        distance = 30 if len(path) // 50 > 30 else len(path) // 50
        sep = distance
        while i < len(path) and self.is_route:
            if not self.is_pause:
                self.actual_path.lineTo(*path[i])
                # self.Order.emit(actions[i - 1])
                self.update()
                i += 1
            delay_mark = time.time()
            sep -= 1
            if sep == 0:
                offset = 0
                while offset <= 0.01 and self.is_flash:
                    offset = time.time() - delay_mark
                sep = distance
                # time.sleep(0.001)

        # self.End()

    def Thread_Start(self):
        if self.plan_path.elementCount():
            if self.is_route:
                if self.is_pause:
                    self.start_route.setText('暂停')
                    self.Order.emit(str((1 << 1, True))+'\n')
                else:
                    self.start_route.setText('启动')
                    self.Order.emit(str((1 << 1, False))+'\n')
                self.is_pause ^= 1
            else:
                self.is_route = True
                self.is_pause = False
                self.start_route.setText('暂停')
                self.thread.start()

    def End(self):
        self.is_route = False
        self.press_Straight = False
        self.Order.emit(str((1 << 1, False))+'\n')
        self.actual_path.clear()
        self.update()
        self.start_route.setText('开始')

    def Send(self, value):
        print(value)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.is_route = True
        self.is_pause = False
        self.thread.wait()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Drawer()
    w.show()
    sys.exit(app.exec_())
