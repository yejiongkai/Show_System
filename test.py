import numpy as np
import cv2
from datetime import datetime


img = np.ones((400, 400, 6), dtype='uint8')*255

img = cv2.copyMakeBorder(img, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=(0, 0, 0))

cv2.imshow("img1", img[:, :, :3])
cv2.imshow("img2", img[:, :, 3:])

cv2.waitKey(0)