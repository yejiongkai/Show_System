import ctypes
import sys
import os

root = os.path.curdir
sys.path.append(os.path.join(root, "Module"))
sys.path.append(os.path.join(root, "Module/Local_Camera"))
sys.path.append(os.path.join(root, "Module/Local_Camera/yololite"))
sys.path.append(os.path.join(root, "Module/Local_Camera/yololite/deep_sort/deep/reid"))

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QCursor, QIcon, QColor
from PyQt5.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QDockWidget, QToolBar, QMenu, \
    QAction, QInputDialog, qApp, QGraphicsDropShadowEffect

from Module.QTray import TrayModel
from control import CenterWidget

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myappid")


class MainWindow(QMainWindow):
    count = 0

    def __new__(cls, *args, **kwargs):
        MainWindow.count += 1
        return super(MainWindow, cls).__new__(cls)

    def __del__(self):
        MainWindow.count -= 1

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.hide_normal = True
        self.Control = CenterWidget()
        self.Show = self.Control.Show
        self.Wave = self.Control.Wave
        self.VideoModule = self.Control.VideoModule
        self.tray = TrayModel(self)
        self.threads = [self.VideoModule.trans_thread, self.Wave.thread, self.Show.thread]

        self.setup_ui()

    def setup_ui(self):
        self.setWindowIcon(QIcon('./win.ico'))
        self.setStyleSheet('font-size: 20px;')
        self.resize(1000, 700)
        self.setGeometry(400, 400, 1000, 700)
        show_item = QDockWidget(self)
        show_item.setContextMenuPolicy(3)
        show_item.customContextMenuRequested[QPoint].connect(lambda: self.showContextMenu(show_item))
        menu = QMenu(self)
        self.SetMenuStyle(menu)
        show_item.contextMenu = menu
        #
        wave_item = QDockWidget(self)
        wave_item.setMinimumSize(400, 400)

        video_item = QDockWidget(self)

        clear = QAction('还原', show_item)
        clear.triggered.connect(self.Show_Clear)
        alpha = QAction('设置alpha(角速度分辨率)', show_item)
        alpha.triggered.connect(self.Change_Alpha)
        beta = QAction('设置beta(速度系数)', show_item)
        beta.triggered.connect(self.Change_Beta)

        show_item.contextMenu.addActions([clear, alpha, beta])
        layout = QHBoxLayout()
        show_item.setWidget(self.Show)
        bar = QToolBar()
        bar.setStyleSheet('background-color:rgba(0, 225, 225, 12)')
        show_item.setTitleBarWidget(bar)
        show_item.setFeatures(
            QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable)

        wave_item.setStyleSheet('font-size: 12px;font-family: "宋体";background-color:rgba(255, 255, 255, 230)')
        wave_item.setWidget(self.Wave)
        w_bar = QToolBar()
        w_bar.setStyleSheet('background-color:rgba(0, 225, 225, 12)')
        wave_item.setTitleBarWidget(w_bar)
        wave_item.setFeatures(
            QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable)

        # video_item.setStyleSheet('font-size: 12px;font-family: "宋体";background-color:rgba(255, 255, 255, 230)')
        video_item.setWidget(self.VideoModule)
        v_bar = QToolBar()
        v_bar.setStyleSheet('background-color:rgba(0, 225, 225, 12)')
        video_item.setTitleBarWidget(v_bar)
        video_item.setFeatures(
            QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable)

        show_item.setFloating(False)
        show_item.setMinimumSize(200, 200)

        wave_item.setFloating(False)
        wave_item.setMinimumSize(200, 200)

        video_item.setFloating(False)

        self.setCentralWidget(self.Control)
        self.addDockWidget(Qt.RightDockWidgetArea, show_item)
        self.addDockWidget(Qt.RightDockWidgetArea, wave_item)
        self.addDockWidget(Qt.RightDockWidgetArea, video_item)

        self.setLayout(layout)
        self.setWindowTitle('主界面')

    def SetMenuStyle(self, menu):
        with open('./parameter/menu.qss', 'r') as f:  # 导入QListWidget的qss样式
            menu_style = f.read()

        shadow = QGraphicsDropShadowEffect(menu)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor('#444444'))
        shadow.setBlurRadius(10)

        menu.setStyleSheet(menu_style)
        menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WA_TranslucentBackground)
        menu.setGraphicsEffect(shadow)
        menu_list = menu.actions()
        for action in menu_list:
            if action.menu():
                self.SetMenuStyle(action.menu())

    def showContextMenu(self, cls):
        '''''
        右键点击显示控件右键菜单
        '''
        # 菜单定位
        cls.contextMenu.exec_(QCursor.pos())

    def Show_Clear(self):
        self.Show.Clear()

    def Change_Alpha(self):
        value, ok = QInputDialog.getText(self, '改变alpha', 'cur_alpha', text=str(self.Show.alpha))
        if ok:
            self.Show.alpha = eval(value)
            self.Show.Setting_Save()

    def Change_Beta(self):
        value, ok = QInputDialog.getText(self, '改变beta', 'cur_beta', text=str(self.Show.beta))
        if ok:
            self.Show.beta = eval(value)
            self.Show.Setting_Save()

    def ResetEvent(self):
        self.Control.Drawer.is_route = True
        self.Control.Drawer.is_pause = False
        self.Show.Close = True
        self.Wave.Close = True
        for thread in self.threads:
            thread.wait()
        self.hide()
        qApp.exit(1)

    def closeEvent(self, a0) -> None:
        if self.hide_normal:
            a0.ignore()
            self.hide()
        else:
            self.Control.Drawer.is_route = True
            self.Control.Drawer.is_pause = False
            self.Show.Close = True
            self.Wave.Close = True
            self.VideoModule.is_trans = False
            self.VideoModule.is_detect = False
            self.VideoModule.is_camera_open = False
            self.VideoModule.is_track = False
            for thread in self.threads:
                thread.wait()
            MainWindow.count -= 1
            qApp.exit(0)


if __name__ == '__main__':
    status = 1
    try:
        app = QApplication(sys.argv)
    except RuntimeError:
        app = QApplication.instance()
    while status:
        if MainWindow.count <= 1:
            demo = MainWindow()
            demo.show()
        else:
            continue
        status = app.exec_()
        del demo
    sys.exit(status)