import random
import math
import time
from datetime import datetime, timedelta
import threading

_start_time = time.time()
_base_lat = -6.5971
_base_lng = 106.8060

# Latest telemetry pushed by external device (ESP32)
_latest_lock = threading.Lock()
_latest_data = None

def set_latest_data(d):
    """Store last telemetry received from external device.

    The ESP32 sketch may use short names like ``lat``/``lon``; normalize them
    to what the Flask backend expects (``latitude``/``longitude``) so the web
    interface shows valid GPS status even if the device uses different field
    names.
    """
    global _latest_data
    with _latest_lock:
        if not isinstance(d, dict):
            return False
        # copy so we can mutate
        d = d.copy()
        # normalize common synonyms
        if 'lat' in d and 'latitude' not in d:
            d['latitude'] = d.pop('lat')
        if 'lon' in d and 'longitude' not in d:
            d['longitude'] = d.pop('lon')
        if 'sat' in d and 'satellites' not in d:
            d['satellites'] = d.pop('sat')
        # ensure timestamp fields
        d.setdefault('timestamp', datetime.now().strftime("%H:%M:%S"))
        d['_received_at'] = time.time()
        _latest_data = d
    return True

def get_latest_data():
    """Return latest telemetry if available, otherwise synthetic telemetry."""
    with _latest_lock:
        if _latest_data is not None:
            return _latest_data.copy()
    return get_telemetry()


def get_telemetry():
    t = time.time() - _start_time
    return {
        "battery": round(max(20, 95 - (t / 600) * 30 + random.uniform(-1, 1)), 1),
        "speed": round(abs(math.sin(t / 10) * 8 + random.uniform(-0.5, 0.5)), 1),
        "temperature": round(32 + math.sin(t / 30) * 5 + random.uniform(-0.5, 0.5), 1),
        "humidity": round(65 + math.sin(t / 20) * 10 + random.uniform(-1, 1), 1),
        "latitude": round(_base_lat + math.sin(t / 50) * 0.001, 6),
        "longitude": round(_base_lng + math.cos(t / 50) * 0.001, 6),
        "satellites": random.randint(7, 12),
        "hdop": round(random.uniform(0.8, 1.5), 2),
        "heading": round((t * 5) % 360, 1),
        "altitude": round(250 + math.sin(t / 40) * 3, 1),
        "distance_front": round(max(10, 150 + math.sin(t / 3) * 80 + random.uniform(-5, 5)), 1),
        "distance_left": round(max(10, 80 + math.sin(t / 4) * 40 + random.uniform(-3, 3)), 1),
        "distance_right": round(max(10, 80 + math.cos(t / 4) * 40 + random.uniform(-3, 3)), 1),
        "motor_left": round(abs(math.sin(t / 10)) * 80 + random.uniform(-2, 2), 1),
        "motor_right": round(abs(math.sin(t / 10)) * 80 + random.uniform(-2, 2), 1),
        "gps_valid": True,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }


def get_ml_detection():
    conditions = ["Tanah Kering", "Tanah Basah", "Tanah Ideal", "Bebatuan", "Rumput Tebal"]
    qualities = ["Excellent", "Good", "Fair", "Poor"]
    weights_cond = [0.2, 0.25, 0.35, 0.1, 0.1]
    weights_qual = [0.3, 0.4, 0.2, 0.1]
    condition = random.choices(conditions, weights_cond)[0]
    quality = random.choices(qualities, weights_qual)[0]
    confidence = round(random.uniform(0.72, 0.99), 3)
    quality_score = round(random.uniform(55, 98), 1)
    return {
        "condition": condition,
        "confidence": confidence,
        "quality": quality,
        "quality_score": quality_score,
        "detections_count": random.randint(1, 5),
        "bbox": {
            "x": random.randint(50, 300),
            "y": random.randint(50, 200),
            "w": random.randint(80, 200),
            "h": random.randint(60, 150),
        },
        "avg_quality": round(random.uniform(72, 92), 1),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }


def get_battery_history(points=20):
    now = datetime.now()
    data = []
    val = 95.0
    for i in range(points):
        ts = now - timedelta(minutes=(points - i) * 3)
        val = max(20, val - random.uniform(0.2, 0.8))
        data.append({"time": ts.strftime("%H:%M"), "value": round(val, 1)})
    return data


def get_area_history(points=20):
    now = datetime.now()
    data = []
    val = 0.0
    for i in range(points):
        ts = now - timedelta(minutes=(points - i) * 3)
        val += random.uniform(0.05, 0.2)
        data.append({"time": ts.strftime("%H:%M"), "value": round(val, 2)})
    return data


def get_soil_quality_history(points=20):
    now = datetime.now()
    data = []
    for i in range(points):
        ts = now - timedelta(minutes=(points - i) * 3)
        data.append({"time": ts.strftime("%H:%M"), "value": round(random.uniform(65, 95), 1)})
    return data


def get_op_duration_history(points=10):
    now = datetime.now()
    data = []
    for i in range(points):
        date = now - timedelta(days=(points - i))
        data.append({"date": date.strftime("%d/%m"), "hours": round(random.uniform(2, 8), 1)})
    return data


def get_maintenance():
    t = time.time() - _start_time
    health = round(max(40, 92 - (t / 3600) * 5 + random.uniform(-1, 1)), 1)
    components = [
        {"name": "Motor Kiri", "health": round(health + random.uniform(-5, 5), 1), "next_service": "15 hari"},
        {"name": "Motor Kanan", "health": round(health + random.uniform(-5, 5), 1), "next_service": "15 hari"},
        {"name": "Sensor Ultrasonik", "health": round(health + random.uniform(-8, 8), 1), "next_service": "30 hari"},
        {"name": "GPS Module", "health": round(98 + random.uniform(-2, 2), 1), "next_service": "60 hari"},
        {"name": "Baterai", "health": round(max(40, 95 - (t / 600) * 30), 1), "next_service": "7 hari"},
        {"name": "Roda & Drive", "health": round(health + random.uniform(-10, 5), 1), "next_service": "20 hari"},
    ]
    for c in components:
        c["health"] = max(10, min(100, c["health"]))
        if c["health"] >= 80:
            c["status"] = "good"
        elif c["health"] >= 60:
            c["status"] = "warning"
        else:
            c["status"] = "critical"
    return {"overall_health": health, "components": components}


def get_notifications():
    items = [
        {"id": 1, "type": "warning", "title": "Baterai Rendah", "message": "Level baterai mendekati 30%", "time": "2 mnt lalu", "read": False},
        {"id": 2, "type": "info", "title": "Servis Terjadwal", "message": "Perawatan motor dalam 7 hari", "time": "15 mnt lalu", "read": False},
        {"id": 3, "type": "success", "title": "Misi Selesai", "message": "Operasi Area B berhasil diselesaikan", "time": "1 jam lalu", "read": True},
        {"id": 4, "type": "error", "title": "Obstacle Terdeteksi", "message": "Halangan di jalur depan, navigasi ulang", "time": "2 jam lalu", "read": True},
        {"id": 5, "type": "info", "title": "GPS Terkunci", "message": "12 satelit terhubung, akurasi tinggi", "time": "3 jam lalu", "read": True},
    ]
    return items


def get_operation_history():
    ops = []
    statuses = ["Selesai", "Selesai", "Selesai", "Terhenti", "Selesai"]
    areas_list = ["Lahan A", "Lahan B", "Lahan C", "Lahan D", "Lahan E"]
    modes = ["Auto", "Manual", "Auto", "Auto", "Line Following"]
    for i in range(20):
        date = datetime.now() - timedelta(days=i, hours=random.randint(0, 12))
        ops.append({
            "id": f"OP-{1000 + i}",
            "date": date.strftime("%d/%m/%Y %H:%M"),
            "area": areas_list[i % 5],
            "duration": f"{random.randint(1, 7)}j {random.randint(0, 59)}m",
            "coverage": round(random.uniform(0.2, 3.5), 2),
            "mode": modes[i % 5],
            "status": statuses[i % 5],
            "quality_score": round(random.uniform(72, 98), 1),
        })
    return ops
