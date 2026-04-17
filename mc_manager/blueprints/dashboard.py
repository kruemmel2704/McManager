from flask import Blueprint, render_template, redirect, url_for, session
from mc_manager.core.config import load_auth_config, get_role

# Blueprint for the main user interface
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    """
    Main dashboard view. 
    Redirects to setup if no admin is set, or to login if user is not authenticated.
    """
    config = load_auth_config()
    if not config.get('admin_password_hash'):
        return redirect(url_for('auth.setup'))
    
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
        
    # Render the main dashboard template with role and username from session
    return render_template('index.html', role=get_role(), username=session.get('username'))
