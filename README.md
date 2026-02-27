# AI-TRAC — Autonomous Tractor Platform

Dashboard web berbasis Flask untuk monitoring dan kontrol traktor otonom berbasis ESP32.

## Cara Menjalankan

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Jalankan server
```bash
python run.py
```

Buka browser: **http://localhost:5000**

## Struktur Project

```
ai-trac/
├── run.py                        # Entry point
├── requirements.txt
├── app/
│   ├── __init__.py              # App factory
│   ├── blueprints/
│   │   ├── main.py              # Landing page
│   │   ├── dashboard.py         # Dashboard utama
│   │   ├── control.py           # Control Mode
│   │   ├── ml.py                # ML Monitoring
│   │   ├── analytics.py         # Analytics
│   │   ├── telemetry.py         # Telemetry IoT
│   │   ├── maintenance.py       # Predictive Maintenance
│   │   ├── history.py           # Riwayat Misi
│   │   ├── settings.py          # Settings
│   │   └── api.py               # REST API + Dummy Data
│   ├── templates/               # Jinja2 templates
│   └── static/
│       ├── css/main.css
│       └── js/main.js
```

## Integrasi Hardware (Placeholder)

File `app/blueprints/api.py` berisi endpoint `/api/control/command` yang siap
dihubungkan ke ESP32 via:
- HTTP Request ke WebServer ESP32 (port 80)
- Serial Communication (/dev/ttyUSB0)
- MQTT Broker
- WebSocket / ROS Bridge

## Fitur

- Dashboard real-time dengan Chart.js
- Control Mode (Manual/Auto/Line Following)
- ML Monitor dengan bounding box simulasi
- Advanced Analytics (4 grafik interaktif)
- Telemetry IoT (GPS, sensor, motor status)
- Predictive Maintenance + Health Score
- Riwayat Misi (sortable, searchable, paginated)
- Dark/Light Mode + Bahasa Indonesia/English
- Sidebar responsive + hamburger menu mobile

## Hardware (ESP32 v1.7.1)

| Komponen | Pin |
|---|---|
| Motor Kanan PWM | GPIO13 |
| Motor Kiri PWM | GPIO14 |
| GPS NEO-6M RX | GPIO16 |
| GPS NEO-6M TX | GPIO17 |
| US Depan TRIG/ECHO | GPIO32/33 |
| FlySky iBUS | GPIO23 |
