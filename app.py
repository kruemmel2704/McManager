import os
from flask import Flask, session
from mc_manager.core.config import load_env

# 1. Load environment variables from .env file before anything else.
# This ensures that variables like MS_CLIENT_ID are available when blueprints are imported.
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
    
    # Secret key for session encryption
    app.secret_key = os.urandom(24)
    # Set session lifetime to 31 days
    app.config['PERMANENT_SESSION_LIFETIME'] = 2678400 
    
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
