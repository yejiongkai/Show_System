from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout, QHBoxLayout, QApplication
from PyQt5.QtCore import Qt
import sys


class Sensor(QDialog):

    def __init__(self, parent=None):
        super(Sensor, self).__init__(parent)
        self.SetupUI()

    def SetupUI(self):
        self.setStyleSheet('QWidget {background: palette(window);font-family: "Segoe UI";font-size: 18px;}')
        fix_width, fix_height = 100, 30
        self.temp = QLabel("温度:")
        self.temp.setFixedSize(fix_width, fix_height)
        self.gyro_x = QLabel("X轴偏移")
        self.gyro_x.setFixedSize(fix_width, fix_height)
        self.gyro_y = QLabel("Y轴偏移")
        self.gyro_y.setFixedSize(fix_width, fix_height)
        self.gyro_z = QLabel("Z轴偏移")
        self.gyro_z.setFixedSize(fix_width, fix_height)
        self.acc_x = QLabel("X轴加速度")
        self.acc_x.setFixedSize(fix_width, fix_height)
        self.acc_y = QLabel("Y轴加速度")
        self.acc_y.setFixedSize(fix_width, fix_height)
        self.acc_z = QLabel("Z轴加速度")
        self.acc_z.setFixedSize(fix_width, fix_height)

        h1 = QHBoxLayout()
        h1.setAlignment(Qt.AlignCenter)
        h1.addWidget(self.temp)
        h2 = QHBoxLayout()
        h2.addWidget(self.gyro_x)
        h2.addWidget(self.acc_x)
        h3 = QHBoxLayout()
        h3.addWidget(self.gyro_y)
        h3.addWidget(self.acc_y)
        h4 = QHBoxLayout()
        h4.addWidget(self.gyro_z)
        h4.addWidget(self.acc_z)
        v = QVBoxLayout()
        v.addLayout(h1)
        v.addLayout(h2)
        v.addLayout(h3)
        v.addLayout(h4)
        self.setLayout(v)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    demo = Sensor()
    demo.show()
    sys.exit(demo.exec_())
