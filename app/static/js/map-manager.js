/**
 * AI-TRAC Frontend — Map Manager Module
 * Handles Leaflet map initialization, marker animation, and map-based interactions
 * 
 * Features:
 * - Smooth GPS marker animation dengan interpolation
 * - WebSocket real-time GPS updates
 * - Auto-follow mode dengan smooth panning
 * - Geofence visualization dan tracking
 */

class MapManager {
    constructor(mapElementId = 'map') {
        this.mapElement = document.getElementById(mapElementId);
        this.map = null;
        this.vehicleMarker = null;
        
        // Animation state
        this.currentLat = 0;
        this.currentLng = 0;
        this.targetLat = 0;
        this.targetLng = 0;
        this.animationProgress = 0;
        this.lastUpdateTime = 0;
        this.animationFrameId = null;
        
        // Configuration
        this.ANIMATION_DURATION_MS = 100; // Interpolate over 100ms (10 Hz)
        this.MAP_DEFAULT_LAT = -6.5971;
        this.MAP_DEFAULT_LNG = 106.8060;
        this.MAP_DEFAULT_ZOOM = 17;
        
        // Features
        this.autoFollow = false;
        this.geofenceActive = false;
        this.geofenceCircle = null;
        this.trackLine = null;
        this.trackPoints = [];
        this.boundaryPoly = null;
        
        // WebSocket
        this.ws = null;
        this.wsConnected = false;
    }
    
    /**
     * Initialize Leaflet map dan vehicle marker
     */
    initMap() {
        console.log('Initializing map...');
        
        // Create map
        this.map = L.map(this.mapElement, {
            zoomControl: true,
            attributionControl: false,
        }).setView([this.MAP_DEFAULT_LAT, this.MAP_DEFAULT_LNG], this.MAP_DEFAULT_ZOOM);
        
        // Add tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 22,
            attribution: ''
        }).addTo(this.map);
        
        // Create vehicle marker
        this.currentLat = this.MAP_DEFAULT_LAT;
        this.currentLng = this.MAP_DEFAULT_LNG;
        this.targetLat = this.MAP_DEFAULT_LAT;
        this.targetLng = this.MAP_DEFAULT_LNG;
        
        this.vehicleMarker = L.marker(
            [this.currentLat, this.currentLng],
            { icon: this._createVehicleIcon() }
        ).addTo(this.map)
         .bindPopup('<b>AI-TRAC Vehicle</b>');
        
        // Browser geolocation untuk initial centering
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    console.log('Browser geolocation found');
                    this.map.setView([pos.coords.latitude, pos.coords.longitude], 18);
                },
                (err) => {
                    console.log('Geolocation unavailable, using default');
                }
            );
        }
        
        // Start animation loop
        this._startAnimationLoop();
    }
    
    /**
     * Create custom vehicle marker icon dengan pulsing ring
     */
    _createVehicleIcon() {
        return L.divIcon({
            className: '',
            html: `<div style="position:relative;width:32px;height:32px;display:flex;align-items:center;justify-content:center;">
                <div style="position:absolute;width:32px;height:32px;border-radius:50%;background:rgba(0,212,255,0.15);border:1.5px solid rgba(0,212,255,0.5);animation:vping 1.8s ease-out infinite;"></div>
                <div style="width:16px;height:16px;border-radius:50%;background:#00d4ff;border:2px solid #fff;box-shadow:0 0 12px rgba(0,212,255,0.8);z-index:2;position:relative;"></div>
                <style>@keyframes vping{0%{transform:scale(1);opacity:0.7}100%{transform:scale(2.4);opacity:0;}}</style>
              </div>`,
            iconSize: [32, 32],
            iconAnchor: [16, 16]
        });
    }
    
    /**
     * Start animation loop (60 FPS) untuk smooth marker movement
     */
    _startAnimationLoop() {
        const animate = (timestamp) => {
            if (this.lastUpdateTime === 0) {
                this.lastUpdateTime = timestamp;
            }
            
            const deltaTime = timestamp - this.lastUpdateTime;
            
            // Update progress
            this.animationProgress += deltaTime / this.ANIMATION_DURATION_MS;
            
            if (this.animationProgress >= 1.0) {
                // Animation complete
                this.currentLat = this.targetLat;
                this.currentLng = this.targetLng;
                this.animationProgress = 0;
            } else {
                // Smooth interpolation dengan easing function (cubic easeOut)
                const t = this.animationProgress;
                const eased = 1 - Math.pow(1 - t, 3);
                
                this.currentLat = this._interpolate(this.currentLat, this.targetLat, eased);
                this.currentLng = this._interpolate(this.currentLng, this.targetLng, eased);
            }
            
            // Update marker position
            if (this.vehicleMarker) {
                this.vehicleMarker.setLatLng([this.currentLat, this.currentLng]);
            }
            
            // Auto-follow
            if (this.autoFollow && this.animationProgress > 0.5) {
                this.map.panTo([this.currentLat, this.currentLng], { animate: true });
            }
            
            this.lastUpdateTime = timestamp;
            this.animationFrameId = requestAnimationFrame(animate);
        };
        
        this.animationFrameId = requestAnimationFrame(animate);
    }
    
    /**
     * Linear interpolation antara two values
     */
    _interpolate(from, to, t) {
        return from + (to - from) * t;
    }
    
    /**
     * Update marker dengan new GPS data
     * Called dari WebSocket 'gps_update' event
     */
    updateGPSPosition(gpsData) {
        // Set target untuk animation
        this.targetLat = parseFloat(gpsData.lat);
        this.targetLng = parseFloat(gpsData.lng);
        
        // Reset animation
        this.animationProgress = 0;
        
        // Record track points jika recording
        if (this.isTracking && gpsData.quality_score > 0.7) {
            const lastPoint = this.trackPoints[this.trackPoints.length - 1];
            const distance = this._haversine(this.currentLat, this.currentLng, 
                                            this.targetLat, this.targetLng);
            
            if (!lastPoint || distance > 0.5) {  // Minimum 0.5m between points
                this.trackPoints.push([this.targetLat, this.targetLng]);
                this._updateTrackLine();
            }
        }
    }
    
    /**
     * Haversine distance calculation
     */
    _haversine(lat1, lng1, lat2, lng2) {
        const R = 6371000;  // Earth radius in meters
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLng = (lng2 - lng1) * Math.PI / 180;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLng/2) * Math.sin(dLng/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }
    
    /**
     * Toggle auto-follow mode
     */
    toggleAutoFollow() {
        this.autoFollow = !this.autoFollow;
        return this.autoFollow;
    }
    
    /**
     * Center map ke vehicle position
     */
    centerOnVehicle() {
        if (this.vehicleMarker) {
            this.map.setView(this.vehicleMarker.getLatLng(), this.map.getZoom());
        }
    }
    
    /**
     * Setup geofence circle
     */
    setGeofence(radiusM) {
        if (this.geofenceCircle) {
            this.map.removeLayer(this.geofenceCircle);
        }
        
        this.geofenceActive = true;
        this.geofenceCircle = L.circle([this.currentLat, this.currentLng], {
            radius: radiusM,
            color: '#ff4444',
            fillColor: '#ff4444',
            fillOpacity: 0.06,
            weight: 1.5,
            dashArray: '6 4'
        }).addTo(this.map);
    }
    
    /**
     * Update geofence radius
     */
    updateGeofenceRadius(radiusM) {
        if (this.geofenceCircle) {
            this.geofenceCircle.setRadius(radiusM);
        }
    }
    
    /**
     * Clear geofence
     */
    clearGeofence() {
        if (this.geofenceCircle) {
            this.map.removeLayer(this.geofenceCircle);
            this.geofenceCircle = null;
        }
        this.geofenceActive = false;
    }
    
    /**
     * Draw boundary polygon
     */
    drawBoundary(coordinates) {
        // coordinates: [[lat, lng], [lat, lng], ...]
        if (this.boundaryPoly) {
            this.map.removeLayer(this.boundaryPoly);
        }
        
        this.boundaryPoly = L.polygon(coordinates, {
            color: '#fbbf24',
            weight: 2,
            opacity: 0.85,
            fillColor: '#fbbf24',
            fillOpacity: 0.09
        }).addTo(this.map);
    }
    
    /**
     * Start track recording
     */
    startTracking() {
        this.isTracking = true;
        this.trackPoints = [];
    }
    
    /**
     * Stop track recording
     */
    stopTracking() {
        this.isTracking = false;
        return this.trackPoints;
    }
    
    /**
     * Update track line visualization
     */
    _updateTrackLine() {
        if (this.trackLine) {
            this.map.removeLayer(this.trackLine);
        }
        
        if (this.trackPoints.length > 1) {
            this.trackLine = L.polyline(this.trackPoints, {
                color: '#ff4444',
                weight: 2.5,
                opacity: 0.9,
                dashArray: '5 10'
            }).addTo(this.map);
        }
    }
    
    /**
     * Clear track
     */
    clearTrack() {
        this.trackPoints = [];
        if (this.trackLine) {
            this.map.removeLayer(this.trackLine);
            this.trackLine = null;
        }
    }
    
    /**
     * Connect WebSocket untuk live GPS streaming
     */
    connectWebSocket(wsUrl = 'ws://' + window.location.host) {
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.wsConnected = true;
            
            // Request GPS stream
            this.ws.send(JSON.stringify({
                'event': 'request_gps_stream',
                'data': {}
            }));
        };
        
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            if (message.event === 'gps_update') {
                this.updateGPSPosition(message.data);
                this._updateGPSUI(message.data);
                // mirror to global UI renderer if available
                if (typeof render === 'function') {
                    render(message.data);
                }
            } else if (message.event === 'mode_changed') {
                // update mode display as well
                if (typeof render === 'function') {
                    render({ mode: message.data.current_mode });
                }
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.wsConnected = false;
        };
    }
    
    /**
     * Update GPS info panel (called dari gps_update event)
     */
    _updateGPSUI(gpsData) {
        document.getElementById('latitude').textContent = gpsData.lat.toFixed(6);
        document.getElementById('longitude').textContent = gpsData.lng.toFixed(6);
        document.getElementById('gpsSats').textContent = gpsData.sats + ' / 12';
        document.getElementById('speed').textContent = (gpsData.speed * 3.6).toFixed(1) + ' km/h';
        document.getElementById('heading').textContent = gpsData.heading.toFixed(0) + '°';
        
        const gpsQuality = gpsData.quality_score;
        const gpsBadge = document.getElementById('gpsBadge');
        if (gpsQuality >= 0.8) {
            gpsBadge.className = 'badge b-ok';
            gpsBadge.textContent = '✓ Valid Fix';
        } else if (gpsQuality >= 0.6) {
            gpsBadge.className = 'badge b-warn';
            gpsBadge.textContent = 'Moderate';
        } else {
            gpsBadge.className = 'badge b-err';
            gpsBadge.textContent = 'Searching';
        }
    }
    
    /**
     * Get current map center
     */
    getMapCenter() {
        return this.map.getCenter();
    }
    
    /**
     * Get zoom level
     */
    getZoom() {
        return this.map.getZoom();
    }
}

// Export untuk digunakan di modul lain
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MapManager;
}
