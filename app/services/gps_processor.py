"""
AI-TRAC GPS Processor Service
Handles GPS filtering, validation, and smoothing using Kalman filter
"""

import numpy as np
import math
import time
from collections import deque


class KalmanFilter:
    """1D Kalman Filter untuk GPS coordinate smoothing"""
    
    def __init__(self, process_variance=1e-5, measurement_variance=1e-4, initial_value=0):
        """
        Initialize Kalman filter
        
        Args:
            process_variance: Model noise (Q) — how much we trust the model
            measurement_variance: Measurement noise (R) — how much we trust GPS
            initial_value: Starting coordinate value
        """
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        
        # State
        self.value = initial_value
        self.estimate_error = 1.0
        
        # Tuning untuk GPS (higher R = filter more aggressively)
        self.Q = process_variance
        self.R = measurement_variance
    
    def update(self, measurement):
        """
        Update filter dengan GPS measurement
        
        Returns: Filtered/smoothed value
        """
        # Prediction
        prediction = self.value
        prediction_error = self.estimate_error + self.Q
        
        # Update
        kalman_gain = prediction_error / (prediction_error + self.R)
        self.value = prediction + kalman_gain * (measurement - prediction)
        self.estimate_error = (1 - kalman_gain) * prediction_error
        
        return self.value


class GPSQualityValidator:
    """Validate GPS data quality using multiple criteria"""
    
    # Quality thresholds
    EXCELLENT_HDOP = 2.0   # < 2m horizontal accuracy
    GOOD_HDOP = 5.0        # 2-5m
    POOR_HDOP = 10.0       # > 10m (reject)
    
    MIN_SATELLITES = 4      # Need minimum 4 for fix
    GOOD_SATELLITES = 8     # Ideal is 8+
    
    MAX_SPEED = 15.0        # m/s (54 km/h) — Max for tractor
    MAX_ACCELERATION = 2.0  # m/s² — Tractor can't accelerate faster
    
    MAX_POSITION_JUMP = 5.0 # meters — Outlier detection
    
    def __init__(self):
        self.last_lat = None
        self.last_lng = None
        self.last_time = None
        self.last_speed = 0
    
    def validate(self, lat, lng, hdop, satellites, speed, heading):
        """
        Comprehensive GPS quality check
        
        Returns: {
            'valid': bool,
            'quality_score': 0.0-1.0,
            'issues': [str],
            'warnings': [str]
        }
        """
        issues = []
        warnings = []
        scores = []
        
        # 1. HDOP validation
        if hdop is None or hdop > self.POOR_HDOP:
            issues.append(f"HDOP {hdop} too high (>10m)")
            hdop_score = 0.0
        elif hdop > self.GOOD_HDOP:
            warnings.append(f"HDOP {hdop:.1f}m (moderate accuracy)")
            hdop_score = 0.5
        elif hdop > self.EXCELLENT_HDOP:
            hdop_score = 0.8
        else:
            hdop_score = 1.0
        scores.append(hdop_score)
        
        # 2. Satellite count
        if satellites < self.MIN_SATELLITES:
            issues.append(f"Only {satellites} satellites (need {self.MIN_SATELLITES})")
            sat_score = 0.0
        elif satellites < self.GOOD_SATELLITES:
            warnings.append(f"Only {satellites} satellites (ideal {self.GOOD_SATELLITES}+)")
            sat_score = 0.6
        else:
            sat_score = 1.0
        scores.append(sat_score)
        
        # 3. Outlier detection (position jump)
        if self.last_lat is not None and self.last_lng is not None:
            distance = self._haversine(self.last_lat, self.last_lng, lat, lng)
            if distance > self.MAX_POSITION_JUMP:
                issues.append(f"Position jump {distance:.1f}m (outlier detected)")
                outlier_score = 0.0
            elif distance > 2.0:
                warnings.append(f"Sudden jump {distance:.1f}m")
                outlier_score = 0.7
            else:
                outlier_score = 1.0
            scores.append(outlier_score)
        
        # 4. Speed validation
        if speed is not None:
            if speed > self.MAX_SPEED:
                issues.append(f"Speed {speed:.1f} m/s unrealistic (>15 m/s)")
                speed_score = 0.0
            elif speed > 10.0:
                warnings.append(f"Speed {speed:.1f} m/s (fast for tractor)")
                speed_score = 0.7
            else:
                speed_score = 1.0
            
            # Speed jump validation (acceleration)
            if self.last_speed is not None and self.last_time is not None:
                dt = time.time() - self.last_time
                if dt > 0:
                    accel = abs(speed - self.last_speed) / dt
                    if accel > self.MAX_ACCELERATION:
                        issues.append(f"Acceleration {accel:.1f} m/s² unrealistic")
                        speed_score = 0.3
            
            scores.append(speed_score)
            self.last_speed = speed
        
        # Update state
        self.last_lat = lat
        self.last_lng = lng
        self.last_time = time.time()
        
        # Calculate overall quality
        quality_score = sum(scores) / len(scores) if scores else 0.0
        
        return {
            'valid': len(issues) == 0,
            'quality_score': quality_score,
            'issues': issues,
            'warnings': warnings,
        }
    
    @staticmethod
    def _haversine(lat1, lng1, lat2, lng2):
        """Calculate distance in meters between two GPS points"""
        R = 6371000  # Earth radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c


class GPSProcessor:
    """Main GPS processor — combines filtering + validation"""
    
    def __init__(self):
        # Kalman filters for lat/lng
        self.kalman_lat = KalmanFilter(process_variance=1e-5, measurement_variance=1e-4)
        self.kalman_lng = KalmanFilter(process_variance=1e-5, measurement_variance=1e-4)
        
        # Quality validator
        self.validator = GPSQualityValidator()
        
        # Moving average buffers untuk smoothing
        self.lat_buffer = deque(maxlen=3)
        self.lng_buffer = deque(maxlen=3)
        
        # Latest processed GPS
        self.current_gps = {
            'lat': 0,
            'lng': 0,
            'hdop': None,
            'satellites': 0,
            'speed': 0,
            'heading': 0,
            'quality_score': 0,
            'timestamp': time.time(),
        }
        self.valid = False
    
    def process(self, raw_gps_data):
        """
        Process raw GPS data from ESP32
        
        Input: {
            'latitude': float,
            'longitude': float,
            'hdop': float,
            'satellites': int,
            'speed': float (m/s or km/h),
            'heading': float,
        }
        
        Returns: processed GPS data
        """
        lat = float(raw_gps_data.get('latitude', 0))
        lng = float(raw_gps_data.get('longitude', 0))
        hdop = float(raw_gps_data.get('hdop')) if raw_gps_data.get('hdop') else None
        sats = int(raw_gps_data.get('satellites', 0))
        speed = float(raw_gps_data.get('speed', 0))
        heading = float(raw_gps_data.get('heading', 0))
        
        # Skip if coordinates are 0 or invalid
        if lat == 0 or lng == 0:
            return None
        
        # Validate
        validation = self.validator.validate(lat, lng, hdop, sats, speed, heading)
        if not validation['valid']:
            self.valid = False
            print(f"GPS validation failed: {validation['issues']}")
            return None
        
        # Apply Kalman filter
        filtered_lat = self.kalman_lat.update(lat)
        filtered_lng = self.kalman_lng.update(lng)
        
        # Apply moving average smoothing
        self.lat_buffer.append(filtered_lat)
        self.lng_buffer.append(filtered_lng)
        final_lat = sum(self.lat_buffer) / len(self.lat_buffer)
        final_lng = sum(self.lng_buffer) / len(self.lng_buffer)
        
        # Update state
        self.current_gps = {
            'lat': final_lat,
            'lng': final_lng,
            'hdop': hdop or 0,
            'satellites': sats,
            'speed': speed,
            'heading': heading,
            'quality_score': validation['quality_score'],
            'timestamp': time.time(),
            'raw_lat': lat,
            'raw_lng': lng,
        }
        self.valid = True
        
        return self.current_gps
    
    def get_current(self):
        """Get latest processed GPS data"""
        return self.current_gps, self.valid
    
    def is_valid_fix(self):
        """Check jika GPS fix cukup baik untuk autonomous"""
        return (self.valid and 
                self.current_gps['quality_score'] >= 0.8 and 
                self.current_gps['satellites'] >= 6)


# Singleton instance
_gps_processor = None

def get_gps_processor():
    global _gps_processor
    if _gps_processor is None:
        _gps_processor = GPSProcessor()
    return _gps_processor
