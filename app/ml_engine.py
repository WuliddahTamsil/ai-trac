import os
import threading
import time
import cv2

# safe import Ultralyics YOLO model; will raise if not installed
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

# determine model path relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'yolo_ml', 'versi_1', 'best.pt')

# choose capture source from environment variable for flexibility
CAM_SOURCE = os.getenv('ML_CAM_SOURCE', '0')
# if it's numeric use int, else keep string (e.g. rtsp://...)
if CAM_SOURCE.isdigit():
    CAM_SOURCE = int(CAM_SOURCE)

# globals shared by blueprint
lock = threading.Lock()
last_frame = None  # BGR numpy array
last_info = {
    'label': '--',
    'confidence': 0.0,
    'quality_score': 0.0,
    'total_detections': 0,
    'avg_quality': 0.0,
    'bbox': {'x': 0, 'y': 0, 'w': 0, 'h': 0}
}

# control whether capture is active; can be toggled by endpoints
# start disabled to avoid opening laptop camera immediately on import
capture_enabled = False

def enable_capture():
    global capture_enabled
    capture_enabled = True

def disable_capture():
    global capture_enabled
    capture_enabled = False

def toggle_capture():
    global capture_enabled
    capture_enabled = not capture_enabled
    return capture_enabled

def is_capture_enabled():
    return bool(capture_enabled)

# helper functions

def analyze_results(results, frame_shape):
    """Simple analysis of YOLO results to produce quality metrics."""
    h, w = frame_shape[:2]
    info = {
        'label': '--',
        'confidence': 0.0,
        'quality_score': 0.0,
        'total_detections': 0,
        'avg_quality': 0.0,
        'bbox': {'x': 0, 'y': 0, 'w': 0, 'h': 0}
    }
    if not results or results.boxes is None or len(results.boxes) == 0:
        return info

    boxes = results.boxes
    confidences = boxes.conf.cpu().numpy()
    info['total_detections'] = len(boxes)
    info['avg_quality'] = round(float(confidences.mean()) * 100, 1)
    # choose highest confidence box for label & bbox
    idx = int(confidences.argmax())
    cls_idx = int(boxes.cls[idx])
    # names mapping (ultralytics stores results.names)
    info['label'] = results.names.get(cls_idx, str(cls_idx))
    info['confidence'] = float(confidences[idx])

    # compute coverage area percentage
    areas = []
    for i in range(len(boxes)):
        x1, y1, x2, y2 = boxes.xyxy[i]
        areas.append((x2 - x1) * (y2 - y1))
    coverage = sum(areas) / (w * h) * 100
    # uniformity: penalty when box areas vary a lot
    try:
        import numpy as _np
        arr = _np.array(areas)
        uniformity = max(0.0, 100.0 - float(_np.std(arr) / (_np.mean(arr) + 1e-6) * 100.0))
    except Exception:
        uniformity = 100.0
    info['coverage'] = float(coverage)
    info['uniformity'] = float(uniformity)
    # simple quality metric combining coverage & uniformity
    info['quality_score'] = float(min(100.0, coverage * 0.6 + uniformity * 0.4))

    # bounding box of chosen index
    x1, y1, x2, y2 = boxes.xyxy[idx]
    info['bbox'] = {
        'x': int(x1),
        'y': int(y1),
        'w': int(x2 - x1),
        'h': int(y2 - y1)
    }
    return info


def capture_loop():
    global last_frame, last_info, capture_enabled
    cap = None

    # load model if available
    if YOLO is None:
        print("[ml_engine] Ultralyics YOLO not installed; stream/inference disabled")
        return

    try:
        model = YOLO(MODEL_PATH)
        print(f"[ml_engine] Loaded YOLO model from {MODEL_PATH}")
    except Exception as e:
        print(f"[ml_engine] Failed to load model: {e}")
        model = None

    while True:
        if not capture_enabled:
            # if camera active, release it to free resource
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
                cap = None
            time.sleep(0.1)
            continue

        # ensure capture open
        if cap is None:
            # prefer DirectShow on Windows when using numeric camera index
            try:
                if isinstance(CAM_SOURCE, int) and os.name == 'nt':
                    cap = cv2.VideoCapture(CAM_SOURCE, cv2.CAP_DSHOW)
                else:
                    cap = cv2.VideoCapture(CAM_SOURCE)
            except Exception:
                cap = cv2.VideoCapture(CAM_SOURCE)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            if not cap.isOpened():
                print(f"[ml_engine] WARNING: Unable to open camera source {CAM_SOURCE}")
                # don't busy-loop when camera missing
                time.sleep(1.0)
                continue

        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue

        # inference on frame if model loaded
        if model is not None:
            try:
                results = model(frame)[0]
                info = analyze_results(results, frame.shape)
            except Exception as e:
                # on inference error, keep minimal info
                info = last_info.copy()
                info['label'] = '--'
                info['confidence'] = 0.0
                print(f"[ml_engine] inference error: {e}")
        else:
            info = last_info.copy()

        with lock:
            last_frame = frame.copy()
            last_info = info

        # small sleep to limit fps
        time.sleep(0.03)

# start thread automatically when module imported
thread = threading.Thread(target=capture_loop, daemon=True)
thread.start()

# helpers used by blueprints

def get_current():
    with lock:
        frame_copy = None if last_frame is None else last_frame.copy()
        info_copy = last_info.copy()
    return frame_copy, info_copy


def gen_frames():
    """Generator producing MPEG frames for streaming."""
    while True:
        frame, _ = get_current()
        if frame is None:
            time.sleep(0.05)
            continue
        ret, jpeg = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        time.sleep(0.03)