# coding:utf-8

import serial
import serial.tools.list_ports
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtNetwork import QTcpSocket
from PyQt5.QtGui import QFont, QPainterPath, QPainter, QBrush, QColor
from PyQt5.QtCore import Qt, QRect, QRectF, pyqtSignal
import sys
import pickle
import time
import os


def format_hex(n):
    return "".join(f"{n:02x}")


class Servo(QtWidgets.QWidget):
    def __init__(self, name, num, ratio_range, parent=None):
        super(Servo, self).__init__(parent)
        self.border_width = 5
        # 设置 窗口无边框和背景透明 *必须
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        self.name = name
        self.num = num
        self.ratio = 90
        self.use_time = 1000  # ms
        self.ratio_range = ratio_range
        self.setupUI()

    def setupUI(self):
        num_label = QtWidgets.QLabel("舵机编号:"+self.name, self)
        ratio_label = QtWidgets.QLabel("角度:", self)
        ratio_label.setFixedSize(50, 20)
        self.ratio_line = QtWidgets.QLineEdit("90", self)
        self.ratio_line.setFixedSize(40, 20)
        self.ratio_line.textChanged.connect(self.ratio_changed)
        self.ratio_slider = QtWidgets.QSlider(Qt.Horizontal, self)
        self.ratio_slider.setRange(0, self.ratio_range)
        self.ratio_slider.setTickInterval(1)
        self.ratio_slider.setValue(self.ratio)
        self.ratio_slider.valueChanged.connect(self.ratio_changed)

        use_time_label = QtWidgets.QLabel("时间:", self)
        use_time_label.setFixedSize(50, 20)
        self.use_time_line = QtWidgets.QLineEdit(self)
        self.use_time_line.setText(str(self.use_time))
        self.use_time_line.setFixedSize(60, 20)
        self.use_time_line.textChanged.connect(self.use_time_changed)
        self.use_time_slider = QtWidgets.QSlider(Qt.Horizontal, self)
        self.use_time_slider.setRange(0, 10000)
        self.use_time_slider.setValue(1000)
        self.use_time_slider.valueChanged.connect(self.use_time_changed)

        self.enable = QtWidgets.QCheckBox(self)
        self.enable.setChecked(True)
        self.enable.setFixedSize(20, 20)

        num_h_layout = QtWidgets.QHBoxLayout()
        ratio_h_layout = QtWidgets.QHBoxLayout()
        use_time_h_layout = QtWidgets.QHBoxLayout()

        num_h_layout.addWidget(num_label)
        # num_h_layout.addWidget(num_line)
        num_h_layout.addWidget(self.enable)
        ratio_h_layout.addWidget(ratio_label)
        ratio_h_layout.addWidget(self.ratio_line)
        ratio_h_layout.addWidget(self.ratio_slider)
        use_time_h_layout.addWidget(use_time_label)
        use_time_h_layout.addWidget(self.use_time_line)
        use_time_h_layout.addWidget(self.use_time_slider)

        total_layout = QtWidgets.QVBoxLayout()
        total_layout.addLayout(num_h_layout)
        total_layout.addLayout(ratio_h_layout)
        total_layout.addLayout(use_time_h_layout)

        self.setLayout(total_layout)

    def ratio_changed(self, val):
        try:
            self.ratio = int(val)
        except Exception as e:
            QtWidgets.QMessageBox.information(self, "警告", str(e))
            return
        self.ratio_line.setText(str(self.ratio))
        self.ratio_slider.setValue(self.ratio)

    def use_time_changed(self, val):
        try:
            self.use_time = int(val)
        except Exception as e:
            QtWidgets.QMessageBox.information(self, "警告", str(e))
            return
        self.use_time_line.setText(str(self.use_time))
        self.use_time_slider.setValue(self.use_time)

    def paintEvent(self, event):
        border = 15

        pat2 = QPainter(self)
        pat2.setRenderHint(pat2.Antialiasing)  # 抗锯齿
        if self.name == "左肩关节" or self.name == "右肩关节":
            pat2.setBrush(QColor(255, 0, 0, 20))
        elif self.name == "腰部旋转":
            pat2.setBrush(QColor(0, 255, 0, 20))
        elif self.name == "左脚底" or self.name == "右脚底":
            pat2.setBrush(QColor(0, 0, 255, 20))
        elif self.name == "左大腿" or self.name == "右大腿":
            pat2.setBrush(QColor(255, 0, 255, 20))
        elif self.name == "左小腿" or self.name == "右小腿":
            pat2.setBrush(QColor(0, 255, 255, 20))
        else:
            pat2.setBrush(QColor(255, 255, 0, 20))
        pat2.setPen(Qt.transparent)
        rect = self.rect()

        rect.setWidth(rect.width())
        rect.setHeight(rect.height())
        pat2.drawRoundedRect(rect, border, border)


class Servo_Control(QtWidgets.QDialog):
    Socket_Connect = pyqtSignal()
    Socket_Disconnect = pyqtSignal()
    Socket_Send = pyqtSignal(str)

    def __init__(self, parent=None):
        # 父类初始化方法
        super(Servo_Control, self).__init__(parent)
        self.servo_map = {0: "腰部旋转", 1: "左脚底", 2: "右脚底", 3: "左肩关节",
                          4: "右肩关节", 5: "左小腿", 6: "右小腿", 7: "左大腿", 8: "右大腿"}
        self.servo_index = [0, 7, 8, 3, 5, 6, 4, 1, 2]
        self.font = QFont('New Roman', 13)
        self.setFont(self.font)
        self.Socket = QTcpSocket(self)
        self.Socket.disconnected.connect(self.Server_Disconnect)
        self.servos = []
        self.UI_Init()
        self.signal_changed()

        self.live = True
        self.send_num = 0

    def UI_Init(self):
        # with open(os.path.join(os.path.dirname(__file__), "Ubuntu.qss"), "r") as f:
        #     self.setStyleSheet(f.read())

        # with open("Ubuntu.qss", "r") as f:
        #     self.setStyleSheet(f.read())

        self.setGeometry(400, 400, 800, 600)

        for i in self.servo_index:
            if i == 0:
                servo = Servo(self.servo_map[i], i, 360)
            elif i == 1 or i == 2 or i == 7 or i == 8:
                servo = Servo(self.servo_map[i], i, 270)
            else:
                servo = Servo(self.servo_map[i], i, 180)
            servo.ratio_line.textChanged.connect(self.signal_changed)
            servo.use_time_line.textChanged.connect(self.signal_changed)
            servo.enable.stateChanged.connect(self.signal_changed)
            self.servos.append(servo)

        self.Recv = QtWidgets.QTextEdit(self)
        self.Recv.setReadOnly(True)

        self.combobox = QtWidgets.QComboBox(self)
        self.combobox.setFixedHeight(30)
        self.combobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.combobox.setEditable(True)
        self.combobox.lineEdit().setFont(self.font)
        self.combobox.lineEdit().setAlignment(Qt.AlignCenter)
        self.combobox.lineEdit().setClearButtonEnabled(True)
        self.combotext = ['192.168.29.191:3411', '127.0.0.1:3411']
        self.combobox.addItems(self.combotext)

        self.save_pb = QtWidgets.QPushButton("保存")
        self.save_pb.clicked.connect(self.Save)
        self.save_pb.setFixedHeight(30)
        self.load_pb = QtWidgets.QPushButton("加载")
        self.load_pb.clicked.connect(self.Load)
        self.load_pb.setFixedHeight(30)

        self.send_pushbutton = QtWidgets.QPushButton("发送")
        self.send_pushbutton.setEnabled(False)
        self.send_pushbutton.clicked.connect(self.Send)
        self.send_pushbutton.setFixedHeight(30)

        self.Connect = QtWidgets.QPushButton('连接', self)
        self.Connect.setFixedHeight(30)
        self.Connect.clicked.connect(self.Socket_Init)

        self.real_time = QtWidgets.QCheckBox(self)
        self.real_time.setFixedHeight(30)
        self.real_time.setText("实时")

        self.reset32 = QtWidgets.QPushButton("STM32重启", self)
        self.reset32.setFixedHeight(30)
        self.reset32.clicked.connect(self.Reset_STM32)

        self.chooseAll = QtWidgets.QCheckBox(self)
        self.chooseAll.setFixedHeight(30)
        self.chooseAll.setText("全选")
        self.chooseAll.clicked.connect(self.ChooseAll)

        self.chooseShoulder = QtWidgets.QCheckBox(self)
        self.chooseShoulder.setFixedHeight(30)
        self.chooseShoulder.setText("肩部")
        self.chooseShoulder.clicked.connect(self.ChooseShoulder)

        self.chooseWaist = QtWidgets.QCheckBox(self)
        self.chooseWaist.setFixedHeight(30)
        self.chooseWaist.setText("腰部")
        self.chooseWaist.clicked.connect(self.ChooseWaist)

        self.gesture_control = QtWidgets.QCheckBox(self)
        self.gesture_control.setFixedHeight(30)
        self.gesture_control.setText("姿态控制")
        self.gesture_control.setChecked(False)
        self.gesture_control.clicked.connect(self.Gesture_Control)

        # 设置布局
        servo_layouts = [QtWidgets.QHBoxLayout(), QtWidgets.QHBoxLayout(), QtWidgets.QHBoxLayout()]
        for i in range(9):
            servo_layouts[i // 3].addWidget(self.servos[i])

        servo_v_layout = QtWidgets.QVBoxLayout()
        for i in range(3):
            servo_v_layout.addLayout(servo_layouts[i])

        layout = QtWidgets.QVBoxLayout()

        h2 = QtWidgets.QHBoxLayout()
        # h2.addWidget(self.time_scale)
        h2.addWidget(self.real_time)
        h2.addWidget(self.chooseAll)
        h2.addWidget(self.chooseShoulder)
        h2.addWidget(self.chooseWaist)
        h2.addWidget(self.gesture_control)
        h2.addWidget(self.send_pushbutton)
        h2.addWidget(self.load_pb)
        h2.addWidget(self.save_pb)

        h2.addWidget(self.reset32)

        h3 = QtWidgets.QHBoxLayout()
        h3.addWidget(self.Connect)
        h3.addWidget(self.combobox, 8)

        layout.addWidget(self.Recv, 6)
        layout.addLayout(servo_v_layout, 6)
        layout.addLayout(h2, 1)
        layout.addLayout(h3, 1)
        self.setLayout(layout)
        self.clearFocus()

    def Socket_Init(self):
        if self.Socket.state() == 3:
            self.Socket.disconnectFromHost()
            self.Socket.waitForDisconnected(3000)
            self.Socket.close()
            self.Connect.setText('连接')
            self.combobox.setEnabled(True)
            self.send_pushbutton.setEnabled(False)
        elif self.Socket.state() == 0:
            try:
                host, port = self.combobox.currentText().split(':')
                self.Socket.connectToHost(host, int(port))
            except Exception as e:
                QtWidgets.QMessageBox.information(self, '警告', str(e))
                return

            if self.Socket.waitForConnected(3000):
                self.Socket_Connect.emit()
                QtWidgets.QMessageBox.information(self, '提示', '连接成功')
                self.Connect.setText('断开')
                self.send_pushbutton.setEnabled(True)
                self.combobox.setEnabled(False)
            else:
                QtWidgets.QMessageBox.information(self, '提示', '连接失败')

    def Server_Disconnect(self):
        self.Socket.disconnectFromHost()
        self.Socket.close()
        self.Socket_Disconnect.emit()
        self.Connect.setText('连接')
        self.combobox.setEnabled(True)
        QtWidgets.QMessageBox.information(self, '提示', '服务器断开')

    def Send(self):
        self.Socket_Send.emit(str((1 << 0, " ".join(self.get_SendMessageFormat()))))

    def Save(self):
        address, _ = QtWidgets.QFileDialog.getSaveFileName(self, "保存数据", ".")
        if address:
            with open(address, "wb+") as f:
                pickle.dump(self.get_SendMessageFormat(), f)

    def Load(self):
        address, _ = QtWidgets.QFileDialog.getOpenFileName(self, "加载数据", ".")

        if address:
            with open(address, "rb+") as f:
                list_bytes = pickle.load(f)

                for i in range(9):
                    self.servos[self.servo_index.index(i)].enable.setChecked(True if (int(list_bytes[1 + i*5], 16) == 1) else False)
                    self.servos[self.servo_index.index(i)].ratio_slider.setValue((int(list_bytes[2 + i*5], 16) << 8) +
                                                         (int(list_bytes[3 + i*5], 16)))
                    self.servos[self.servo_index.index(i)].use_time_slider.setValue((int(list_bytes[4 + i*5], 16) << 8) +
                                                         (int(list_bytes[5 + i*5], 16)))
            # self.signal_changed()

    def Reset_STM32(self):
        self.Socket_Send.emit(str((1 << 7, True)))

    def ChooseAll(self, event):
        if self.chooseAll.isChecked():
            for i in range(9):
                self.servos[i].enable.setChecked(True)
        else:
            for i in range(9):
                self.servos[i].enable.setChecked(False)

    def ChooseShoulder(self):
        if self.chooseShoulder.isChecked():
            for i in range(9):
                self.servos[i].enable.setChecked(False)
            self.servos[3].enable.setChecked(True)
            self.servos[6].enable.setChecked(True)
        else:
            self.servos[3].enable.setChecked(False)
            self.servos[6].enable.setChecked(False)

    def ChooseWaist(self):
        if self.chooseWaist.isChecked():
            for i in range(9):
                self.servos[i].enable.setChecked(False)
            self.servos[0].enable.setChecked(True)
        else:
            self.servos[0].enable.setChecked(False)

    def Gesture_Control(self):
        if self.gesture_control.isChecked():
            self.Socket_Send.emit(str((1 << 6, True)))
        else:
            self.Socket_Send.emit(str((1 << 6, False)))

    def signal_changed(self):
        if self.sender() and type(self.sender().parent()) == Servo:
            num = self.sender().parent().num
            if num == 3 or num == 4:
                self.servos[self.servo_index.index(7 - num)].ratio_line.setText(
                    str(self.servos[self.servo_index.index(num)].ratio_range -
                        self.servos[self.servo_index.index(num)].ratio)
                )
                self.servos[self.servo_index.index(7 - num)].use_time_line.setText(
                    str(self.servos[self.servo_index.index(num)].use_time)
                )
                self.servos[self.servo_index.index(7 - num)].enable.setChecked(
                    self.servos[self.servo_index.index(num)].enable.isChecked()
                )

        if self.real_time.isChecked():
            self.Send()

    def get_SendMessageFormat(self):
        list_bytes = [format_hex(0x01), "00", "00", "00", "00"]
        for i in range(9):
            enable = 1 if self.servos[self.servo_index.index(i)].enable.isChecked() else 0
            ratio = int(self.servos[self.servo_index.index(i)].ratio)
            use_time = int(self.servos[self.servo_index.index(i)].use_time)
            list_bytes.append(format_hex(enable))
            list_bytes.append(format_hex(ratio >> 8))
            list_bytes.append(format_hex(ratio & 0xff))
            if self.real_time.isChecked():
                list_bytes.append("01")
                list_bytes.append("00")
            else:
                list_bytes.append(format_hex(use_time >> 8))
                list_bytes.append(format_hex(use_time & 0xff))
        list_bytes += [format_hex(0x0d), format_hex(0x0c)]

        return list_bytes

    def closeEvent(self, a0):
        self.live = False
        self.thread_recv.wait()


# 运行程序
if __name__ == '__main__':
    QtCore.QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QtWidgets.QApplication(sys.argv)
    main_window = Servo_Control()
    main_window.show()
    sys.exit(app.exec_())
