import numpy as np
import cv2



img = np.ones((6, 100, 100))

print(np.pad(img, ((0, 0), (2, 2), (2, 2)), mode='constant', constant_values=((0, 0), (114, 114), (114, 114))))
print(np.pad(img, ((0, 0), (2, 2), (2, 2)), mode='constant', constant_values=((0, 0), (114, 114), (114, 114))).transpose((2, 1, 0)).shape)

# print(cv2.copyMakeBorder(img, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(114, 114, 144, 114, 114, 114)).shape)