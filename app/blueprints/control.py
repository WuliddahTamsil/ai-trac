"""
AI-TRAC Blueprint: Control Routes
Updated control.py dengan integration services baru
"""

from flask import Blueprint, render_template, request, jsonify
from app.services import (
    get_gps_processor,
    get_mode_manager,
    get_boundary_recorder,
    ControlMode
)
import logging
import time

logger = logging.getLogger(__name__)

control_bp = Blueprint('control', __name__)

# Service instances
gps_processor = get_gps_processor()
mode_manager = get_mode_manager()
boundary_recorder = get_boundary_recorder()


# ─────────────────────────────────────────────────────────────
# MAIN CONTROL PAGE
# ─────────────────────────────────────────────────────────────

@control_bp.route('/')
def index():
    """Main control page"""
    return render_template('control/index.html')


# ─────────────────────────────────────────────────────────────
# MODE MANAGEMENT
# ─────────────────────────────────────────────────────────────

@control_bp.route('/api/mode/current', methods=['GET'])
def get_current_mode():
    """Get current mode info"""
    return jsonify(mode_manager.get_mode_info())


@control_bp.route('/api/mode/prerequisites', methods=['GET'])
def get_mode_prerequisites():
    """Get prerequisite checks untuk target mode"""
    target_mode = request.args.get('mode', 'SEMI_AUTONOMOUS').upper()
    
    try:
        target_mode_enum = ControlMode[target_mode]
        prereq = mode_manager.check_prerequisites(target_mode_enum)
        
        return jsonify({
            'target_mode': target_mode,
            'checks': [
                {
                    'name': c['name'],
                    'met': c['met'],
                    'message': c['message']
                }
                for c in prereq['checks']
            ],
            'all_met': prereq['ok'],
        })
    except KeyError:
        return jsonify({'error': f'Invalid mode: {target_mode}'}), 400


@control_bp.route('/setMode', methods=['POST', 'GET'])
@control_bp.route('/api/mode/set', methods=['POST'])
def set_mode():
    """
    Set control mode dengan validation
    
    POST/GET params: mode='MANUAL' | 'SEMI_AUTONOMOUS' | 'FULL_AUTONOMOUS'
    POST data: {'mode': str, 'force': bool}
    """
    # Support both GET (legacy) dan POST
    if request.method == 'GET':
        target_mode_str = request.args.get('mode', '').upper()
    else:
        data = request.get_json() or {}
        target_mode_str = data.get('mode', '').upper()
    
    force = request.args.get('force', False) or (request.get_json() or {}).get('force', False)
    
    # Validate mode
    try:
        target_mode = ControlMode[target_mode_str]
    except KeyError:
        return jsonify({
            'success': False,
            'error': f'Invalid mode: {target_mode_str}'
        }), 400
    
    # Attempt mode change
    result = mode_manager.set_mode(target_mode, force=force)
    
    if result['success']:
        # Broadcast ke WebSocket clients (if available)
        try:
            from flask_socketio import emit
            emit('mode_changed', {
                'previous_mode': result['previous_mode'],
                'current_mode': result['current_mode'],
                'timestamp': time.time(),
            }, broadcast=True)
        except Exception as e:
            logger.debug(f"WebSocket broadcast (mode_changed): {e}")
    
    return jsonify(result)


@control_bp.route('/emergencyStop', methods=['POST'])
def emergency_stop():
    """
    Activate emergency stop
    - Halt all motors immediately
    - Lock to E-STOP mode until manual reset
    """
    try:
        result = mode_manager.set_mode(ControlMode.E_STOP, force=True)
        
        # TODO: Send E-STOP command ke ESP32
        # - Set throttle = 0
        # - Set steering = center
        # - Activate relay/solenoid cutoff jika ada
        
        # Broadcast alert ke semua clients
        try:
            from flask_socketio import emit
            emit('emergency_stop_activated', {
                'timestamp': time.time(),
                'message': 'All motors halted — emergency stop engaged'
            }, broadcast=True)
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': 'EMERGENCY STOP activated'
        })
    except Exception as e:
        logger.error(f"E-STOP error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────
# BOUNDARY RECORDING
# ─────────────────────────────────────────────────────────────

@control_bp.route('/api/boundary/start', methods=['POST'])
def start_boundary_recording():
    """Start boundary recording session"""
    data = request.get_json() or {}
    operator_name = data.get('operator_name')
    
    result = boundary_recorder.start_recording(operator_name)
    
    return jsonify(result)


@control_bp.route('/api/boundary/add-point', methods=['POST'])
def add_boundary_point():
    """
    Add GPS point saat recording boundary
    
    POST data: {
        'lat': float,
        'lng': float,
        'hdop': float (optional),
        'speed': float (optional),
        'heading': float (optional),
    }
    """
    data = request.get_json() or {}
    
    result = boundary_recorder.add_boundary_point(
        lat=data.get('lat'),
        lng=data.get('lng'),
        hdop=data.get('hdop'),
        speed=data.get('speed'),
        heading=data.get('heading'),
    )
    
    # Broadcast ke WebSocket
    if result['success']:
        try:
            from flask_socketio import emit
            emit('boundary_point_added', {
                'lat': data.get('lat'),
                'lng': data.get('lng'),
                'count': result['point_count'],
            }, broadcast=True)
        except:
            pass
    
    return jsonify(result)


@control_bp.route('/api/boundary/stop', methods=['POST'])
def stop_boundary_recording():
    """Finalize boundary recording"""
    result = boundary_recorder.stop_recording()
    
    if result['success']:
        # Update mode manager dengan boundary info
        mode_manager.update_system_state({
            'boundary_valid': True,
            'boundary_area_m2': result.get('area_m2', 0),
        })
        
        # Broadcast
        try:
            from flask_socketio import emit
            emit('boundary_recorded', {
                'area_m2': result.get('area_m2'),
                'perimeter_m': result.get('perimeter_m'),
                'boundary': result.get('boundary'),
            }, broadcast=True)
        except:
            pass
    
    return jsonify(result)


@control_bp.route('/api/boundary/clear', methods=['POST'])
def clear_boundary():
    """Clear boundary recording"""
    result = boundary_recorder.clear_recording()
    return jsonify(result)


@control_bp.route('/api/boundary/get', methods=['GET'])
def get_boundary():
    """Get recorded boundary"""
    result = boundary_recorder.get_boundary()
    return jsonify(result)


@control_bp.route('/api/boundary/save', methods=['POST'])
def save_boundary():
    """Save boundary ke file"""
    data = request.get_json() or {}
    filepath = data.get('filepath', '/tmp/boundary.json')
    
    result = boundary_recorder.save_to_file(filepath)
    return jsonify(result)


# ─────────────────────────────────────────────────────────────
# Telemetry endpoint for ESP32 or other devices to push data
# ─────────────────────────────────────────────────────────────
@control_bp.route('/api/telemetry', methods=['POST'])
def receive_telemetry():
    """Receive JSON telemetry from ESP32 and store it for polling endpoints."""
    try:
        data = request.get_json() or {}
        from app.data_generator import set_latest_data
        ok = set_latest_data(data)
        if not ok:
            return jsonify({'success': False, 'error': 'Invalid payload'}), 400
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"telemetry receive error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ------------------------------------------------------------------
# Command endpoint that ESP32 can poll for simple control instructions
# ------------------------------------------------------------------
@control_bp.route('/api/command', methods=['GET'])
def get_command():
    """Return minimal control data (mode, throttle, steering) to the device."""
    try:
        mode_info = mode_manager.get_mode_info()
        # mode_info may contain 'current_mode' or similar
        cmd = {
            'mode': mode_info.get('current_mode') if isinstance(mode_info, dict) else None,
            'throttle': 0,
            'steering': 0
        }
        # in the future, you could inject server-calculated throttle/steering here
        return jsonify(cmd)
    except Exception as e:
        logger.error(f"get_command error: {e}")
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────
# GPS DATA (Legacy polling endpoint)
# ─────────────────────────────────────────────────────────────

@control_bp.route('/getData')
def get_data():
    """
    Legacy endpoint untuk polling GPS/sensor data
    
    NOTE: Untuk production, gunakan WebSocket streaming
    Endpoint ini dijaga untuk backward compatibility
    """
    try:
        from app.data_generator import get_latest_data
        
        raw_data = get_latest_data()  # dari ESP32 atau simulator
        
        # Process GPS melalui Kalman filter
        gps_result = gps_processor.process(raw_data)
        
        # Update mode manager state
        if gps_result:
            gps_data, is_valid = gps_processor.get_current()
            mode_manager.update_system_state({
                'gps_quality_score': gps_data['quality_score'],
                'gps_fix_valid': is_valid,
                'satellite_count': gps_data['satellites'],
            })
        
        return jsonify({
            **raw_data,
            # Processed GPS (filtered + smoothed)
            'latitude': gps_result['lat'] if gps_result else raw_data.get('latitude'),
            'longitude': gps_result['lng'] if gps_result else raw_data.get('longitude'),
            'gpsValid': gps_result and gps_processor.is_valid_fix(),
            'gpsQuality': gps_result['quality_score'] if gps_result else 0,
        })
    except Exception as e:
        logger.error(f"getData error: {e}")
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────
# WAYPOINT MANAGEMENT
# ─────────────────────────────────────────────────────────────

@control_bp.route('/api/waypoints/add', methods=['POST'])
def add_waypoint():
    """Add waypoint"""
    data = request.get_json() or {}
    
    # TODO: Validate coordinates
    # TODO: Save to database/session
    
    return jsonify({'success': True, 'id': 1})


@control_bp.route('/api/waypoints/list', methods=['GET'])
def list_waypoints():
    """List all waypoints"""
    return jsonify({
        'success': True,
        'waypoints': []
    })


@control_bp.route('/api/waypoints/delete', methods=['POST'])
def delete_waypoint():
    """Delete waypoint"""
    return jsonify({'success': True})


# ─────────────────────────────────────────────────────────────
# STATUS/INFO ENDPOINTS
# ─────────────────────────────────────────────────────────────

# WiFi proxy settings - forward scan requests to the ESP32 device
import os
ESP_WIFI_HOST = os.getenv('ESP_WIFI_HOST', 'http://192.168.4.1')

@control_bp.route('/api/wifi/scan')
def proxy_wifi_scan():
    """Proxy the WiFi scan request to the ESP32 unit running its own web server.
    The front end still calls '/api/wifi/scan' on Flask, which then makes a
    server-side request to the ESP. This avoids cross‑origin issues and
    allows AJAX to succeed even when the browser is talking only to the PC.
    """
    try:
        # use standard library to avoid adding new dependencies
        from urllib.request import urlopen, Request
        from urllib.error import URLError, HTTPError
        req = Request(f"{ESP_WIFI_HOST}/api/wifi/scan")
        with urlopen(req, timeout=3) as resp:
            data = resp.read().decode('utf-8')
            return data, resp.getcode(), [('Content-Type','application/json')]
    except Exception as e:
        return jsonify({'networks': [], 'error': str(e)}), 500


@control_bp.route('/api/status', methods=['GET'])
def get_status():
    """Get system status summary"""
    gps_data, gps_valid = gps_processor.get_current()
    mode_info = mode_manager.get_mode_info()
    boundary_status = boundary_recorder.get_status()
    
    return jsonify({
        'mode': mode_info,
        'gps': {
            'valid': gps_valid,
            'quality': gps_data['quality_score'],
            'satellites': gps_data['satellites'],
            'hdop': gps_data['hdop'],
            'lat': gps_data['lat'],
            'lng': gps_data['lng'],
        },
        'boundary': boundary_status,
        'timestamp': time.time(),
    })


# ─────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────

@control_bp.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    gps_data, gps_valid = gps_processor.get_current()
    
    return jsonify({
        'status': 'ok',
        'gps_processor': 'ok',
        'mode_manager': 'ok',
        'boundary_recorder': 'ok',
        'gps_valid': gps_valid,
    })
