from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox
from PyQt5.QtGui import (
    QColor, QPainterPath, QFont, QPainter, QLinearGradient, QBrush, QPen, QFontMetrics,
    QRadialGradient, QPixmap, QTransform
)
from PyQt5.QtCore import QPoint, QRectF, pyqtSignal
from PyQt5.Qt import Qt
import math
import time


def format_hex(n):
    return "".join(f"{n:02x}")


class QMoveWidget(QWidget):
    Order = pyqtSignal(str)

    def __init__(self, servo_control=None, parent=None):
        super(QMoveWidget, self).__init__(parent)
        self.servo_control = servo_control

    def __init__(self, wave=None, parent=None):
        super(QMoveWidget, self).__init__(parent)
        self.wave = wave
        self.mDegreePixmap_y = 0
        self.mDegreePixmap_x = 0
        self.Degree_y, self.Degree_x = 0, 0
        self.m_pressIndex = 0
        self.m_enterIndex = 0
        self.m_isMouseEntered = False
        self.m_isMousePressed_left = False
        self.m_isMousePressed_right = False
        self.m_radius = 150
        self.m_arcLength = 130
        self.mCenterRound = QPoint(0, 0)
        self.m_bTextModeEn = False
        self.setMouseTracking(True)
        self.mSectorColor = QColor(38, 38, 38)
        self.m_arcPathList = []
        self.m_colorList = []
        self.m_textPathList = []
        self.mCurWorkRegion = []
        self.QUADRANT_UP = 1
        self.QUADRANT_LEFT = 2
        self.QUADRANT_DOWN = 3
        self.QUADRANT_RIGHT = 4
        self.M_PI = 3.14159265358979323846
        self.cur_style = 0    # 0: 对称   1：同步
        self.send_num = 0
        self.initButton()
        self.setWidgetStyle(self.cur_style)
        self.setAxesVertical(False)

    def setWidgetStyle(self, style):
        if style == 0:
            self.forward_label.setStyleSheet(
                'border-width: 2px;border-style: solid;border-color: rgb(175, 180, 191);background-color: rgb(221, 225, 231);color: rgb(239, 39, 87)')
            self.side_label.setStyleSheet(
                'border-width: 2px;border-style: solid;border-color: rgb(175, 180, 191);background-color: rgb(221, 225, 231);color: rgb(239, 39, 87)')
            self.mode_label.setStyleSheet(
                'border-width: 2px;border-style: solid;border-color: rgb(175, 180, 191);background-color: rgb(221, 225, 231);color: rgb(239, 39, 87)')
            self.mSectorColor = QColor(238, 241, 240)
            self.colorSPL = QColor(63, 155, 178)
            self.colorBKG = QColor(193, 199, 209)

            self.colorSectorUp2 = QColor(240, 243, 208)
            self.colorSectorUp = QColor(239, 242, 247)
            self.colorSectorDown = QColor(221, 225, 231)

            self.colorbgGradient0 = QColor(175, 180, 191)
            self.colorbgGradient1 = QColor(239, 242, 247)

            self.colorExcircle0 = QColor(68, 68, 68)
            self.colorExcircle5 = QColor(37, 40, 46)
            self.colorExcircle9 = QColor(22, 22, 22)

            self.colorInnerCircle0 = QColor(45, 48, 56)
            self.colorInnerCircle9 = QColor(30, 32, 37)
        else:
            self.forward_label.setStyleSheet(
                'border-width: 2px;border-style: solid;border-color: rgb(24, 24, 24);background-color: rgb(41, 44, 50); color: rgb(5, 199, 199);')
            self.side_label.setStyleSheet(
                'border-width: 2px;border-style: solid;border-color: rgb(24, 24, 24);background-color: rgb(41, 44, 50); color: rgb(5, 199, 199);')
            self.mode_label.setStyleSheet(
                'border-width: 2px;border-style: solid;border-color: rgb(24, 24, 24);background-color: rgb(41, 44, 50); color: rgb(5, 199, 199);')

            self.mSectorColor = QColor(38, 38, 38)
            self.colorSPL = QColor(32, 149, 216)
            self.colorBKG = QColor(41, 44, 50)

            self.colorSectorUp2 = QColor(68, 68, 68)
            self.colorSectorUp = QColor(60, 60, 60)
            self.colorSectorDown = QColor(22, 22, 22)

            self.colorbgGradient0 = QColor(24, 24, 24)
            self.colorbgGradient1 = QColor(53, 57, 63)

            self.colorExcircle0 = QColor(211, 215, 223)
            self.colorExcircle5 = QColor(231, 235, 240)
            self.colorExcircle9 = QColor(182, 187, 197)

            self.colorInnerCircle0 = QColor(45, 48, 56)
            self.colorInnerCircle9 = QColor(30, 32, 37)
        self.update()

    def setRadiusValue(self, radius):
        self.m_radius = radius

    def setArcLength(self, arcLength):
        self.m_arcLength = arcLength

    def drawRotatedText(self, painter, degrees, x, y, text):
        painter.save()  # 保存原来坐标系统
        painter.translate(x, y)  # 平移坐标原点到x， y
        painter.rotate(degrees)  # 坐标旋转degrees度
        painter.drawText(0, 0, text)  # 在原点绘制文本
        painter.restore()  # 回复原来的坐标系统

    def setAxesVertical(self, axesVertical):
        self.mAxesVertical = axesVertical
        if not self.mAxesVertical:
            self.addArc(1, 0, 45, 90, self.mSectorColor)
            self.addArc(0, 1, 135, 90, self.mSectorColor)
            self.addArc(-1, 0, 225, 90, self.mSectorColor)
            self.addArc(0, -1, 315, 90, self.mSectorColor)
        else:
            self.addArc(1, 0, 0, 90, self.mSectorColor)
            self.addArc(0, 1, 90, 90, self.mSectorColor)
            self.addArc(-1, 0, 180, 90, self.mSectorColor)
            self.addArc(0, -1, 270, 90, self.mSectorColor)

        # 绘制中心圆
        self.centerRoundPath = QPainterPath()
        self.centerRoundPath.addEllipse(QPoint(0, 0), self.m_radius - self.m_arcLength + 2,
                                        self.m_radius - self.m_arcLength + 2)
        self.m_arcPathList.append(self.centerRoundPath)
        self.m_colorList.append(QColor(255, 255, 255))

        # 添加文字
        self.font = QFont()
        self.font.setFamily("Microsoft YaHei")
        self.font.setPointSize(18)

        for i in range(len(self.m_arcPathList)):
            painterPath = QPainterPath()
            self.m_textPathList.append(painterPath)

        self.mStrUp = "↑"
        self.mStrLeft = "←"
        self.mStrDown = "切换"
        self.mStrRight = "→"
        self.update()

    def initButton(self):
        self.setGeometry(400, 400, 600, 400)
        self.mode_label = QLabel(self)
        self.mode_label.setText("模式:    对称")
        self.mode_label.setFont(QFont("Arial", 20))
        self.mode_label.setFixedSize(170, 40)
        self.mode_label.setStyleSheet(
            'border-width: 5px;border-style: solid;border-color: rgb(175, 180, 191);background-color: rgb(221, 225, 231);')
        self.forward_label = QLabel(self)
        self.forward_label.setText("前向分量:{:>2}".format(int(self.Degree_y)))
        self.forward_label.setFont(QFont("Arial", 20))
        self.forward_label.setFixedSize(170, 40)
        self.forward_label.setStyleSheet(
            'border-width: 5px;border-style: solid;border-color: rgb(175, 180, 191);background-color: rgb(221, 225, 231);')
        self.side_label = QLabel(self)
        self.side_label.setText("侧向分量:{:>2}".format(int(self.Degree_x)))
        self.side_label.setFont(QFont("Arial", 20))
        self.side_label.setFixedSize(170, 40)
        self.side_label.setStyleSheet(
            'border-width: 5px;border-style: solid;border-color: rgb(175, 180, 191);background-color: rgb(221, 225, 231);')

        self.send_pushbutton = QPushButton("发送")
        self.send_pushbutton.setEnabled(True)
        self.send_pushbutton.setFont(QFont("Arial", 18))
        self.send_pushbutton.clicked.connect(self.Send)

        self.real_time = QCheckBox(self)
        self.real_time.setFont(QFont("Arial", 18))
        self.real_time.setText("实时")

        self.h_layout = QHBoxLayout()
        # self.h_layout.setAlignment(Qt.AlignJustify)
        self.h_layout.addWidget(self.real_time)
        self.h_layout.addWidget(self.send_pushbutton)

        self.label_layout = QVBoxLayout()
        self.label_layout.addWidget(self.mode_label, 2)
        self.label_layout.addWidget(self.forward_label, 2)
        self.label_layout.addWidget(self.side_label, 2)
        self.label_layout.addLayout(self.h_layout)

        self.label_layout.setAlignment(Qt.AlignRight)

        self.setLayout(self.label_layout)

        self.addArc(1, 0, 45, 90, self.mSectorColor)
        self.addArc(0, 1, 135, 90, self.mSectorColor)
        self.addArc(-1, 0, 225, 90, self.mSectorColor)
        self.addArc(0, -1, 315, 90, self.mSectorColor)

        # 绘制中心圆
        self.centerRoundPath = QPainterPath()
        self.centerRoundPath.addEllipse(QPoint(0, 0), self.m_radius - self.m_arcLength + 2,
                                        self.m_radius - self.m_arcLength + 2)
        self.m_arcPathList.append(self.centerRoundPath)
        self.m_colorList.append(QColor(255, 255, 255))

        # 添加文字
        font = QFont()
        font.setFamily("Microsoft YaHei")
        font.setPointSize(14)

        for i in range(len(self.m_arcPathList)):
            painterPath = QPainterPath()
            self.m_textPathList.append(painterPath)

        self.mStrUp = "↑"
        self.mStrLeft = "←"
        self.mStrDown = "切换"
        self.mStrRight = "→"

    def Send(self):
        """
            mode			1byte      2: 鱼体波
            synmode		    1byte      0： 同步    1：对称
            montionmode	    1byte      0： 前进    1：左转    2：右转    其他：停止复位
            T				1byte	   T>1.8
            c1_amp			1byte	   1<c1_amp<1.5
            flag	  1*9 = 18byte
            angle     2*9 = 18byte
            time	  2*9 = 18byte
            end		 0d0c = 2byte
        """
        T = max(255 - int(math.sqrt(self.Degree_y ** 2 + self.Degree_x ** 2) / 12.8 * 255), 0)
        if self.Degree_y == 0:
            c1_amp = 255
        elif self.Degree_x == 0:
            c1_amp = 0
        else:
            c1_amp = int(self.Degree_x**2 / (self.Degree_y ** 2 + self.Degree_x ** 2) * 255)

        list_bytes = [format_hex(0x02), format_hex(0x00 if self.cur_style else 0x01)]

        if self.Degree_y == 0 and self.Degree_x == 0:
            list_bytes.append(format_hex(0x03))
        elif self.Degree_x == 0:
            list_bytes.append(format_hex(0x00))
        elif self.QUADRANT_RIGHT in self.mCurWorkRegion:
            list_bytes.append(format_hex(0x02))
        elif self.QUADRANT_LEFT in self.mCurWorkRegion:
            list_bytes.append(format_hex(0x01))

        list_bytes.append(format_hex(T))
        list_bytes.append(format_hex(c1_amp))
        list_bytes += ["00"] * 45
        list_bytes += [format_hex(0x0d), format_hex(0x0c)]

        print(" ".join(list_bytes))
        self.Order.emit(str((1 << 1, " ".join(list_bytes))))
        self.wave.c1_amp = c1_amp / 512 + 1
        self.wave.T = T / 256 + 1.8
        if list_bytes[1] == "00" and list_bytes[2] == "00":
            self.wave.mode = "sync_front"
        elif list_bytes[1] == "01" and list_bytes[2] == "00":
            self.wave.mode = "async_front"
        elif list_bytes[2] == "01":
            self.wave.mode = "left"
        elif list_bytes[2] == "02":
            self.wave.mode = "right"
        else:
            self.wave.mode = "stop"

    def paintEvent(self, QPaintEvent):
        self.forward_label.setText("前向分量:{:>2}".format(int(self.Degree_y)))
        self.side_label.setText("侧向分量:{:>2}".format(int(self.Degree_x)))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.HighQualityAntialiasing, True)

        painter.setPen(Qt.NoPen)
        painter.translate(self.width() / 3, self.height() >> 1)

        # 背景色，分割线颜色
        painter.setBrush(self.colorBKG)
        painter.drawEllipse(QPoint(0, 0), self.m_radius + 8, self.m_radius + 8)

        linearGradient = QLinearGradient(0, -self.m_radius - 2, 0, self.m_radius + 2)
        linearGradient.setColorAt(0.0, self.colorSectorUp2)
        linearGradient.setColorAt(0.9, self.colorSectorDown)
        painter.setBrush(QBrush(linearGradient))
        painter.drawEllipse(QPoint(0, 0), self.m_radius + 2, self.m_radius + 2)

        linearGradient = QLinearGradient(0, -self.m_radius, 0, self.m_radius)
        linearGradient.setColorAt(0.0, self.colorSectorUp)
        linearGradient.setColorAt(0.9, self.colorSectorDown)
        painter.setBrush(QBrush(linearGradient))
        painter.drawEllipse(QPoint(0, 0), self.m_radius, self.m_radius)

        bgGradient = QLinearGradient(0, -37, 0, 37)
        bgGradient.setColorAt(0.0, self.colorbgGradient0)
        bgGradient.setColorAt(1.0, self.colorbgGradient1)
        painter.setBrush(bgGradient)
        painter.drawEllipse(QPoint(0, 0), self.m_radius - self.m_arcLength + 4,
                            self.m_radius - self.m_arcLength + 4)

        count = 4
        for i in range(count):
            painter.save()
            if not self.mAxesVertical:
                painter.rotate(45 + 90 * i)

            else:
                painter.rotate(0 + 90 * i)
            painter.setPen(QPen(self.colorBKG, 3, Qt.SolidLine))
            painter.drawLine(0, self.m_radius - self.m_arcLength + 5, 0, self.m_radius + 5)
            painter.setPen(QPen(self.colorSPL, 3, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(0, self.m_radius - self.m_arcLength + 6, 0, 40)
            painter.setPen(QPen(self.colorSPL, 3, Qt.SolidLine))
            painter.drawLine(0, 40, 0, self.m_radius - 5)
            painter.restore()

        linearGradient = QLinearGradient(0, self.mCenterRound.y() - self.m_radius + self.m_arcLength - 1, 0,
                                         self.mCenterRound.y() + self.m_radius - self.m_arcLength + 1)
        linearGradient.setColorAt(0.0, self.colorExcircle0)
        linearGradient.setColorAt(0.0, self.colorExcircle5)
        linearGradient.setColorAt(0.9, self.colorExcircle9)

        painter.setBrush(QBrush(linearGradient))
        painter.drawEllipse(self.mCenterRound, self.m_radius - self.m_arcLength, self.m_radius - self.m_arcLength)

        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        if not self.mAxesVertical:
            leftmatrix = QTransform()
            if self.QUADRANT_UP in self.mCurWorkRegion:
                painter.drawPixmap(int(-self.m_radius / 2), int(-self.m_radius * 3 / 4), self.m_radius,
                                   self.m_radius // 2, self.mDegreePixmap_y)
                leftmatrix.reset()
            if self.QUADRANT_LEFT in self.mCurWorkRegion:
                leftmatrix.rotate(270)
                mDegreePixmap = self.mDegreePixmap_x.transformed(leftmatrix, Qt.SmoothTransformation)
                painter.drawPixmap(int(-self.m_radius * 3 / 4), -self.m_radius // 2, self.m_radius // 2, self.m_radius,
                                   mDegreePixmap)
                leftmatrix.reset()
            if self.QUADRANT_DOWN in self.mCurWorkRegion:
                pass
                # leftmatrix.rotate(180)
                # mDegreePixmap = self.mDegreePixmap_y.transformed(leftmatrix, Qt.SmoothTransformation)
                # painter.drawPixmap(-self.m_radius//2, self.m_radius//4, self.m_radius, self.m_radius//2, mDegreePixmap)
                # leftmatrix.reset()
            if self.QUADRANT_RIGHT in self.mCurWorkRegion:
                leftmatrix.rotate(90)
                mDegreePixmap = self.mDegreePixmap_x.transformed(leftmatrix, Qt.SmoothTransformation)
                painter.drawPixmap(self.m_radius // 4, -self.m_radius // 2, self.m_radius // 2, self.m_radius,
                                   mDegreePixmap)
                leftmatrix.reset()

        font = QFont()
        font.setFamily("Microsoft YaHei")
        font.setPointSize(18)
        painter.setFont(font)
        painter.setPen(QColor(170, 170, 170))
        if self.mAxesVertical:
            painter.drawText(QPoint(-60, -40), self.mStrUp)
            painter.drawText(QPoint(30, -40), self.mStrLeft)
            painter.drawText(QPoint(-80, 40), self.mStrDown)
            painter.drawText(QPoint(20, 40), self.mStrRight)
        else:
            fm = QFontMetrics(font)
            rText = 100
            nHeight = fm.height() - 4
            iTotalWidth = fm.width(self.mStrUp)
            painter.save()
            painter.rotate(-90 * iTotalWidth / (rText * self.M_PI))
            for i in range(len(self.mStrUp)):
                self.nWidth = fm.width(self.mStrUp[i])
                painter.rotate(90 * self.nWidth / (rText * self.M_PI))
                painter.drawText(-self.nWidth / 2, -1 * rText, self.mStrUp[i])
                painter.rotate(90 * self.nWidth / (rText * self.M_PI))
            painter.restore()
            painter.save()
            if self.m_bTextModeEn:
                iTotalWidth = fm.width(self.mStrRight)
                painter.rotate(90 - 90 * iTotalWidth / (rText * self.M_PI))
                for i in range(len(self.mStrRight)):
                    nWidth = fm.width(self.mStrRight[i])
                    painter.rotate(90 * nWidth / (rText * self.M_PI))
                    painter.drawText(-nWidth / 2, -1 * rText, self.mStrRight[i])
                    painter.rotate(90 * nWidth / (rText * self.M_PI))
            else:
                iTotalWidth = nHeight * len(self.mStrRight)
                painter.rotate(-90 * iTotalWidth / (rText * self.M_PI))
                for i in range(len(self.mStrRight)):
                    painter.rotate(90 * nHeight / (rText * self.M_PI))
                    painter.drawText(rText - 5, nHeight / 2, self.mStrRight[i])
                    painter.rotate(90 * nHeight / (rText * self.M_PI))
            painter.restore()

            painter.save()
            iTotalWidth = fm.width(self.mStrDown)
            painter.rotate(90 * iTotalWidth / (rText * self.M_PI))
            for i in range(len(self.mStrDown)):
                nWidth = fm.width(self.mStrDown[i])
                painter.rotate(-90 * nWidth / (rText * self.M_PI))
                painter.drawText(-nWidth / 2, rText + nHeight - 8, self.mStrDown[i])
                painter.rotate(-90 * nWidth / (rText * self.M_PI))
            painter.restore()

            painter.save()
            if self.m_bTextModeEn:
                iTotalWidth = fm.width(self.mStrLeft)
                painter.rotate(90 + 90 * iTotalWidth / (rText * self.M_PI))
                for i in range(len(self.mStrLeft)):
                    nWidth = fm.width(self.mStrLeft[i])
                    painter.rotate(-90 * nWidth / (rText * self.M_PI))
                    painter.drawText(-nWidth / 2, rText + nHeight - 8, self.mStrLeft[i])
                    painter.rotate(-90 * nWidth / (rText * self.M_PI))

            else:
                iTotalWidth = nHeight * len(self.mStrLeft)
                painter.rotate(90 * iTotalWidth / (rText * self.M_PI))
                for i in range(len(self.mStrLeft)):
                    painter.rotate(-90 * nHeight / (rText * self.M_PI))
                    painter.drawText(-rText - 20, nHeight / 2, self.mStrLeft[i])
                    painter.rotate(-90 * nHeight / (rText * self.M_PI))
            painter.restore()

    def addArc(self, x, y, startAngle, angleLength, color):
        rect = QRectF(-self.m_radius + x, -self.m_radius + y, self.m_radius * 2, self.m_radius * 2)
        path = QPainterPath()
        path.arcTo(rect, startAngle, angleLength)
        subPath = QPainterPath()
        subPath.addEllipse(rect.adjusted(self.m_arcLength, self.m_arcLength, -self.m_arcLength, -self.m_arcLength))
        path -= subPath
        self.m_arcPathList.append(path)
        radialGradient = QRadialGradient()
        radialGradient.setCenter(0, 0)
        radialGradient.setRadius(self.m_radius)
        radialGradient.setColorAt(0, color)
        radialGradient.setColorAt(1.0, color)
        self.m_colorList.append(radialGradient)

    def mousePressEvent(self, event):
        mousePressPoint = event.pos()
        translatePoint = mousePressPoint - QPoint(self.width() / 3, self.height() >> 1)
        angle = self.analysisAngle(translatePoint.x(), translatePoint.y())
        length = math.sqrt(translatePoint.x() ** 2 + translatePoint.y() ** 2)
        if 40 < angle < 130 and self.m_radius*0.2 < length < self.m_radius*0.8:
            self.setWidgetStyle(1 - self.cur_style)
            self.cur_style = 1 - self.cur_style
            if self.cur_style == 1:
                self.mode_label.setText("模式:  同向")
            else:
                self.mode_label.setText("模式:  对称")
            self.m_isMousePressed_left = True
            self.m_isMousePressed_right = True
        for i in range(len(self.m_arcPathList)):
            if self.m_arcPathList[i].contains(translatePoint) or self.m_textPathList[i].contains(translatePoint):
                self.m_pressIndex = i
                if event.button() == Qt.LeftButton:
                    self.m_isMousePressed_left = True
                self.update()
                break

        if event.button() == Qt.RightButton:
            self.m_isMousePressed_right = True

    def mouseReleaseEvent(self, event):
        if self.m_isMousePressed_left:
            self.m_isMousePressed_left = False
        if self.m_isMousePressed_right:
            self.m_isMousePressed_right = False
            self.mCenterRound = QPoint(0, 0)
            self.mDegreePixmap_x = QPixmap(0, 0)
            self.mDegreePixmap_y = QPixmap(0, 0)
            self.Degree_x, self.Degree_y = 0, 0
            self.update()

    def mouseMoveEvent(self, event):
        if self.m_isMousePressed_left:
            point = event.pos() - QPoint(self.width() / 3, self.height() >> 1)
            x = point.x()
            y = -point.y()
            if y >= self.m_arcLength:
                y = self.m_arcLength
            elif y <= 0:
                y = 0
            if x >= self.m_arcLength:
                x = self.m_arcLength
            elif x <= -self.m_arcLength:
                x = -self.m_arcLength
            if x * x + y * y > self.m_arcLength * self.m_arcLength:
                x_y = abs(x) / abs(y)
                _y = self.m_arcLength / math.sqrt(x_y * x_y + 1.0)
                _x = x_y * _y
                if y >= 0:
                    y = abs(_y)
                else:
                    y = -abs(_y)
                if x >= 0:
                    x = abs(_x)
                else:
                    x = -abs(_x)
            self.mCenterRound = QPoint(x, -y)
            angle = self.analysisAngle(x, y)
            if 90 < angle <= 180:
                self.mCurWorkRegion = [self.QUADRANT_UP, self.QUADRANT_LEFT]
            elif 0 < angle < 90:
                self.mCurWorkRegion = [self.QUADRANT_UP, self.QUADRANT_RIGHT]
            elif 180 < angle <= 270:
                self.mCurWorkRegion = [self.QUADRANT_DOWN, self.QUADRANT_LEFT]
            elif 270 < angle < 360:
                self.mCurWorkRegion = [self.QUADRANT_DOWN, self.QUADRANT_RIGHT]
            self.mDegreePixmap_x = self.getPixmap(abs(x))
            self.Degree_x = self.getLineNum(abs(x))
            self.Degree_y = self.getLineNum(abs(y))
            self.mDegreePixmap_y = self.getPixmap(abs(y))
            if self.real_time.isChecked():
                if self.send_num == 10:
                    self.Send()
                    self.send_num = 0
                else:
                    self.send_num += 1
            self.update()

    def analysisAngle(self, x, y):
        angle = math.atan2(abs(y), abs(x)) / (2 * math.acos(-1)) * 360
        if x < 0 < y:
            angle = 180 - angle
        if x < 0 and y < 0:
            angle += 180
        if x > 0 > y:
            angle = 360 - angle
        return angle

    def getPixmap(self, ping):
        if self.cur_style == 1:
            return self.getSignalPixmap(QColor(0x5, 0x00c7, 0xc7), self.getLineNum(ping))
        else:
            return self.getSignalPixmap(QColor(0xef, 0x27, 0x57), self.getLineNum(ping))

    def getColor(self, ping):
        if ping <= 10:
            return QColor(0xea, 0x00, 0x00)
        elif ping <= 20:
            return QColor(0xff, 0x00, 0x80)
        elif ping <= 30:
            return QColor(0xe8, 0x00, 0xe8)
        elif ping <= 40:
            return QColor(0xea, 0xc1, 0x00)
        elif ping <= 50:
            return QColor(0xe1, 0xe1, 0x00)
        elif ping <= 60:
            return QColor(0x9a, 0xff, 0x02)
        elif ping <= 70:
            return QColor(0x00, 0xff, 0xff)
        elif ping <= 80:
            return QColor(0x28, 0x94, 0xff)
        else:
            return QColor(0x6a, 0x6a, 0xff)

    def getLineNum(self, ping):
        return ping // (10 / 632 * self.width()) if ping < (150 / 632 * self.width()) else 15

    def getSignalPixmap(self, color, linenum):
        pixmap = QPixmap(self.m_radius, self.m_radius / 2)
        pixmap.fill(QColor(255, 255, 255, 0))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.HighQualityAntialiasing, True)
        painter.setPen(QPen(color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        i = 1
        xpos = 0
        x_width, y_width = self.m_radius / 35, self.m_radius / 35
        while i <= linenum:
            painter.drawArc(self.m_radius / 2 - i * x_width, self.m_radius / 2 - i * y_width,
                            i * x_width * 2, i * y_width * 2, 53 * 16, 37 * 2 * 16)
            i += 1
            xpos += 1
        return pixmap

    def resizeEvent(self, a0):
        self.m_radius = 150 / 632 * a0.size().width()
        self.m_arcLength = 130 / 632 * a0.size().width()
        self.mCenterRound = QPoint(0, 0)
        self.mDegreePixmap_x = QPixmap(0, 0)
        self.mDegreePixmap_y = QPixmap(0, 0)
        self.Degree_x, self.Degree_y = 0, 0
        self.m_arcPathList = []
        self.m_textPathList = []
        self.addArc(1, 0, 45, 90, self.mSectorColor)
        self.addArc(0, 1, 135, 90, self.mSectorColor)
        self.addArc(-1, 0, 225, 90, self.mSectorColor)
        self.addArc(0, -1, 315, 90, self.mSectorColor)
        self.centerRoundPath = QPainterPath()
        self.centerRoundPath.addEllipse(QPoint(0, 0), self.m_radius - self.m_arcLength + 2,
                                        self.m_radius - self.m_arcLength + 2)
        self.m_arcPathList.append(self.centerRoundPath)
        for i in range(len(self.m_arcPathList)):
            painterPath = QPainterPath()
            self.m_textPathList.append(painterPath)
        self.update()


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    mainWindow = QMoveWidget()
    mainWindow.show()
    sys.exit(app.exec_())
