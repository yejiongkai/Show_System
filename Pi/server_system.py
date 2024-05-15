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
from PID_Control import Gesture_PID_Control

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


def format_hex(n):
    return "".join(f"{n:02x}")


class Servo(object):
    def __init__(self, name, ratio_range, enable=False):
        self.name = name
        self.ratio = ratio_range // 2
        self.use_time = 1000  # ms
        self.ratio_range = ratio_range
        self.enable = enable


class Control_Manager(object):
    def __init__(self):
        self.mode = 0
        self.cur_mode = 0
        self.arg = None  # 最近一次获取的命令参数
        # ----------- parameter ---------------- #
        # ------- Servo -------- #
        self.servo_map = {0: "腰部旋转", 1: "左脚底", 2: "右脚底", 3: "左肩关节",
                          4: "右肩关节", 5: "左小腿", 6: "右小腿", 7: "左大腿", 8: "右大腿"}
        self.servos = []
        for i in range(9):
            if i == 0:
                servo = Servo(self.servo_map[i], 360, True)
            elif i == 1 or i == 2 or i == 7 or i == 8:
                servo = Servo(self.servo_map[i], 270, False)
            else:
                if i == 3 or i == 4:
                    servo = Servo(self.servo_map[i], 180, True)
                else:
                    servo = Servo(self.servo_map[i], 180, False)
            self.servos.append(servo)
        # ------ Handful ------- #
        self.is_hand = False
        self.hand_data = None
        # ------- Swim --------- #
        self.is_swim = False
        self.swim_data = None
        # ------- Track -------- #
        self.is_track = False
        self.is_first = True
        self.init_rect = None
        self.track_epoch = 1
        self.track_num = self.track_epoch
        self.track_system = Track_System(self)
        # ------- Detect ------- #
        self.is_detect = False
        # ------- Camera ------- #
        self.video_width, self.video_height, self.video_fps = 640, 480, 30
        self.is_camera_open = False
        self.frame = None
        self.camera = cv2.VideoCapture("v4l2src device=/dev/video0 ! videoconvert ! video/x-raw, width={}, "
                                       "height={}, framerate={}/1 !  appsink".format(self.video_width,
                                                                                     self.video_height, self.video_fps),
                                       cv2.CAP_GSTREAMER)
        # ------- Route -------- #
        self.is_route = False
        self.route_data = None
        self.route_index = None
        # ------- Gesture ------ #
        self.is_gesture = False
        self.gesture_init_num = 0
        self.pitch, self.roll, self.yaw = None, None, None
        self.gesture_pid_control = Gesture_PID_Control(self.video_width, self.video_height)
        # ------- Reset -------- #
        self.is_stm32_reset = False
        # ------- Bionic ------- #
        self.is_bionic = False
        self.sep = 0
        # ----- video_trans ----- #
        self.is_video_trans = False
        self.trans_width, self.trans_height, self.trans_fps = 320, 240, 30
        self.video_trans = cv2.VideoWriter(
                            "appsrc ! videoconvert ! x264enc tune=zerolatency bitrate=400 qp-max=20 "
                            "qp-min=10 ! rtph264pay ! udpsink buffer-size=12000000 host=192.168.29.132 "
                            "port=5000 async=true max-lateness=-1 qos-dscp=10 max-bitrate=200000000 ",
                            cv2.CAP_GSTREAMER, 0, self.trans_fps, (self.trans_width, self.trans_height),
                            True)
        # ------- Other -------- #
        self.close = False
        self.is_finish = False  # 判断cur_mode是否成功执行
        self.server = None
        self.inputs = []
        self.outputs = []
        self.message_queues = {}
        self.thread_server = threading.Thread(target=self.Server_Init)
        self.thread_serial = threading.Thread(target=self.Serial_Rec)
        # ------- init --------- #
        os.system("echo 1 > /sys/class/gpio/gpio496/value")
        os.system("echo 1 > /sys/class/gpio/gpio445/value")
        self.serial_stm32 = serial.Serial('/dev/ttyAMA2', 115200, 8, 'N', 1)

    def run(self):
        self.thread_server.start()
        self.thread_serial.start()
        self.Processing_Command()

    def closeEvent(self):
        self.camera.release()
        self.video_trans.release()
        self.server.close()
        self.serial_stm32.close()
        self.thread_server.join()
        self.thread_serial.join()

    def Bionic(self):
        pass

    def Swim_Control(self, sync_mode, motion_mode, T, c1_amp):
        list_bytes = [format_hex(0x02),
                      format_hex(sync_mode),
                      format_hex(motion_mode),
                      format_hex(T),
                      format_hex(c1_amp)]
        list_bytes += ["00"] * 45
        list_bytes += [format_hex(0x0d), format_hex(0x0c)]
        send_data = " ".join(list_bytes)
        self.Serial_Send(send_data)

    def Servo_Control(self):
        list_bytes = [format_hex(0x01), "00", "00", "00", "00"]
        for i in range(9):
            enable = 1 if self.servos[i].enable else 0
            ratio = int(self.servos[i].ratio)
            use_time = int(self.servos[i].use_time)
            list_bytes.append(format_hex(enable))
            list_bytes.append(format_hex(ratio >> 8))
            list_bytes.append(format_hex(ratio & 0xff))
            list_bytes.append(format_hex(use_time >> 8))
            list_bytes.append(format_hex(use_time & 0xff))
        list_bytes += [format_hex(0x0d), format_hex(0x0c)]
        send_data = " ".join(list_bytes)
        self.Serial_Send(send_data)

    # 主要使用以下两个函数，控制舵机角度
    def Set_Servo_Shoulder(self, value=0, enable=True):
        self.servos[3].ratio = max(min(self.servos[3].ratio + value, self.servos[3].ratio_range), 0)
        self.servos[3].enable = enable
        self.servos[4].ratio = max(min(self.servos[4].ratio - value, self.servos[4].ratio_range), 0)
        self.servos[4].enable = enable

    def Set_Servo_Waist(self, value=0, enable=True):
        self.servos[0].ratio = max(min(self.servos[0].ratio + value, self.servos[0].ratio_range), 0)
        self.servos[0].enable = enable

    def Set_Servo_Reset(self):
        for i in range(9):
            self.servos[i].ratio = self.servos[i].ratio_range / 2
            self.servos[i].use_time = 5000
            self.servos[i].enable = True

    def Track(self):
        if self.frame is None:
            return

        if self.is_first:
            if self.is_detect:
                if self.track_system.Search_Object(self.frame):
                    self.is_first = False
            else:
                if self.init_rect:
                    self.track_system.Set_Template(self.frame, self.init_rect)
                    self.is_first = False
        else:
            if self.track_num == self.track_epoch:
                self.track_system.Get_Track(self.frame)
                self.track_num = 0
            else:
                self.track_num += 1
            cv2.rectangle(self.frame, (self.track_system.bbox[0], self.track_system.bbox[1]),
                          (self.track_system.bbox[0] + self.track_system.bbox[2],
                           self.track_system.bbox[1] + self.track_system.bbox[3]),
                          (0, 255, 0), 3)

    def Gesture_Control(self):
        # 目标丢失
        if self.track_system.score < self.track_system.track_thresh:
            value_v, value_h = self.gesture_pid_control.get_Control_Value(False, None, None)
        else:
            object_x, object_y = self.track_system.bbox[0] + self.track_system.bbox[2]/2, \
                self.track_system.bbox[1] + self.track_system.bbox[3]/2
            value_v, value_h = self.gesture_pid_control.get_Control_Value(True, object_x, object_y)

        self.Set_Servo_Shoulder(value_v, True)
        self.Set_Servo_Waist(value_h, True)

    def Serial_Rec(self):
        while not self.close:
            if self.serial_stm32 and self.serial_stm32.readable():
                try:
                    data = list(map(int, self.serial_stm32.readline()[:-1].decode('utf-8').split("\t")))
                    self.pitch, self.roll, self.yaw = data[4]/10, data[5]/10, data[6]/10
                    if data:
                        self.Message_Send("&"+str(data))
                except Exception:
                    pass

            time.sleep(0.01)

    def Serial_Send(self, text):
        if len(text) == 155:
            self.serial_stm32.write(bytes.fromhex(text))
            time.sleep(0.02)

    def Message_Send(self, buff):
        try:
            for s in self.inputs:
                if s is not self.server:
                    self.message_queues[s].put(buff + '\n')
                    if s not in self.outputs:
                        self.outputs.append(s)
        except KeyError:
            pass

    def STM32_Reset(self):
        os.system("echo 0 > /sys/class/gpio/gpio496/value")
        os.system("echo 0 > /sys/class/gpio/gpio445/value")
        time.sleep(1)
        os.system("echo 1 > /sys/class/gpio/gpio496/value")
        os.system("echo 1 > /sys/class/gpio/gpio445/value")

    def Server_Init(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setblocking(0)
        # ip_port = ('127.0.0.1', 3411)
        ip_port = ('192.168.29.191', 3411)
        self.server.bind(ip_port)
        self.server.listen(5)
        self.inputs.append(self.server)
        print("bind ip from {}, port from {}".format(*ip_port))
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
                        while not self.is_finish:
                                continue
                        try:
                            command = eval(data)
                            self.cur_mode, self.arg = command[0], command[1]
                        except Exception as e:
                            print(str(e))
                            self.cur_mode, self.arg = None, None
                        if self.cur_mode:
                            self.mode |= self.cur_mode
                            self.is_finish = False
                        # self.message_queues[s].put(data)
                        if s not in self.outputs:
                            self.outputs.append(s)

                    else:
                        try:
                            print('closing', s.getpeername())
                            if s in self.outputs:
                                self.outputs.remove(s)
                            self.inputs.remove(s)
                            s.close()
                            del self.message_queues[s]
                        except OSError:
                            continue
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
                try:
                    print('exception condition on', s.getpeername())
                    self.inputs.remove(s)
                    if s in self.outputs:
                        self.outputs.remove(s)
                    s.close()
                    del self.message_queues[s]
                except OSError:
                    continue

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
                            # self.Message_Send("Start autonomous control")
                    else:
                        self.sep += 1
                else:
                    self.sep = 0
                    if self.cur_mode != 1 << 9:
                        self.mode &= ~(1 << 9)
                        # self.Message_Send("Stop autonomous control")

                # ------ 9个舵机控制 ------- #
                if self.mode & (1 << 0):
                    if self.cur_mode == (1 << 0):
                        self.is_hand = True
                        self.hand_data = self.arg.copy()

                # ------ 鱼形态 ------ #
                if self.mode & (1 << 1):
                    if self.cur_mode == (1 << 1):
                        self.is_swim = True
                        self.swim_data = self.arg.copy()

                # -------- 目标跟踪 ------- #
                if self.mode & (1 << 2):
                    if self.cur_mode == (1 << 2):
                        if self.arg is False:
                            self.mode &= ~(1 << 2)
                            self.is_track = False
                            self.is_first = True
                            self.Message_Send("Stop object tracking")
                        else:
                            if isinstance(self.arg, list):
                                self.init_rect = self.arg
                                self.init_rect[0] *= self.video_width
                                self.init_rect[1] *= self.video_height
                                self.init_rect[2] *= self.video_width
                                self.init_rect[3] *= self.video_height
                                self.track_system.miss_object_num = 1
                            self.is_track = True
                            self.Message_Send("Start object tracking")

                # ------- 目标检测 ------- #
                if self.mode & (1 << 3):
                    if self.cur_mode == (1 << 3):
                        if self.arg is False:
                            self.mode &= ~(1 << 3)
                            self.is_detect = False
                            self.track_system.use_detect = False
                            self.Message_Send("Stop object detecting")
                        else:
                            self.is_detect = True
                            self.track_system.use_detect = True
                            self.Message_Send("Start object detecting")

                # ------ 摄像头控制 ------- #
                if self.mode & (1 << 4):
                    if self.cur_mode == (1 << 4):
                        if self.arg is False:
                            self.mode &= ~(1 << 4)
                            self.is_camera_open = False
                            self.Message_Send("Close camera")
                        else:
                            self.is_camera_open = True
                            self.Message_Send("Open camera")

                # -------- 路径控制 -------- #
                if self.mode & (1 << 5):
                    if self.cur_mode == (1 << 5):
                        if self.arg is False:
                            self.mode &= ~(1 << 5)
                            self.is_route = False
                            self.Message_Send("Stop Path Tracing")
                        else:
                            self.is_route = True
                            self.route_data = self.arg
                            self.Message_Send("Start Path Tracing")

                # -------- 姿态控制 --------- #
                if self.mode & (1 << 6):
                    if self.cur_mode == (1 << 6):
                        if self.arg is False:
                            self.mode &= ~(1 << 6)
                            self.is_gesture = False
                            self.gesture_init_num = 0
                            self.Message_Send("Stop gesture control")
                        else:
                            self.is_gesture = True
                            self.Message_Send("Start gesture control")

                # -------- stm32复位 -------- #
                if self.mode & (1 << 7):
                    self.mode &= ~(1 << 7)
                    self.STM32_Reset()
                    self.Message_Send("Start STM32 Reset")

                # -------- 图传功能 ---------- #
                if self.mode & (1 << 8):
                    if self.cur_mode == (1 << 8):
                        if self.arg is False:
                            self.mode &= ~(1 << 8)
                            self.is_video_trans = False
                            self.Message_Send("Stop video transmission")
                        else:
                            self.is_video_trans = True
                            self.Message_Send("Start video transmission")

                # --------- 自主控制 ---------- #
                if self.mode & (1 << 9):
                    if self.cur_mode == 1 << 9:
                        if self.arg is False:
                            self.mode &= ~(1 << 9)
                            self.is_bionic = False
                            self.Message_Send("Stop autonomous control")

                        else:
                            self.is_bionic = True
                            self.Message_Send("Start autonomous control")

                self.cur_mode, self.arg, self.is_finish = None, None, True
            # ----------------------------------- #
            # ------------ 状态机第三层 ----------- #
            if self.is_camera_open:
                if self.camera.isOpened():
                    ret, self.frame = self.camera.read()
                else:
                    self.Message_Send("Cannot get frame")

            if self.is_hand:
                self.mode &= ~(1 << 0)
                if self.serial_stm32 and self.serial_stm32.writable() and not self.is_gesture and not self.is_route:
                    self.Serial_Send(self.hand_data)
                    self.Message_Send("Perform manual control")
                self.is_hand = False

            if self.is_swim:
                self.mode &= ~(1 << 1)
                if (not self.is_route and not self.is_track
                        and self.serial_stm32 and self.serial_stm32.writable()):
                    self.Serial_Send(self.swim_data)  # 无论停止还是执行都通过命令控制
                    self.Message_Send("Perform fish form control")
                self.is_swim = False

            if self.is_track:
                self.Track()

            if self.is_route:
                pass

            if self.is_gesture:  # 控制前面三个舵机
                if self.gesture_init_num < 500:
                    if self.gesture_init_num == 0:
                        self.Message_Send("Gesture is initializing")
                        self.Set_Servo_Reset()
                    else:
                        self.gesture_init_num += 1
                else:
                    self.Gesture_Control()
                self.Servo_Control()

            if self.is_video_trans:
                if self.frame is not None:
                    frame = cv2.resize(self.frame, (self.trans_width, self.trans_height))
                    self.video_trans.write(frame)

            if self.is_bionic:
                pass


if __name__ == '__main__':
    manager = Control_Manager()
    manager.run()
