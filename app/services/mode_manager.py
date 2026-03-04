"""
AI-TRAC Control Mode Manager
Implements explicit state machine untuk mode switching dengan validation
"""

from enum import Enum
from datetime import datetime
import json
import time


class ControlMode(Enum):
    """Available control modes"""
    MANUAL = "MANUAL"
    SEMI_AUTONOMOUS = "SEMI_AUTONOMOUS"
    FULL_AUTONOMOUS = "FULL_AUTONOMOUS"
    E_STOP = "E_STOP"


class ModeTransitionError(Exception):
    """Raised when mode transition is not allowed"""
    pass


class ControlModeManager:
    """
    State machine untuk kontrol mode traktor
    
    Valid transitions:
    - MANUAL → SEMI_AUTONOMOUS (dengan ≥2 waypoints)
    - MANUAL → FULL_AUTONOMOUS (dengan boundary + ML ready)
    - SEMI_AUTONOMOUS → MANUAL
    - SEMI_AUTONOMOUS → FULL_AUTONOMOUS
    - ANY → E_STOP
    - E_STOP → MANUAL (manual reset only)
    """
    
    # Define valid transitions
    VALID_TRANSITIONS = {
        ControlMode.MANUAL: [
            ControlMode.SEMI_AUTONOMOUS,
            ControlMode.FULL_AUTONOMOUS,
            ControlMode.E_STOP,
        ],
        ControlMode.SEMI_AUTONOMOUS: [
            ControlMode.MANUAL,
            ControlMode.FULL_AUTONOMOUS,
            ControlMode.E_STOP,
        ],
        ControlMode.FULL_AUTONOMOUS: [
            ControlMode.MANUAL,
            ControlMode.E_STOP,
        ],
        ControlMode.E_STOP: [
            ControlMode.MANUAL,  # ONLY manual reset allowed
        ],
    }
    
    def __init__(self):
        self.current_mode = ControlMode.MANUAL
        self.previous_mode = None
        self.mode_changed_at = datetime.now()
        
        # System state for prerequisites checking
        self.system_state = {
            'waypoint_count': 0,
            'boundary_valid': False,
            'boundary_area_m2': 0,
            'gps_quality_score': 0.0,
            'gps_fix_valid': False,
            'satellite_count': 0,
            'remote_connected': False,
            'remote_signal_strength': -100,
            'ml_model_loaded': False,
            'ml_ready': False,
            'autonomous_running': False,
            'path_generated': False,
        }
        
        # Mode-specific handlers
        self.mode_handlers = {
            ControlMode.MANUAL: {
                'on_enter': self._on_manual_enter,
                'on_exit': self._on_manual_exit,
            },
            ControlMode.SEMI_AUTONOMOUS: {
                'on_enter': self._on_semi_auto_enter,
                'on_exit': self._on_semi_auto_exit,
            },
            ControlMode.FULL_AUTONOMOUS: {
                'on_enter': self._on_full_auto_enter,
                'on_exit': self._on_full_auto_exit,
            },
            ControlMode.E_STOP: {
                'on_enter': self._on_estop_enter,
                'on_exit': self._on_estop_exit,
            },
        }
    
    def update_system_state(self, state_update):
        """Update system state (called from backend services)"""
        self.system_state.update(state_update)
    
    def can_transition(self, target_mode):
        """
        Check if transition dari current mode ke target_mode allowed
        
        Returns: (bool, str) — (can_transition, reason)
        """
        if target_mode not in self.VALID_TRANSITIONS.get(self.current_mode, []):
            reason = f"Invalid transition: {self.current_mode.value} → {target_mode.value}"
            return False, reason
        
        return True, "Transition allowed"
    
    def check_prerequisites(self, target_mode):
        """
        Check if all prerequisites met untuk target mode
        
        Returns: {
            'ok': bool,
            'checks': [{'name': str, 'met': bool, 'message': str}],
            'missing': [str],  # list of failed checks
        }
        """
        checks = []
        
        if target_mode == ControlMode.SEMI_AUTONOMOUS:
            # Check waypoints
            wp_check = {
                'name': 'waypoint_count',
                'met': self.system_state['waypoint_count'] >= 2,
                'message': f"Minimum 2 waypoints required (have {self.system_state['waypoint_count']})",
                'required': True,
            }
            checks.append(wp_check)
            
            # Check GPS
            gps_check = {
                'name': 'gps_fix_valid',
                'met': self.system_state['gps_fix_valid'],
                'message': f"GPS fix required (quality: {self.system_state['gps_quality_score']:.2f})",
                'required': True,
            }
            checks.append(gps_check)
            
            # Check remote
            remote_check = {
                'name': 'remote_connected',
                'met': self.system_state['remote_connected'],
                'message': "FlySky remote must be connected for manual override",
                'required': True,
            }
            checks.append(remote_check)
        
        elif target_mode == ControlMode.FULL_AUTONOMOUS:
            # Boundary
            boundary_check = {
                'name': 'boundary_valid',
                'met': self.system_state['boundary_valid'],
                'message': f"Valid boundary required (current: {self.system_state['boundary_area_m2']:.0f}m²)",
                'required': True,
            }
            checks.append(boundary_check)
            
            # GPS quality (stricter than semi-auto)
            gps_check = {
                'name': 'gps_quality',
                'met': self.system_state['gps_quality_score'] >= 0.85,
                'message': f"GPS quality must be ≥0.85 (current: {self.system_state['gps_quality_score']:.2f})",
                'required': True,
            }
            checks.append(gps_check)
            
            # Satellites
            sat_check = {
                'name': 'satellites',
                'met': self.system_state['satellite_count'] >= 6,
                'message': f"Need ≥6 satellites (current: {self.system_state['satellite_count']})",
                'required': True,
            }
            checks.append(sat_check)
            
            # ML model
            ml_check = {
                'name': 'ml_model',
                'met': self.system_state['ml_model_loaded'] and self.system_state['ml_ready'],
                'message': "ML model must be loaded and ready",
                'required': True,
            }
            checks.append(ml_check)
        
        # Compile results
        missing = [c['name'] for c in checks if not c['met'] and c.get('required', False)]
        all_ok = len(missing) == 0
        
        return {
            'ok': all_ok,
            'checks': checks,
            'missing': missing,
        }
    
    def can_set_mode(self, target_mode, force=False):
        """
        Comprehensive check untuk set mode
        
        Returns: {
            'ok': bool,
            'can_transition': bool,
            'prerequisites_ok': bool,
            'transition_reason': str,
            'prerequisite_failures': [str],
            'message': str,
        }
        """
        # Convert string to enum if needed
        if isinstance(target_mode, str):
            try:
                target_mode = ControlMode[target_mode.upper()]
            except KeyError:
                return {
                    'ok': False,
                    'message': f"Unknown mode: {target_mode}",
                }
        
        # Check transition
        can_trans, trans_reason = self.can_transition(target_mode)
        if not can_trans:
            return {
                'ok': False,
                'can_transition': False,
                'prerequisites_ok': None,
                'transition_reason': trans_reason,
                'prerequisite_failures': [],
                'message': f"Transition not allowed: {trans_reason}",
            }
        
        # Check prerequisites (unless force)
        prereq = self.check_prerequisites(target_mode)
        if not prereq['ok'] and not force:
            return {
                'ok': False,
                'can_transition': True,
                'prerequisites_ok': False,
                'transition_reason': None,
                'prerequisite_failures': prereq['missing'],
                'message': f"Prerequisites not met: " + ", ".join(prereq['missing']),
                'checks': prereq['checks'],
            }
        
        return {
            'ok': True,
            'can_transition': True,
            'prerequisites_ok': prereq['ok'],
            'transition_reason': None,
            'prerequisite_failures': [],
            'message': f"Ready to switch to {target_mode.value}",
        }
    
    def set_mode(self, target_mode, force=False, socketio=None):
        """
        Perform mode transition
        
        Args:
            target_mode: ControlMode enum or string
            force: bypass prerequisite checks
            socketio: Flask-SocketIO instance for broadcasting
        
        Returns: {
            'success': bool,
            'previous_mode': str,
            'current_mode': str,
            'message': str,
            'error': str (if failed),
        }
        """
        # Convert string to enum
        if isinstance(target_mode, str):
            try:
                target_mode = ControlMode[target_mode.upper()]
            except KeyError:
                return {'success': False, 'error': f"Unknown mode: {target_mode}"}
        
        # Comprehensive validation
        validation = self.can_set_mode(target_mode, force=force)
        if not validation['ok']:
            return {
                'success': False,
                'error': validation['message'],
                'details': validation.get('checks', []),
            }
        
        # Store previous mode
        self.previous_mode = self.current_mode
        
        # Run exit handler
        if self.current_mode in self.mode_handlers:
            try:
                self.mode_handlers[self.current_mode]['on_exit']()
            except Exception as e:
                print(f"Error in exit handler: {e}")
        
        # Change mode
        self.current_mode = target_mode
        self.mode_changed_at = datetime.now()
        
        # Run entry handler
        if target_mode in self.mode_handlers:
            try:
                self.mode_handlers[target_mode]['on_enter']()
            except Exception as e:
                print(f"Error in entry handler: {e}")
        
        # Broadcast if socketio available
        if socketio:
            try:
                socketio.emit('mode_changed', {
                    'previous_mode': self.previous_mode.value,
                    'current_mode': self.current_mode.value,
                    'timestamp': datetime.now().isoformat(),
                }, broadcast=True)
            except Exception as e:
                print(f"Error broadcasting mode change: {e}")
        
        return {
            'success': True,
            'previous_mode': self.previous_mode.value,
            'current_mode': self.current_mode.value,
            'message': f"Mode switched to {target_mode.value}",
        }
    
    def get_mode_info(self):
        """Get current mode info"""
        return {
            'current_mode': self.current_mode.value,
            'previous_mode': self.previous_mode.value if self.previous_mode else None,
            'mode_changed_at': self.mode_changed_at.isoformat(),
            'uptime_seconds': (datetime.now() - self.mode_changed_at).total_seconds(),
        }
    
    def get_mode_status(self):
        """Get detailed status untuk UI"""
        current_mode = self.current_mode.value
        state = self.system_state.copy()
        
        return {
            'mode': current_mode,
            'state': state,
            'ui_hints': self._get_ui_hints(),
        }
    
    # ─── Mode Handlers ────────────────────────────────────────
    
    def _on_manual_enter(self):
        """Setup when entering MANUAL mode"""
        print("Entering MANUAL mode — FlySky remote takes full control")
        self.system_state['autonomous_running'] = False
    
    def _on_manual_exit(self):
        """Cleanup when leaving MANUAL mode"""
        print("Exiting MANUAL mode")
    
    def _on_semi_auto_enter(self):
        """Setup when entering SEMI_AUTONOMOUS mode"""
        print("Entering SEMI_AUTONOMOUS mode — Waypoint following")
        # Start waypoint navigation
    
    def _on_semi_auto_exit(self):
        """Cleanup when leaving SEMI_AUTONOMOUS mode"""
        print("Exiting SEMI_AUTONOMOUS mode")
        # Stop waypoint navigation
    
    def _on_full_auto_enter(self):
        """Setup when entering FULL_AUTONOMOUS mode"""
        print("Entering FULL_AUTONOMOUS mode — Autonomous field coverage")
        # Initialize autonomous controller
    
    def _on_full_auto_exit(self):
        """Cleanup when leaving FULL_AUTONOMOUS mode"""
        print("Exiting FULL_AUTONOMOUS mode")
        self.system_state['autonomous_running'] = False
    
    def _on_estop_enter(self):
        """Setup when entering E-STOP mode"""
        print("!!! EMERGENCY STOP ACTIVATED !!!")
        self.system_state['autonomous_running'] = False
    
    def _on_estop_exit(self):
        """Cleanup when leaving E-STOP mode"""
        print("E-STOP reset")
    
    def _get_ui_hints(self):
        """Get UI hints untuk control panel"""
        mode = self.current_mode
        
        hints = {
            ControlMode.MANUAL: {
                'status_text': 'REMOTE CONTROL',
                'status_color': 'blue',
                'enabled_buttons': ['set_semi_auto', 'set_full_auto', 'estop'],
                'disabled_buttons': ['start_autonomous'],
            },
            ControlMode.SEMI_AUTONOMOUS: {
                'status_text': 'WAYPOINT NAVIGATION',
                'status_color': 'yellow',
                'enabled_buttons': ['back_to_manual', 'set_full_auto', 'estop'],
                'disabled_buttons': ['add_waypoint_after_start'],
            },
            ControlMode.FULL_AUTONOMOUS: {
                'status_text': 'AUTONOMOUS COVERAGE',
                'status_color': 'green',
                'enabled_buttons': ['pause_autonomous', 'back_to_manual', 'estop'],
                'disabled_buttons': ['add_waypoint'],
            },
            ControlMode.E_STOP: {
                'status_text': '!!! EMERGENCY STOP !!!',
                'status_color': 'red',
                'enabled_buttons': ['reset_estop'],
                'disabled_buttons': ['all_except_reset'],
            },
        }
        
        return hints.get(mode, {})


# Singleton instance
_mode_manager = None

def get_mode_manager():
    global _mode_manager
    if _mode_manager is None:
        _mode_manager = ControlModeManager()
    return _mode_manager
