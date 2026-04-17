import os
from flask import Flask, session
from mc_manager.core.config import load_env

# Load environment variables before importing blueprints
load_env()

from mc_manager.blueprints.auth import auth_bp
from mc_manager.blueprints.api import api_bp
from mc_manager.blueprints.dashboard import dashboard_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    app.config['PERMANENT_SESSION_LIFETIME'] = 2678400 # 31 Tage
    
    @app.before_request
    def make_session_permanent():
        session.permanent = True

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(dashboard_bp)
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
