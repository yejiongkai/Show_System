import argparse
import time
import ncnn
from ncnn.model_zoo import get_model
import cv2
import torch
import torch.nn.functional as F
import numpy as np
from pysot.core.config import cfg
from pysot.utils.anchor import Anchors


class Track_System(object):
    model_template = None
    model_track = None
    model_detect = None
    ncnn_powersave = 2
    ncnn_omp_num_threads = 4
    model_num_threads = 4
    # ----dynamic---- #
    zf, xf, center_pos, size, channel_average, score, bbox = None, None, None, None, None, None, []
    move_pred = np.array([0, 0])
    # -----fixed----- #
    score_size, hanning, window, anchor_num, anchors = [None for i in range(5)]
    track_thresh = 0.05
    detect_thresh = 0.9

    miss_object_thresh = 200
    miss_object_num = 1

    move_pred_epoch = 20
    move_pred_num = 0
    move_pred_center_pos = None

    use_detect = False

    detect_types = ["person", "dog"]

    def __init__(self):
        super(Track_System, self).__init__()
        self.cfg_Init()
        self.ncnn_Init()
        self.parameter_Init()
        self.model_Init()

    def cfg_Init(self):
        parser = argparse.ArgumentParser(description='tracking demo')
        parser.add_argument('--config', default='object_track/config.yaml', type=str,
                            help='config file')
        args = parser.parse_args()
        cfg.merge_from_file(args.config)
        cfg.CUDA = torch.cuda.is_available() and cfg.CUDA

    def parameter_Init(self):
        self.score_size = ((cfg.TRACK.INSTANCE_SIZE - cfg.TRACK.EXEMPLAR_SIZE)
                           // cfg.ANCHOR.STRIDE + 1 + cfg.TRACK.BASE_SIZE)
        self.hanning = np.hanning(self.score_size)
        self.anchor_num = len(cfg.ANCHOR.RATIOS) * len(cfg.ANCHOR.SCALES)
        self.window = np.tile(np.outer(self.hanning, self.hanning).flatten(), self.anchor_num)
        self.anchors = self.generate_anchor()

    def model_Init(self):
        self.model_template = ncnn.Net()
        self.model_template.opt.num_threads = self.model_num_threads
        self.model_template.load_param("object_track/weights/model_template.ncnn.param")
        self.model_template.load_model("object_track/weights/model_template.ncnn.bin")

        self.model_track = ncnn.Net()
        self.model_track.opt.num_threads = self.model_num_threads
        self.model_track.load_param("object_track/weights/model_track.ncnn.param")
        self.model_track.load_model("object_track/weights/model_track.ncnn.bin")

        # self.model_detect = get_model(
        #     "yolov5s",
        #     target_size=640,
        #     prob_threshold=self.detect_thresh,
        #     nms_threshold=0.45,
        #     num_threads=4,
        #     use_gpu=False,
        # )

        self.model_detect = get_model(
            "retinaface",
            prob_threshold=self.detect_thresh,
            nms_threshold=0.45,
            num_threads=self.model_num_threads,
            use_gpu=False,
        )

    def ncnn_Init(self):
        ncnn.set_omp_num_threads(self.ncnn_omp_num_threads)
        ncnn.set_cpu_powersave(self.ncnn_powersave)

    def Set_Template(self, frame, init_rect):
        self.center_pos = np.array([init_rect[0] + (init_rect[2] - 1) / 2,
                                    init_rect[1] + (init_rect[3] - 1) / 2])
        self.move_pred_center_pos = self.center_pos.copy()
        self.size = np.array([init_rect[2], init_rect[3]])

        # calculate z crop size
        w_z = self.size[0] + cfg.TRACK.CONTEXT_AMOUNT * np.sum(self.size)
        h_z = self.size[1] + cfg.TRACK.CONTEXT_AMOUNT * np.sum(self.size)
        s_z = round(np.sqrt(w_z * h_z))

        # calculate channle average
        self.channel_average = np.mean(frame, axis=(0, 1))

        # get crop
        z_crop = self.get_subwindow(frame, self.center_pos,
                                    cfg.TRACK.EXEMPLAR_SIZE,
                                    s_z, self.channel_average).contiguous()
        with self.model_template.create_extractor() as ex:
            ex.input("in0", ncnn.Mat(z_crop.squeeze(0).numpy()).clone())
            _, self.zf = ex.extract("out0")

    def Get_Track(self, frame):
        w_z = self.size[0] + cfg.TRACK.CONTEXT_AMOUNT * np.sum(self.size)
        h_z = self.size[1] + cfg.TRACK.CONTEXT_AMOUNT * np.sum(self.size)
        s_z = round(np.sqrt(w_z * h_z))
        scale_z = cfg.TRACK.EXEMPLAR_SIZE / s_z
        s_x = s_z * (cfg.TRACK.INSTANCE_SIZE / cfg.TRACK.EXEMPLAR_SIZE)
        x_crop = self.get_subwindow(frame, self.center_pos,
                                    cfg.TRACK.INSTANCE_SIZE,
                                    round(s_x), self.channel_average).contiguous()
        with self.model_template.create_extractor() as ex:
            ex.input("in0", ncnn.Mat(x_crop.squeeze(0).numpy()).clone())
            _, self.xf = ex.extract("out0")
        with self.model_track.create_extractor() as ex:
            ex.input("in0", self.zf)
            ex.input("in1", self.xf)
            _, out0 = ex.extract("out0")
            _, out1 = ex.extract("out1")
            outputs = [torch.from_numpy(np.array(out0)).unsqueeze(0), torch.from_numpy(np.array(out1)).unsqueeze(0)]
        score = self._convert_score(outputs[0])
        pred_bbox = self._convert_bbox(outputs[1], self.anchors)
        s_c = self.change(self.sz(pred_bbox[2, :], pred_bbox[3, :]) /
                          (self.sz(self.size[0] * scale_z, self.size[1] * scale_z)))

        # aspect ratio penalty
        r_c = self.change((self.size[0] / self.size[1]) /
                          (pred_bbox[2, :] / pred_bbox[3, :]))
        penalty = np.exp(-(r_c * s_c - 1) * cfg.TRACK.PENALTY_K)
        pscore = penalty * score

        # window penalty
        pscore = pscore * (1 - cfg.TRACK.WINDOW_INFLUENCE) + \
                 self.window * cfg.TRACK.WINDOW_INFLUENCE
        best_idx = np.argmax(pscore)
        self.score = score[best_idx]
        if self.score >= self.track_thresh and self.miss_object_num <= self.miss_object_thresh:
            bbox = pred_bbox[:, best_idx] / scale_z
            lr = penalty[best_idx] * score[best_idx] * cfg.TRACK.LR
            cx = bbox[0] + self.center_pos[0]
            cy = bbox[1] + self.center_pos[1]
            # smooth bbox
            width = self.size[0] * (1 - lr) + bbox[2] * lr
            height = self.size[1] * (1 - lr) + bbox[3] * lr
            # clip boundary
            cx, cy, width, height = self._bbox_clip(cx, cy, width, height, frame.shape[:2])
            # udpate state
            self.center_pos = np.array([cx, cy])
            self.size = np.array([width, height])
            self.bbox = [cx - width / 2,
                         cy - height / 2,
                         width,
                         height]
            self.bbox = list(map(int, self.bbox))
            self.move_pred_num += 1
            if self.move_pred_num >= self.move_pred_epoch:
                self.move_pred = ((self.center_pos - self.move_pred_center_pos) /
                                  (self.move_pred_epoch + self.miss_object_num)).astype('int8')
                self.move_pred_center_pos = self.center_pos
                self.move_pred_num = 0

            self.miss_object_num = 0
            return self.score, self.bbox
        else:
            if self.miss_object_num > self.miss_object_thresh:
                if self.use_detect:
                    self.Search_Object(frame)
                else:
                    print("object have lose")
            else:
                self.miss_object_num += 1
                self.center_pos += self.move_pred
                self.center_pos[0] = min(max(0, self.center_pos[0]), frame.shape[0])
                self.center_pos[1] = min(max(0, self.center_pos[1]), frame.shape[1])
                self.bbox[0] = self.bbox[0] + self.move_pred[0]
                self.bbox[1] = self.bbox[1] + self.move_pred[1]

            return self.score, self.bbox

    def Search_Object(self, frame):
        print("-------Start search object--------")
        objects = self.model_detect(frame)
        if objects:
            print("-------find search object--------")
            box_sizes = np.array([o.rect.w * o.rect.h for o in objects])
            max_size_id = np.argmax(box_sizes)
            self.Set_Template(frame, (objects[max_size_id].rect.x, objects[max_size_id].rect.y,
                                      objects[max_size_id].rect.w, objects[max_size_id].rect.h))
            self.miss_object_num = 0
            # if self.model_detect.class_names[int(objects[max_size_id].label)] in self.detect_types:

    def generate_anchor(self):
        anchors = Anchors(cfg.ANCHOR.STRIDE,
                          cfg.ANCHOR.RATIOS,
                          cfg.ANCHOR.SCALES)
        anchor = anchors.anchors
        x1, y1, x2, y2 = anchor[:, 0], anchor[:, 1], anchor[:, 2], anchor[:, 3]
        anchor = np.stack([(x1 + x2) * 0.5, (y1 + y2) * 0.5, x2 - x1, y2 - y1], 1)
        total_stride = anchors.stride
        anchor_num = anchor.shape[0]
        anchor = np.tile(anchor, self.score_size * self.score_size).reshape((-1, 4))
        ori = - (self.score_size // 2) * total_stride
        xx, yy = np.meshgrid([ori + total_stride * dx for dx in range(self.score_size)],
                             [ori + total_stride * dy for dy in range(self.score_size)])
        xx, yy = np.tile(xx.flatten(), (anchor_num, 1)).flatten(), \
            np.tile(yy.flatten(), (anchor_num, 1)).flatten()
        anchor[:, 0], anchor[:, 1] = xx.astype(np.float32), yy.astype(np.float32)
        return anchor

    def _bbox_clip(self, cx, cy, width, height, boundary):
        cx = max(0, min(cx, boundary[1]))
        cy = max(0, min(cy, boundary[0]))
        width = max(10, min(width, boundary[1]))
        height = max(10, min(height, boundary[0]))
        return cx, cy, width, height

    def _convert_score(self, score):

        score = score.permute(1, 2, 3, 0).contiguous().view(2, -1).permute(1, 0)
        score = F.softmax(score, dim=1).data[:, 1].cpu().numpy()
        return score

    def _convert_bbox(self, delta, anchor):
        delta = delta.permute(1, 2, 3, 0).contiguous().view(4, -1)
        delta = delta.data.cpu().numpy()

        delta[0, :] = delta[0, :] * anchor[:, 2] + anchor[:, 0]
        delta[1, :] = delta[1, :] * anchor[:, 3] + anchor[:, 1]
        delta[2, :] = np.exp(delta[2, :]) * anchor[:, 2]
        delta[3, :] = np.exp(delta[3, :]) * anchor[:, 3]
        return delta

    def change(self, r):
        return np.maximum(r, 1. / r)

    def sz(self, w, h):
        pad = (w + h) * 0.5
        return np.sqrt((w + pad) * (h + pad))

    def get_subwindow(self, im, pos, model_sz, original_sz, avg_chans):
        """
        args:
            im: bgr based image
            pos: center position
            model_sz: exemplar size
            s_z: original size
            avg_chans: channel average
        """
        if isinstance(pos, float):
            pos = [pos, pos]
        sz = original_sz
        im_sz = im.shape
        c = (original_sz + 1) / 2
        # context_xmin = round(pos[0] - c) # py2 and py3 round
        context_xmin = np.floor(pos[0] - c + 0.5)
        context_xmax = context_xmin + sz - 1
        # context_ymin = round(pos[1] - c)
        context_ymin = np.floor(pos[1] - c + 0.5)
        context_ymax = context_ymin + sz - 1
        left_pad = int(max(0., -context_xmin))
        top_pad = int(max(0., -context_ymin))
        right_pad = int(max(0., context_xmax - im_sz[1] + 1))
        bottom_pad = int(max(0., context_ymax - im_sz[0] + 1))

        context_xmin = context_xmin + left_pad
        context_xmax = context_xmax + left_pad
        context_ymin = context_ymin + top_pad
        context_ymax = context_ymax + top_pad

        r, c, k = im.shape
        if any([top_pad, bottom_pad, left_pad, right_pad]):
            size = (r + top_pad + bottom_pad, c + left_pad + right_pad, k)
            te_im = np.zeros(size, np.uint8)
            te_im[top_pad:top_pad + r, left_pad:left_pad + c, :] = im
            if top_pad:
                te_im[0:top_pad, left_pad:left_pad + c, :] = avg_chans
            if bottom_pad:
                te_im[r + top_pad:, left_pad:left_pad + c, :] = avg_chans
            if left_pad:
                te_im[:, 0:left_pad, :] = avg_chans
            if right_pad:
                te_im[:, c + left_pad:, :] = avg_chans
            im_patch = te_im[int(context_ymin):int(context_ymax + 1),
                       int(context_xmin):int(context_xmax + 1), :]
        else:
            im_patch = im[int(context_ymin):int(context_ymax + 1),
                       int(context_xmin):int(context_xmax + 1), :]

        if not np.array_equal(model_sz, original_sz):
            im_patch = cv2.resize(im_patch, (model_sz, model_sz))
        im_patch = im_patch.transpose(2, 0, 1)
        im_patch = im_patch[np.newaxis, :, :, :]
        im_patch = im_patch.astype(np.float32)
        im_patch = torch.from_numpy(im_patch)
        return im_patch


def get_frames():
    cap = cv2.VideoCapture(r"C:\Users\YJK\Desktop\目标跟踪\pysot\demo\b.mp4")
    # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
    # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    # warmup
    for i in range(1):
        cap.read()
    while True:
        ret, frame = cap.read()
        # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # frame = cv2.merge([frame, frame, frame])
        if ret:
            yield frame
        else:
            break


def show(track_system):
    first_frame = True
    cv2.namedWindow("camera", cv2.WND_PROP_FULLSCREEN)

    for i, frame in enumerate(get_frames()):
        if first_frame:
            init_rect = cv2.selectROI("camera", frame, False, False)
            track_system.Set_Template(frame, init_rect)
            first_frame = False
        else:
            if i % 1 == 0:
                outputs = track_system.Get_Track(frame)
            cv2.rectangle(frame, (track_system.bbox[0], track_system.bbox[1]),
                          (track_system.bbox[0] + track_system.bbox[2], track_system.bbox[1] + track_system.bbox[3]),
                          (0, 255, 0), 3)
            cv2.imshow("camera", frame)
            cv2.waitKey(1)


def main():
    ts = Track_System()
    show(ts)


if __name__ == "__main__":
    start = time.monotonic()
    main()
    print(time.monotonic() - start)
