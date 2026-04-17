import os
import requests
import json
import secrets
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, abort
from werkzeug.security import generate_password_hash, check_password_hash
from mc_manager.core.config import load_auth_config, save_auth_config

# Blueprint for handling both local and Microsoft-based authentication
auth_bp = Blueprint('auth', __name__)

# Microsoft OAuth2 Configuration (loaded from .env)
MS_CLIENT_ID = os.getenv("MS_CLIENT_ID")
MS_CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
MS_AUTHORITY = os.getenv("MS_AUTHORITY", "https://login.microsoftonline.com/consumers")
MS_REDIRECT_URI = os.getenv("MS_REDIRECT_URI")

@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """
    Initial setup page. Allows setting an admin password if none exists.
    Triggered on first launch.
    """
    config = load_auth_config()
    if config.get('admin_password_hash'):
        return "Setup already completed.", 403
    
    if request.method == 'POST':
        pw = request.form.get('password')
        if pw:
            # Store hashed password for security
            config['admin_password_hash'] = generate_password_hash(pw)
            save_auth_config(config)
            return redirect(url_for('auth.login'))
            
    # Inline CSS for the simple setup form
    return '''
        <style>body{background:#050505;color:white;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}</style>
        <form method="post" style="background:#0f0f0f;padding:2rem;border-radius:12px;border:1px solid #333;">
            <h2>Admin Setup</h2>
            <p>Set a password for direct web dashboard access.</p>
            <input type="password" name="password" placeholder="Password" required style="width:100%;padding:10px;margin:10px 0;background:#222;border:1px solid #444;color:white;">
            <button type="submit" style="width:100%;padding:10px;background:#4ade80;border:none;border-radius:5px;cursor:pointer;">Save</button>
        </form>
    '''

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page offering local password login and Microsoft (Xbox Live) login.
    """
    if request.method == 'POST':
        # Local Admin Login
        pw = request.form.get('password')
        config = load_auth_config()
        stored_hash = config.get('admin_password_hash')
        if stored_hash and pw and check_password_hash(stored_hash, pw):
            session['logged_in'] = True
            session['is_admin'] = True
            session['username'] = "WebAdmin"
            return redirect(url_for('dashboard.index'))
    
    # Generate Microsoft OAuth2 Authorization URL with state for CSRF protection
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    ms_url = f"{MS_AUTHORITY}/oauth2/v2.0/authorize?client_id={MS_CLIENT_ID}&response_type=code&redirect_uri={MS_REDIRECT_URI}&scope=XboxLive.signin&state={state}"
    return render_template('login.html', ms_url=ms_url)

@auth_bp.route('/callback')
def callback():
    """
    Callback handler for Microsoft's OAuth2 flow.
    Exchanges authorization code for tokens and fetches Xbox Gamertag for identification.
    """
    code = request.args.get('code')
    state = request.args.get('state')
    stored_state = session.get('oauth_state')
    
    # Verify state to prevent CSRF
    if not state or state != stored_state:
        print(f"[AUTH DEBUG] State Mismatch! URL State: {state}, Session State: {stored_state}")
        return "Invalid session state. Possible CSRF attack.", 403
        
    if not code: return "Microsoft login failed (no code)", 400
    
    # 1. Exchange Code for MS Access Token
    token_url = f"{MS_AUTHORITY}/oauth2/v2.0/token"
    token_data = {
        'client_id': MS_CLIENT_ID,
        'client_secret': MS_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': MS_REDIRECT_URI,
        'scope': 'XboxLive.signin'
    }
    
    try:
        r = requests.post(token_url, data=token_data)
        if r.status_code != 200:
            return f"<b>MS Token Error ({r.status_code}):</b><br><pre>{r.text}</pre>", 500
        ms_token = r.json().get('access_token')
    
        # 2. Xbox Live Authentication (Authenticate user on Xbox services)
        xbl_url = "https://user.auth.xboxlive.com/user/authenticate"
        xbl_payload = {
            "Properties": {"AuthMethod": "RPS", "SiteName": "user.auth.xboxlive.com", "RpsTicket": f"d={ms_token}"},
            "RelyingParty": "http://auth.xboxlive.com", "TokenType": "JWT"
        }
        xbl_res = requests.post(xbl_url, json=xbl_payload).json()
        xbl_token = xbl_res['Token']
        uhs = xbl_res['DisplayClaims']['xui'][0]['uhs']
        xuid = xbl_res['DisplayClaims']['xui'][0].get('xid')

        # 3. XSTS Authorization (Authorize access specifically to Xbox Profile data)
        xsts_url = "https://xsts.auth.xboxlive.com/xsts/authorize"
        xsts_payload = {
            "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbl_token]},
            "RelyingParty": "http://xboxlive.com",
            "TokenType": "JWT"
        }
        xsts_res = requests.post(xsts_url, json=xsts_payload).json()
        
        if 'Token' not in xsts_res:
            return f"<b>XSTS Error:</b> Could not generate profile token.<br><pre>{json.dumps(xsts_res, indent=2)}</pre>", 500
            
        xsts_token = xsts_res['Token']

        # 4. Fetch Xbox Profile (To get the actual Minecraft Gamertag)
        profile_url = "https://profile.xboxlive.com/users/me/profile/settings?settings=Gamertag"
        headers = {
            "x-xbl-contract-version": "2",
            "Authorization": f"XBL3.0 x={uhs};{xsts_token}",
            "Accept": "application/json"
        }
        r = requests.get(profile_url, headers=headers)
       
        if r.status_code != 200:
            return f"<b>Xbox Profile Error ({r.status_code}):</b><br><pre>{r.text}</pre>", 500
            
        profile_data = r.json()
        try:
            username = profile_data['profileUsers'][0]['settings'][0]['value']
        except Exception:
            return "Could not find Gamertag in Xbox response.", 500

        # Successful auth: Create session
        session['logged_in'] = True
        session['username'] = username
        session['xuid'] = xuid
        session['is_admin'] = False
        
        return redirect(url_for('dashboard.index'))
    except Exception as e:
        return f"Xbox Auth Exception: {str(e)}", 500

@auth_bp.route('/logout')
def logout():
    """Clears the session and redirects to login."""
    session.clear()
    return redirect(url_for('auth.login'))
