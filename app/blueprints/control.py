"""
AI-TRAC — control.py (Flask Blueprint) — FIXED v2.1
===================================================
MASALAH SEBELUMNYA:
  - Route terdaftar di blueprint tapi tidak diregister dengan benar
  - Prefix URL tidak konsisten → semua endpoint return 404
  - Browser fetch('/getData') tapi Flask tidak punya route itu

SOLUSI:
  - Blueprint ini harus didaftarkan dengan url_prefix=''  (kosong / root)
  - Atau gunakan url_prefix='/control' dan semua fetch di JS pakai prefix itu
  - File ini menggunakan pendekatan: blueprint prefix = '' (langsung di root)

CARA DAFTAR DI app/__init__.py:
  from app.blueprints.control import control_bp
  app.register_blueprint(control_bp)   # ← TANPA url_prefix agar /getData accessible

KALAU SUDAH PUNYA BLUEPRINT LAIN DI '/' (konflik):
  Daftarkan dengan prefix khusus, lalu edit ESP32_BASE di sini
  dan ubah semua fetch URL di HTML.
"""

import requests
from flask import Blueprint, render_template, jsonify, request

# Blueprint tanpa prefix agar /getData, /setMode, dll bisa diakses langsung
control_bp = Blueprint('control', __name__,
                       template_folder='../templates')

# ── ESP32 config ──────────────────────────────────────────────────────────────
# Ganti dengan IP ESP32 kamu:
#   AP Mode (default)  : 192.168.4.1
#   STA Mode (WiFi)    : cek Serial Monitor ESP32
ESP32_IP      = "192.168.4.1"
ESP32_PORT    = 80
ESP32_TIMEOUT = 3  # detik
ESP32_BASE    = f"http://{ESP32_IP}:{ESP32_PORT}"


# ── Helper proxy ──────────────────────────────────────────────────────────────
def esp_get(path, params=None, timeout=None):
    try:
        r = requests.get(
            f"{ESP32_BASE}{path}",
            params=params,
            timeout=ESP32_TIMEOUT if timeout is None else timeout,
        )
        try:
            return r.json(), r.status_code
        except Exception:
            return {"success": r.status_code < 400, "message": r.text}, r.status_code
    except requests.exceptions.ConnectionError:
        return {"error": "ESP32 unreachable", "connected": False}, 503
    except requests.exceptions.Timeout:
        return {"error": "ESP32 timeout", "connected": False}, 504
    except Exception as e:
        return {"error": str(e), "connected": False}, 500


def esp_post(path, json_body=None, timeout=None):
    try:
        r = requests.post(
            f"{ESP32_BASE}{path}",
            json=json_body or {},
            timeout=ESP32_TIMEOUT if timeout is None else timeout,
            headers={"Content-Type": "application/json"},
        )
        try:
            return r.json(), r.status_code
        except Exception:
            return {"success": True, "message": r.text}, r.status_code
    except requests.exceptions.ConnectionError:
        return {"error": "ESP32 unreachable", "connected": False}, 503
    except requests.exceptions.Timeout:
        return {"error": "ESP32 timeout", "connected": False}, 504
    except Exception as e:
        return {"error": str(e), "connected": False}, 500


# ── Halaman control ───────────────────────────────────────────────────────────
# Note: blueprint already registered with url_prefix="/control"
@control_bp.route('/')
def control_page():
    return render_template('control/index.html', esp32_ip=ESP32_IP)


# ── Data proxy (semua dipanggil oleh JS di frontend) ─────────────────────────

@control_bp.route('/getData')
def get_data():
    data, status = esp_get('/getData')
    return jsonify(data), status


@control_bp.route('/setMode', methods=['GET', 'POST'])
def set_mode():
    if request.method == 'POST':
        body = request.get_json(silent=True) or {}
        mode = body.get('mode', 'manual')
    else:
        mode = request.args.get('mode', 'manual')

    # ESP32 firmware expects mode as query parameter (?mode=manual|auto|line)
    data, status = esp_get('/setMode', params={"mode": mode})

    data.setdefault('success', status < 400)
    data.setdefault('current_mode', mode.upper())
    return jsonify(data), status


@control_bp.route('/emergencyStop', methods=['GET', 'POST'])
def emergency_stop():
    data, status = esp_get('/emergencyStop')
    return jsonify(data), status


@control_bp.route('/clearWaypoints', methods=['GET', 'POST'])
def clear_waypoints():
    data, status = esp_get('/clearWaypoints')
    return jsonify(data), status


@control_bp.route('/startNavigation', methods=['GET', 'POST'])
def start_navigation():
    data, status = esp_get('/startNavigation')
    return jsonify(data), status


# ── Waypoints ─────────────────────────────────────────────────────────────────
@control_bp.route('/api/waypoints/add', methods=['POST'])
def waypoint_add():
    body = request.get_json(silent=True) or {}
    data, status = esp_post('/api/waypoints/add', body)
    return jsonify(data), status


@control_bp.route('/api/waypoints/list')
def waypoint_list():
    data, status = esp_get('/api/waypoints/list')
    return jsonify(data), status


@control_bp.route('/api/waypoints/delete')
def waypoint_delete():
    wp_id = request.args.get('id', '0')
    data, status = esp_get('/api/waypoints/delete', params={"id": wp_id})
    return jsonify(data), status


# ── Track ─────────────────────────────────────────────────────────────────────
@control_bp.route('/api/track/save', methods=['POST'])
def track_save():
    body = request.get_json(silent=True) or {}
    data, status = esp_post('/api/track/save', body)
    return jsonify(data), status


@control_bp.route('/api/track/load')
def track_load():
    data, status = esp_get('/api/track/load')
    return jsonify(data), status


@control_bp.route('/api/track/clear', methods=['POST'])
def track_clear():
    data, status = esp_post('/api/track/clear', {})
    return jsonify(data), status


# ── WiFi ──────────────────────────────────────────────────────────────────────
@control_bp.route('/api/wifi/scan')
def wifi_scan():
    # WiFi scans can take several seconds.
    data, status = esp_get('/api/wifi/scan', timeout=12)
    return jsonify(data), status


@control_bp.route('/api/wifi/connect', methods=['POST'])
def wifi_connect():
    body = request.get_json(silent=True) or {}
    data, status = esp_post('/api/wifi/connect', body)
    return jsonify(data), status


@control_bp.route('/api/wifi/reset', methods=['POST'])
def wifi_reset():
    data, status = esp_post('/api/wifi/reset', {})
    return jsonify(data), status


# ── ESP32 info ────────────────────────────────────────────────────────────────
@control_bp.route('/api/esp32/config')
def esp32_config():
    return jsonify({"ip": ESP32_IP, "port": ESP32_PORT})


@control_bp.route('/api/esp32/setip', methods=['POST'])
def esp32_set_ip():
    """Update ESP32 IP dari frontend tanpa restart Flask."""
    global ESP32_IP, ESP32_BASE
    body = request.get_json(silent=True) or {}
    new_ip = body.get('ip', '').strip()
    if new_ip:
        ESP32_IP   = new_ip
        ESP32_BASE = f"http://{ESP32_IP}:{ESP32_PORT}"
        return jsonify({"success": True, "ip": ESP32_IP})
    return jsonify({"success": False, "error": "No IP provided"}), 400