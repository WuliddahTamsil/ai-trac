from flask import Blueprint, render_template

telemetry_bp = Blueprint('telemetry', __name__)

@telemetry_bp.route('/')
def index():
    return render_template('telemetry/index.html')
