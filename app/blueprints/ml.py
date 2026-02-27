from flask import Blueprint, render_template

ml_bp = Blueprint('ml', __name__)

@ml_bp.route('/')
def index():
    return render_template('ml/index.html')
