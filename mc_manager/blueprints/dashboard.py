from flask import Blueprint, render_template, redirect, url_for, session
from mc_manager.core.config import load_auth_config, get_role

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    config = load_auth_config()
    if not config.get('admin_password_hash'):
        return redirect(url_for('auth.setup'))
    
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
        
    return render_template('index.html', role=get_role(), username=session.get('username'))
