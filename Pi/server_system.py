import os
import sys
import queue
import random
import select
import socket
import threading
import time
import serial
import serial.tools.list_ports
import cv2

root = os.path.curdir

sys.path.append(os.path.join(root, "object_track"))
sys.path.append(os.path.join(root, "object_track/pysot"))
sys.path.append(os.path.join(root, "object_track/weights"))

from object_track.track_system import Track_System

"""
mode:
    input:
    (1 << 0), 9个舵机的控制 (包括每个舵机是角度和转动时间)  
    (1 << 1), 鱼形态动作控制 (先判断是否为鱼形态, 否则跳过, 是则执行前进, 左转, 右转的鱼体波控制(传递参数: 模式, 动作, 动作的幅度和频率))
    (1 << 2), 跟踪控制 (先判断是否启动摄像头, 是则开启目标跟踪, (图传返回当前图像, 直到PC端返回box/通过目标检测获取box))
    (1 << 3), 检测控制 (开启则跟踪控制无需通过PC传递box, 当目标丢失时重新检测)
    (1 << 4), 摄像头控制 (是否读取摄像头)
    (1 << 5), 路径规划 (将PC端的路径参数传递给飞腾派, 飞腾派控制舵机执行)
    (1 << 6), 姿态控制 (结合6轴陀螺仪的偏角和加速度, 通过肩关节和腰部舵机对头部进行调整)
    (1 << 7), stm32复位
    (1 << 8), 图传
    (1 << 9), 自主控制
    
    output:
    三轴偏移, 三轴加速度 
"""


class Control_Manager(object):
    def __init__(self):
        self.mode = 0
        self.cur_mode = 0
        self.arg = None  # 最近一次获取的命令参数
        # ----------- parameter ---------------- #
        # ------ Handful ------- #
        self.hand_data = None
        # ------- Swim --------- #
        self.is_swim = True
        self.swim_mode, self.A, self.k = 0, 0, 0
        # ------- Track -------- #
        self.is_track = False
        self.is_first = True
        self.init_rect = None
        self.track_system = Track_System()
        # ------- Detect ------- #
        self.is_detect = False
        # ------- Camera ------- #
        self.is_camera_open = False
        self.frame = None
        self.camera = cv2.VideoCapture("v4l2src device=/dev/video0 ! videoconvert ! video/x-raw, width=320, "
                                       "height=240, framerate=30/1 !  appsink", cv2.CAP_GSTREAMER)
        # ------- Route -------- #
        self.is_route = False
        self.route_data = None
        self.route_index = None
        # ------- Gesture ------ #
        self.is_gesture = False
        # ------- Reset -------- #
        self.is_stm32_reset = False
        # ------- Bionic ------- #
        self.is_bionic = False
        self.sep = 0
        # ----- video_trans ----- #
        self.is_video_trans = False
        self.video_trans = cv2.VideoWriter("appsrc ! videoconvert ! x264enc tune=zerolatency bitrate=200 qp-max=1 "
                                           "qp-min=1 ! rtph264pay ! udpsink buffer-size=6000000 host=192.168.29.203 "
                                           "port=5000 async=true max-lateness=-1 qos-dscp=10 max-bitrate=200000000 ",
                                           cv2.CAP_GSTREAMER, 0, 30, (320, 240), True)
        # ------- Other -------- #
        self.close = False
        self.is_finish = False  # 判断cur_mode是否成功执行
        self.server = None
        self.inputs = []
        self.outputs = []
        self.message_queues = {}
        self.thread = threading.Thread(target=self.Server_Init)
        # ------- init --------- #
        os.system("echo 0 > /sys/class/gpio/gpio496/value")
        self.serial_stm32 = serial.Serial(str(list(serial.tools.list_ports.comports())[0]), 115200, 8, 'N', 1)

    def run(self):
        self.thread.start()
        self.Processing_Command()

    def closeEvent(self):
        self.camera.release()
        self.video_trans.release()
        self.server.close()
        self.serial_stm32.close()
        self.thread.join()

    def Bionic(self):
        time.sleep(random.random() + 1)
        self.Servo_Send(random.randint(2, 5),
                        random.choice([-1, 1]) * random.choices([0, 5, 6, 7, 8],
                                                                weights=[0.3, 0.3, 0.2, 0.1, 0.1])[0], 0)
        time.sleep(random.random() + 1.5)
        self.Servo_Send(0, 0, 0)

    def Track(self):
        if self.is_first:
            if self.is_detect:
                self.track_system.Search_Object(self.frame)
            else:
                if self.init_rect:
                    self.track_system.Set_Template(self.frame, self.track_system)
        else:
            self.track_system.Get_Track(self.frame)
            cv2.rectangle(self.frame, (self.track_system.bbox[0], self.track_system.bbox[1]),
                          (self.track_system.bbox[0] + self.track_system.bbox[2],
                           self.track_system.bbox[1] + self.track_system.bbox[3]),
                          (0, 255, 0), 3)

    def Serial_Rec(self):
        pass

    def Serial_Send(self, text):
        self.serial_stm32.write(bytes.fromhex(text))

    def Servo_Send(self, a, k, c):
        try:
            for s in self.inputs:
                if s is not self.server:
                    self.message_queues[s].put('(0, ({}, {}, {}))'.format(int(a), int(k), int(c)) + '\n')
                    if s not in self.outputs:
                        self.outputs.append(s)
        except KeyError:
            pass

    def STM32_Reset(self):
        os.system("echo 1 > /sys/class/gpio/gpio496/value")
        time.sleep(1)
        os.system("echo 0 > /sys/class/gpio/gpio496/value")

    def Server_Init(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setblocking(0)
        ip_port = ('127.0.0.1', 3411)
        # ip_port = ('192.168.137.1', 3411)
        self.server.bind(ip_port)
        self.server.listen(5)
        self.inputs.append(self.server)
        while self.inputs and not self.close:
            # print(len(self.inputs), len(self.outputs))  # 在这里加停止命令 需要把视觉、巡航相关参数也调零
            rs, ws, es = select.select(self.inputs, self.outputs, self.inputs)
            for s in rs:
                if s is self.server:
                    connection, address = s.accept()
                    print('connecting from', address)
                    connection.setblocking(0)
                    self.inputs.append(connection)
                    self.outputs.append(connection)
                    self.message_queues[connection] = queue.Queue()
                else:
                    # ---------- 状态机第一层 ----------- #
                    try:
                        data = s.recv(4096).decode('utf-8')
                    except ConnectionResetError:
                        es.append(s)
                        continue
                    if data != '':
                        print('receive {} from {}'.format(data, s.getpeername()))
                        try:
                            command = eval(data)
                            self.cur_mode, self.arg = command[0], command[1]
                        except Exception:
                            self.cur_mode, self.arg = None, None
                        if self.cur_mode:
                            while not self.is_finish:
                                continue
                            self.mode |= self.cur_mode
                            self.is_finish = False
                        # self.message_queues[s].put(data)
                        if s not in self.outputs:
                            self.outputs.append(s)

                    else:
                        print('closing', s.getpeername())
                        if s in self.outputs:
                            self.outputs.remove(s)
                        self.inputs.remove(s)
                        s.close()
                        del self.message_queues[s]
            for s in ws:
                try:
                    message_queue = self.message_queues.get(s)
                    send_data = ''
                    if message_queue is not None:
                        send_data = message_queue.get_nowait()
                except queue.Empty:
                    pass
                else:
                    if send_data:
                        try:
                            s.send(send_data.encode('utf-8'))
                        except ConnectionResetError:
                            es.append(s)
                            continue

            for s in es:
                print('exception condition on', s.getpeername())
                self.inputs.remove(s)
                if s in self.outputs:
                    self.outputs.remove(s)
                s.close()
                del self.message_queues[s]

            time.sleep(0.01)

    def Processing_Command(self):
        while not self.close:
            time.sleep(0.01)
            # ----------- 状态机第二层 ------------- #
            if not self.is_finish:
                # ------- 待机 -------- #
                if self.cur_mode is None:
                    if self.sep == 1 << 10:
                        if self.mode == 0 and self.is_bionic:
                            self.mode |= (1 << 9)
                    else:
                        self.sep += 1
                else:
                    self.sep = 0
                    if self.cur_mode != 1 << 9:
                        self.mode &= ~(1 << 9)

                # ------ 9个舵机控制 ------- #
                if self.mode & (1 << 0):
                    self.mode &= ~(1 << 0)
                    if self.serial_stm32 and self.serial_stm32.writable():
                        self.Serial_Send(self.arg)

                # ------ 鱼形态 ------ #
                if self.mode & (1 << 1):
                    self.mode &= ~(1 << 1)
                    if self.is_swim and not self.is_route and not self.is_track:
                        self.Serial_Send(self.arg)  # 无论停止还是执行都通过命令控制

                # -------- 目标跟踪 ------- #
                if self.mode & (1 << 2):
                    if self.cur_mode == (1 << 2):
                        if self.arg is False:
                            self.mode &= ~(1 << 2)
                            self.is_track = False
                        else:
                            if isinstance(self.arg, tuple):
                                self.init_rect = self.arg
                            self.is_track = True

                # ------- 目标检测 ------- #
                if self.mode & (1 << 3):
                    if self.cur_mode == (1 << 3) and self.arg is False:
                        self.mode &= ~(1 << 3)
                        self.is_detect = False
                    else:
                        self.is_detect = True

                # ------ 摄像头控制 ------- #
                if self.mode & (1 << 4):
                    if self.cur_mode == (1 << 4) and self.arg is False:
                        self.mode &= ~(1 << 4)
                        self.is_camera_open = False
                    else:
                        self.is_camera_open = True

                # -------- 路径控制 -------- #
                if self.mode & (1 << 5):
                    if self.cur_mode == (1 << 5):
                        if self.arg is False:
                            self.mode &= ~(1 << 5)
                            self.is_route = False
                        else:
                            self.is_route = True
                            self.route_data = self.arg
                    else:
                        self.is_route = True

                # -------- 姿态控制 --------- #
                if self.mode & (1 << 6):
                    if self.cur_mode == (1 << 6) and self.arg is False:
                        self.mode &= ~(1 << 6)
                        self.is_gesture = False
                    else:
                        self.is_gesture = True

                # -------- stm32复位 -------- #
                if self.mode & (1 << 7):
                    self.mode &= ~(1 << 7)
                    self.STM32_Reset()

                # -------- 图传功能 ---------- #
                if self.mode & (1 << 8):
                    if self.cur_mode == (1 << 8) and self.arg is False:
                        self.mode &= ~(1 << 8)
                        self.is_video_trans = False
                    else:
                        self.is_video_trans = True

                # --------- 自主控制 ---------- #
                if self.mode & (1 << 9):
                    if self.cur_mode == 1 << 8 and self.arg is False:
                        self.mode &= ~(1 << 8)
                        self.is_bionic = False

                    else:
                        self.is_bionic = True

                self.cur_mode, self.arg, self.is_finish = None, None, True
            # ----------------------------------- #
            # ------------ 状态机第三层 ----------- #
            if self.is_camera_open:
                ret, self.frame = self.camera.read()

            if self.is_track:
                self.Track()

            elif self.is_route:
                pass

            if self.is_gesture:  # 控制前面三个舵机
                pass

            if self.is_video_trans:
                self.video_trans.write(self.frame)

            if self.is_bionic:
                pass


if __name__ == '__main__':
    manager = Control_Manager()
    manager.run()
