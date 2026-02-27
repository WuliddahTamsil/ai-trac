from flask import Blueprint, render_template

maintenance_bp = Blueprint('maintenance', __name__)

@maintenance_bp.route('/')
def index():
    return render_template('maintenance/index.html')
