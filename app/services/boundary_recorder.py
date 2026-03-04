"""
AI-TRAC Boundary Recorder Service
Handles telemetry boundary recording untuk full autonomous field coverage calibration
"""

import json
import math
import time
from datetime import datetime
from typing import List, Dict, Tuple


class GeoUtils:
    """Geographic utility functions"""
    
    EARTH_RADIUS_M = 6371000
    
    @staticmethod
    def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in meters between two GPS points"""
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return GeoUtils.EARTH_RADIUS_M * c
    
    @staticmethod
    def polygon_area(coords: List[Tuple[float, float]]) -> float:
        """
        Calculate polygon area using Shoelace formula
        
        Args:
            coords: list of (lat, lng) tuples
        
        Returns: area in square meters
        """
        area = 0
        n = len(coords)
        
        for i in range(n):
            j = (i + 1) % n
            lat1, lng1 = coords[i]
            lat2, lng2 = coords[j]
            
            # Convert to projected coordinates (rough approximation)
            x1 = lng1 * math.pi / 180 * GeoUtils.EARTH_RADIUS_M * math.cos(lat1 * math.pi / 180)
            y1 = lat1 * math.pi / 180 * GeoUtils.EARTH_RADIUS_M
            x2 = lng2 * math.pi / 180 * GeoUtils.EARTH_RADIUS_M * math.cos(lat2 * math.pi / 180)
            y2 = lat2 * math.pi / 180 * GeoUtils.EARTH_RADIUS_M
            
            area += x1 * y2 - x2 * y1
        
        return abs(area / 2)
    
    @staticmethod
    def polygon_perimeter(coords: List[Tuple[float, float]]) -> float:
        """Calculate perimeter of polygon in meters"""
        perimeter = 0
        n = len(coords)
        
        for i in range(n):
            j = (i + 1) % n
            dist = GeoUtils.haversine_distance(
                coords[i][0], coords[i][1],
                coords[j][0], coords[j][1]
            )
            perimeter += dist
        
        return perimeter
    
    @staticmethod
    def is_polygon_closed(coords: List[Tuple[float, float]], tolerance_m: float = 20) -> bool:
        """
        Check if polygon is closed (first point ≈ last point)
        
        Args:
            coords: list of (lat, lng) tuples
            tolerance_m: maximum distance between first and last point (meters)
        
        Returns: bool
        """
        if len(coords) < 3:
            return False
        
        distance = GeoUtils.haversine_distance(
            coords[0][0], coords[0][1],
            coords[-1][0], coords[-1][1]
        )
        
        return distance <= tolerance_m
    
    @staticmethod
    def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
        """
        Ray casting algorithm untuk check if point is inside polygon
        
        Args:
            point: (lat, lng) to test
            polygon: list of (lat, lng) vertices
        
        Returns: bool
        """
        lat, lng = point
        n = len(polygon)
        inside = False
        
        p1lat, p1lng = polygon[0]
        for i in range(1, n + 1):
            p2lat, p2lng = polygon[i % n]
            
            if lat > min(p1lat, p2lat):
                if lat <= max(p1lat, p2lat):
                    if lng <= max(p1lng, p2lng):
                        if p1lat != p2lat:
                            xinters = (lat - p1lat) * (p2lng - p1lng) / (p2lat - p1lat) + p1lng
                        if p1lng == p2lng or lng <= xinters:
                            inside = not inside
            
            p1lat, p1lng = p2lat, p2lng
        
        return inside


class BoundaryRecorder:
    """
    Manage boundary recording untuk autonomous field coverage
    
    Flow:
    1. Start boundary recording
    2. Operator drive traktor mengelilingi sawah (manual mode)
    3. Website record GPS points real-time
    4. Finalize boundary → validate polygon
    5. Use untuk path planning
    """
    
    MIN_AREA_M2 = 500
    MAX_AREA_M2 = 100000
    MIN_POINTS = 3
    MIN_POINT_SPACING_M = 5  # Don't record points too close together
    MAX_POINT_SPACING_M = 50  # Gap might indicate missed waypoints
    
    def __init__(self):
        self.is_recording = False
        self.boundary_points = []
        self.boundary_polygon = None
        self.metadata = {}
        self.validation = None
        
        # Track last recorded point untuk avoid duplicates
        self.last_recorded_point = None
    
    def get_status(self):
        """Get current recording status"""
        return {
            'is_recording': self.is_recording,
            'point_count': len(self.boundary_points),
            'metadata': self.metadata,
            'is_valid': self.validation is not None and self.validation['valid'],
        }
    
    def start_recording(self, operator_name: str = None) -> Dict:
        """
        Start boundary recording session
        
        Args:
            operator_name: Optional nama operator
        
        Returns: {'success': bool, 'message': str}
        """
        if self.is_recording:
            return {'success': False, 'message': 'Already recording'}
        
        self.is_recording = True
        self.boundary_points = []
        self.boundary_polygon = None
        self.validation = None
        self.last_recorded_point = None
        
        self.metadata = {
            'start_time': datetime.now().isoformat(),
            'start_timestamp': time.time(),
            'operator': operator_name or 'Unknown',
            'status': 'recording',
        }
        
        return {
            'success': True,
            'message': 'Boundary recording started',
            'session_id': int(time.time()),
        }
    
    def add_boundary_point(self, lat: float, lng: float, hdop: float = None,
                          speed: float = None, heading: float = None) -> Dict:
        """
        Add GPS point to boundary
        
        Args:
            lat: Latitude
            lng: Longitude
            hdop: Horizontal Dilution of Precision (accuracy)
            speed: Traktor speed (m/s)
            heading: Traktor heading (degrees)
        
        Returns: {'success': bool, 'message': str, 'point_count': int}
        """
        if not self.is_recording:
            return {'success': False, 'message': 'Not recording'}
        
        # Validate coordinates
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            return {'success': False, 'message': 'Invalid coordinates'}
        
        # Check GPS accuracy
        if hdop and hdop > 10:
            return {
                'success': False,
                'message': f'GPS accuracy poor (HDOP={hdop:.1f}m, need <10m)'
            }
        
        # Avoid duplicate/too-close points
        if self.last_recorded_point:
            distance = GeoUtils.haversine_distance(
                self.last_recorded_point['lat'],
                self.last_recorded_point['lng'],
                lat, lng
            )
            
            if distance < self.MIN_POINT_SPACING_M:
                return {
                    'success': False,
                    'message': f'Point too close ({distance:.1f}m) to last point'
                }
            
            if distance > self.MAX_POINT_SPACING_M:
                return {
                    'success': False,
                    'message': f'Gap too large ({distance:.1f}m) from last point — check GPS!'
                }
        
        # Add point
        point = {
            'lat': lat,
            'lng': lng,
            'hdop': hdop or 0,
            'speed': speed or 0,
            'heading': heading or 0,
            'timestamp': time.time(),
            'sequence': len(self.boundary_points),
        }
        
        self.boundary_points.append(point)
        self.last_recorded_point = point
        
        return {
            'success': True,
            'message': 'Point added',
            'point_count': len(self.boundary_points),
            'sequence': point['sequence'],
        }
    
    def stop_recording(self) -> Dict:
        """
        Stop recording dan finalize boundary
        
        Returns: {
            'success': bool,
            'message': str,
            'boundary': GeoJSON,
            'validation': validation result,
            'area_m2': float,
            'perimeter_m': float,
        }
        """
        if not self.is_recording:
            return {'success': False, 'message': 'Not recording'}
        
        self.is_recording = False
        self.metadata['end_time'] = datetime.now().isoformat()
        self.metadata['end_timestamp'] = time.time()
        self.metadata['duration_seconds'] = (self.metadata['end_timestamp'] - 
                                            self.metadata['start_timestamp'])
        self.metadata['point_count'] = len(self.boundary_points)
        
        # Validate boundary
        self.validation = self._validate_boundary()
        
        if not self.validation['valid']:
            return {
                'success': False,
                'message': f'Boundary invalid: {self.validation["error"]}',
                'validation': self.validation,
            }
        
        # Create polygon
        coords = [(p['lat'], p['lng']) for p in self.boundary_points]
        area = GeoUtils.polygon_area(coords)
        perimeter = GeoUtils.polygon_perimeter(coords)
        
        self.metadata['area_m2'] = area
        self.metadata['perimeter_m'] = perimeter
        
        # Store polygon
        self.boundary_polygon = {
            'type': 'Polygon',
            'coordinates': coords,
        }
        
        return {
            'success': True,
            'message': 'Boundary recorded and validated',
            'boundary': self._get_boundary_geojson(),
            'validation': self.validation,
            'area_m2': area,
            'area_ha': area / 10000,
            'perimeter_m': perimeter,
            'metadata': self.metadata,
        }
    
    def _validate_boundary(self) -> Dict:
        """Validate recorded boundary"""
        issues = []
        
        # Min points
        if len(self.boundary_points) < self.MIN_POINTS:
            issues.append(f"Minimum {self.MIN_POINTS} points required (have {len(self.boundary_points)})")
        
        # Polygon closed
        coords = [(p['lat'], p['lng']) for p in self.boundary_points]
        if not GeoUtils.is_polygon_closed(coords):
            issues.append("Polygon not closed — gap too large between first and last point")
        
        # Area check
        if len(coords) >= 3:
            area = GeoUtils.polygon_area(coords)
            if area < self.MIN_AREA_M2:
                issues.append(f"Area too small ({area:.0f}m²) — minimum {self.MIN_AREA_M2}m²")
            if area > self.MAX_AREA_M2:
                issues.append(f"Area too large ({area:.0f}m²) — maximum {self.MAX_AREA_M2}m²")
        
        # Boundary geometry (self-intersection check simplified)
        # TODO: Implement proper polygon self-intersection detection
        
        if issues:
            return {'valid': False, 'error': ' | '.join(issues)}
        
        return {
            'valid': True,
            'message': 'Boundary is valid',
            'points_counted': len(self.boundary_points),
        }
    
    def clear_recording(self) -> Dict:
        """Clear current recording"""
        self.is_recording = False
        self.boundary_points = []
        self.boundary_polygon = None
        self.validation = None
        self.metadata = {}
        
        return {'success': True, 'message': 'Recording cleared'}
    
    def get_boundary(self) -> Dict:
        """Get recorded boundary as GeoJSON"""
        if not self.boundary_polygon:
            return {'success': False, 'message': 'No boundary recorded'}
        
        return {
            'success': True,
            'boundary': self._get_boundary_geojson(),
            'metadata': self.metadata,
        }
    
    def _get_boundary_geojson(self) -> Dict:
        """Get boundary as GeoJSON FeatureCollection"""
        if not self.boundary_polygon:
            return None
        
        coords = self.boundary_polygon['coordinates']
        
        # Convert back to GeoJSON format [lng, lat]
        geojson_coords = [[c[1], c[0]] for c in coords]
        
        return {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [geojson_coords],
                    },
                    'properties': {
                        'name': 'Field Boundary',
                        'area_m2': self.metadata.get('area_m2', 0),
                        'perimeter_m': self.metadata.get('perimeter_m', 0),
                        'recorded_at': self.metadata.get('end_time', ''),
                    },
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': geojson_coords,
                    },
                    'properties': {
                        'name': 'Boundary Edge',
                        'point_count': len(self.boundary_points),
                    },
                },
            ],
        }
    
    def save_to_file(self, filepath: str) -> Dict:
        """Save boundary to JSON file"""
        if not self.boundary_polygon:
            return {'success': False, 'message': 'No boundary to save'}
        
        try:
            data = {
                'boundary': self._get_boundary_geojson(),
                'metadata': self.metadata,
                'raw_points': self.boundary_points,
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            return {'success': True, 'message': f'Saved to {filepath}'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def load_from_file(self, filepath: str) -> Dict:
        """Load boundary from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.boundary_points = data.get('raw_points', [])
            self.metadata = data.get('metadata', {})
            
            # Recreate polygon
            if self.boundary_points:
                coords = [(p['lat'], p['lng']) for p in self.boundary_points]
                self.boundary_polygon = {
                    'type': 'Polygon',
                    'coordinates': coords,
                }
                self.validation = self._validate_boundary()
            
            return {'success': True, 'message': 'Loaded from file'}
        except Exception as e:
            return {'success': False, 'message': str(e)}


# Singleton instance
_boundary_recorder = None

def get_boundary_recorder():
    global _boundary_recorder
    if _boundary_recorder is None:
        _boundary_recorder = BoundaryRecorder()
    return _boundary_recorder
