from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QApplication
from PyQt5.QtCore import pyqtSignal, Qt, QThread, QSize
from PyQt5.QtGui import QImage, QPixmap
import sys
import cv2
import time


class VideoWidget(QWidget):
    Order = pyqtSignal(str)
    Update_Image = pyqtSignal(QImage)

    def __init__(self, parent=None):
        super(VideoWidget, self).__init__(parent)
        self.is_camera_open = False
        self.is_track = False
        self.is_detect = False
        self.is_trans = False
        self.window_resize = False
        self.video = None
        self.frame = None
        self.Update_Image.connect(self.Show_Image)
        self.trans_thread = QThread(self)
        self.trans_thread.run = self.Get_Video
        self.SetupUI()

    def SetupUI(self):
        self.Screen = QLabel(self)
        self.Screen.setFixedSize(320, 240)
        self.Screen.setStyleSheet('border-width: 6px;border-style: solid;\
                        border-color: rgb(0, 0, 0);background-color: rgb(255,255,255, 120);')

        self.open_camera = QPushButton("打开摄像头")
        self.open_camera.clicked.connect(self.Camera)
        self.open_trans = QPushButton("启动图传")
        self.open_trans.clicked.connect(self.Trans)
        self.open_track = QPushButton("启动跟踪")
        self.open_track.clicked.connect(self.Track)
        self.open_detect = QPushButton("启动检测")
        self.open_detect.clicked.connect(self.Detect)

        self.button_layout_1 = QHBoxLayout()
        self.button_layout_1.addWidget(self.open_camera)
        self.button_layout_1.addWidget(self.open_trans)

        self.button_layout_2 = QHBoxLayout()
        self.button_layout_2.addWidget(self.open_track)
        self.button_layout_2.addWidget(self.open_detect)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.Screen)
        self.main_layout.addLayout(self.button_layout_1)
        self.main_layout.addLayout(self.button_layout_2)
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(self.main_layout)

    def Trans(self):
        if self.is_trans:
            self.open_trans.setText("启动图传")
            self.is_trans = False
            self.trans_thread.wait(3)
            self.Order.emit(str((1 << 8, False)))
        else:
            self.open_trans.setText("关闭图传")
            self.is_trans = True
            self.Order.emit(str((1 << 8, True)))
            self.trans_thread.start()

    def Camera(self):
        if self.is_camera_open:
            self.open_camera.setText("打开摄像头")
            self.is_camera_open = False
            self.Order.emit(str((1 << 4, False)))

        else:
            self.open_camera.setText("关闭摄像头")
            self.is_camera_open = True
            self.Order.emit(str((1 << 4, True)))

    def Track(self):
        if self.is_track:
            self.open_track.setText("启动跟踪")
            self.is_track = False
            self.Order.emit(str((1 << 2, False)))
        else:
            self.open_track.setText("关闭跟踪")
            self.is_track = True
            self.Order.emit(str((1 << 2, True)))

    def Detect(self):
        if self.is_detect:
            self.open_detect.setText("启动跟踪")
            self.is_detect = False
            self.Order.emit(str((1 << 3, False)))
        else:
            self.open_detect.setText("关闭跟踪")
            self.is_detect = True
            self.Order.emit(str((1 << 3, True)))

    def Show_Image(self, image):
        self.Screen.setPixmap(QPixmap.fromImage(image))

    def Get_Video(self):
        self.video = cv2.VideoCapture('udpsrc port=5000 caps="application/x-rtp, media=video, clock-rate=90000, '
                                      'encoding-name=H264, payload=96" !'
                                      'rtph264depay ! decodebin ! videoconvert ! appsink sync=true', cv2.CAP_GSTREAMER)
        while self.is_trans:
            ret, self.frame = self.video.read()
            frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
            image_height, image_width, image_depth = frame.shape
            image = QImage(frame.data, image_width, image_height,  # 创建QImage格式的图像，并读入图像信息
                           QImage.Format_RGB888)
            self.Update_Image.emit(image)

        self.video.release()

    def mousePressEvent(self, a0):
        if a0.button() == Qt.RightButton and self.childAt(a0.pos()) == self.Screen and self.frame is not None:
            cv2.namedWindow("selectROI", cv2.WND_PROP_FULLSCREEN)
            init_rect = list(cv2.selectROI("selectROI", self.frame, False, False))
            init_rect[0] /= 320
            init_rect[1] /= 240
            init_rect[2] /= 320
            init_rect[3] /= 240
            self.Order.emit(str((1 << 2, init_rect)))
            if init_rect:
                self.open_track.setText("关闭跟踪")
                self.is_track = True
            cv2.waitKey(1)
            cv2.destroyAllWindows()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    demo = VideoWidget()
    demo.show()
    sys.exit(app.exec_())
