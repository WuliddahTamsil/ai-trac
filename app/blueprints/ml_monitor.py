from flask import Blueprint, render_template
ml_bp = Blueprint('ml', __name__)

@ml_bp.route('/ml-monitor')
def index():
    return render_template('pages/ml_monitor.html', active='ml')
