import cv2
import time
import os

print('Probing camera indices 0..8 (will try DirectShow on Windows)')
for i in range(9):
    try:
        if os.name == 'nt':
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(i)
        if not cap.isOpened():
            print(f'[{i}] not open')
            continue
        # try to grab a frame
        ret, frame = cap.read()
        if not ret or frame is None:
            print(f'[{i}] opened but no frame')
        else:
            h, w = frame.shape[:2]
            print(f'[{i}] OK — resolution {w}x{h}')
        cap.release()
    except Exception as e:
        print(f'[{i}] error: {e}')
    time.sleep(0.15)
print('Done')
