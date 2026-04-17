import os
import sys

# 1. Dependency Check
# This is done before importing Flask to ensure we can auto-install missing packages.
from mc_manager.core.bootstrap import check_and_install_dependencies
check_and_install_dependencies()

from flask import Flask, session
from mc_manager.core.config import load_env

# 2. Load environment variables
load_env()

from mc_manager.blueprints.auth import auth_bp
from mc_manager.blueprints.api import api_bp
from mc_manager.blueprints.dashboard import dashboard_bp

def create_app():
    """
    Application factory for the Flask app.
    Sets up the secret key, session lifetime, and registers all blueprints.
    """
    app = Flask(__name__)
    
    # Secret key for session encryption - loaded from environment for persistence
    app.secret_key = os.getenv("SESSION_SECRET", os.urandom(24))
    
    # Session Cookie Security Flags
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true",
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=2678400 # 31 days
    )
    
    @app.before_request
    def make_session_permanent():
        """Ensure sessions persist across browser restarts."""
        session.permanent = True

    # Register modular blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(dashboard_bp)
    
    return app

# Instantiate the application
app = create_app()

if __name__ == '__main__':
    # Run server on all interfaces, port 5000
    app.run(host='0.0.0.0', port=5000)
