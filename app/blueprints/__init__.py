"""
app/__init__.py — FIXED
========================
Cara registrasi blueprint yang benar agar semua route /getData, /setMode, dll
bisa diakses langsung tanpa prefix yang salah.
"""

from flask import Flask


def create_app():
    app = Flask(__name__)

    # ── Daftarkan semua blueprint ──────────────────────────────────
    from app.blueprints.main        import main_bp
    from app.blueprints.dashboard   import dashboard_bp
    from app.blueprints.control     import control_bp   # ← blueprint control
    # from app.blueprints.ml        import ml_bp
    # from app.blueprints.analytics import analytics_bp
    # dari blueprint lain yang kamu punya

    app.register_blueprint(main_bp)
    app.register_blueprint(dashboard_bp)

    # ╔══════════════════════════════════════════════════════╗
    # ║  PENTING: control_bp HARUS tanpa url_prefix          ║
    # ║  agar /getData, /setMode, dll terdaftar di root      ║
    # ║  dan bisa di-fetch oleh JS di browser                ║
    # ╚══════════════════════════════════════════════════════╝
    app.register_blueprint(control_bp)   # ← TANPA url_prefix='...'

    return app