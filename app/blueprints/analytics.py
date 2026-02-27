from flask import Blueprint, render_template

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/')
def index():
    return render_template('analytics/index.html')
