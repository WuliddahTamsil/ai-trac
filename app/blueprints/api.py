from flask import Blueprint, jsonify
import random
import math
import time

api_bp = Blueprint('api', __name__)

def gen_battery():
    t = time.time()
    return round(75 + 15 * math.sin(t / 60) + random.uniform(-2, 2), 1)

def gen_speed():
    return round(random.uniform(0.8, 3.5), 2)

def gen_temp():
    return round(random.uniform(38, 52), 1)

def gen_soil_quality():
    labels = ['Optimal', 'Good', 'Fair', 'Poor']
    weights = [0.45, 0.30, 0.15, 0.10]
    return random.choices(labels, weights)[0]

@api_bp.route('/telemetry')
def telemetry():
    t = time.time()
    return jsonify({
        'battery': gen_battery(),
        'speed': gen_speed(),
        'temperature': gen_temp(),
        'latitude': -6.5971 + random.uniform(-0.001, 0.001),
        'longitude': 106.8060 + random.uniform(-0.001, 0.001),
        'satellites': random.randint(6, 12),
        'hdop': round(random.uniform(0.8, 2.5), 2),
        'altitude': round(random.uniform(180, 200), 1),
        'heading': round((t * 10) % 360, 1),
        'front_dist': round(random.uniform(20, 150), 1),
        'left_dist': round(random.uniform(15, 120), 1),
        'right_dist': round(random.uniform(15, 120), 1),
        'mode': random.choice(['MANUAL', 'AUTO', 'AUTO']),
        'connected': True,
        'uptime': int(t % 86400),
        'area_covered': round(random.uniform(1200, 1800), 1),
        'soil_quality': gen_soil_quality(),
        'confidence': round(random.uniform(0.82, 0.98), 3),
        'timestamp': int(t * 1000)
    })

@api_bp.route('/battery-chart')
def battery_chart():
    t = time.time()
    data = []
    for i in range(20):
        ts = t - (19 - i) * 30
        val = round(75 + 15 * math.sin(ts / 60) + random.uniform(-2, 2), 1)
        data.append({'x': int(ts * 1000), 'y': val})
    return jsonify(data)

@api_bp.route('/analytics/summary')
def analytics_summary():
    return jsonify({
        'total_area': round(random.uniform(8500, 9200), 1),
        'total_hours': round(random.uniform(42, 50), 1),
        'avg_speed': round(random.uniform(1.8, 2.4), 2),
        'avg_soil_quality': round(random.uniform(78, 88), 1),
        'fuel_saved': round(random.uniform(12, 18), 1),
        'efficiency': round(random.uniform(88, 96), 1)
    })

@api_bp.route('/notifications')
def notifications():
    items = [
        {'id': 1, 'type': 'warning', 'msg': 'Baterai di bawah 20%', 'time': '2 min ago'},
        {'id': 2, 'type': 'info', 'msg': 'Mode AUTO aktif', 'time': '15 min ago'},
        {'id': 3, 'type': 'success', 'msg': 'Misi selesai — Area B3', 'time': '1 jam ago'},
        {'id': 4, 'type': 'danger', 'msg': 'Obstacle terdeteksi, traktor berhenti', 'time': '2 jam ago'},
        {'id': 5, 'type': 'info', 'msg': 'GPS signal locked (12 satelit)', 'time': '3 jam ago'},
    ]
    return jsonify(items)

@api_bp.route('/ml/detection')
def ml_detection():
    classes = ['Tanah Kering', 'Tanah Lembab', 'Tanah Optimal', 'Gulma Terdeteksi']
    weights = [0.15, 0.25, 0.45, 0.15]
    label = random.choices(classes, weights)[0]
    return jsonify({
        'label': label,
        'confidence': round(random.uniform(0.82, 0.98), 3),
        'quality_score': round(random.uniform(70, 95), 1),
        'total_detections': random.randint(1420, 1500),
        'avg_quality': round(random.uniform(80, 90), 1),
        'bbox': {
            'x': random.randint(50, 200),
            'y': random.randint(50, 150),
            'w': random.randint(100, 200),
            'h': random.randint(80, 160)
        }
    })

@api_bp.route('/maintenance/health')
def maintenance_health():
    return jsonify({
        'overall': round(random.uniform(82, 92), 1),
        'components': [
            {'name': 'Motor Kanan', 'health': round(random.uniform(88, 98), 1), 'next_service': '45 jam'},
            {'name': 'Motor Kiri', 'health': round(random.uniform(85, 95), 1), 'next_service': '45 jam'},
            {'name': 'GPS Module', 'health': round(random.uniform(92, 99), 1), 'next_service': '120 jam'},
            {'name': 'Baterai', 'health': round(random.uniform(75, 90), 1), 'next_service': '10 jam'},
            {'name': 'Sensor Ultrasonik', 'health': round(random.uniform(90, 99), 1), 'next_service': '200 jam'},
            {'name': 'Kamera', 'health': round(random.uniform(88, 96), 1), 'next_service': '150 jam'},
        ]
    })

@api_bp.route('/history')
def history():
    missions = []
    statuses = ['Selesai', 'Selesai', 'Selesai', 'Dibatalkan', 'Selesai']
    areas = ['Blok A-1', 'Blok A-2', 'Blok B-1', 'Blok B-2', 'Blok C-1', 'Blok C-3']
    modes = ['AUTO', 'AUTO', 'MANUAL', 'AUTO', 'LINE']
    for i in range(25):
        missions.append({
            'id': f'MSN-{1000+i}',
            'date': f'2025-0{(i%3)+1}-{(i%28)+1:02d}',
            'area': random.choice(areas),
            'mode': random.choice(modes),
            'duration': f'{random.randint(1,4)}h {random.randint(0,59)}m',
            'coverage': f'{random.randint(400,1800)} m²',
            'avg_speed': f'{round(random.uniform(1.2, 3.2), 1)} m/s',
            'status': random.choice(statuses)
        })
    return jsonify(missions)

@api_bp.route('/control/command', methods=['POST'])
def control_command():
    # Placeholder for hardware bridge
    return jsonify({'status': 'ok', 'msg': 'Command received (hardware bridge pending)'})
