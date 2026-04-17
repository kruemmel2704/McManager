import os
import requests
import json
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from mc_manager.core.config import load_auth_config, save_auth_config

auth_bp = Blueprint('auth', __name__)

MS_CLIENT_ID = os.getenv("MS_CLIENT_ID")
MS_CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
MS_AUTHORITY = os.getenv("MS_AUTHORITY", "https://login.microsoftonline.com/consumers")
MS_REDIRECT_URI = os.getenv("MS_REDIRECT_URI")

@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    config = load_auth_config()
    if config.get('admin_password_hash'):
        return "Setup bereits abgeschlossen.", 403
    
    if request.method == 'POST':
        pw = request.form.get('password')
        if pw:
            config['admin_password_hash'] = generate_password_hash(pw)
            save_auth_config(config)
            return redirect(url_for('auth.login'))
    return '''
        <style>body{background:#050505;color:white;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}</style>
        <form method="post" style="background:#0f0f0f;padding:2rem;border-radius:12px;border:1px solid #333;">
            <h2>Initiales Admin-Setup</h2>
            <p>Lege ein Passwort für den direkten Web-Zugang fest.</p>
            <input type="password" name="password" placeholder="Passwort" required style="width:100%;padding:10px;margin:10px 0;background:#222;border:1px solid #444;color:white;">
            <button type="submit" style="width:100%;padding:10px;background:#4ade80;border:none;border-radius:5px;cursor:pointer;">Speichern</button>
        </form>
    '''

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pw = request.form.get('password')
        config = load_auth_config()
        if check_password_hash(config.get('admin_password_hash'), pw):
            session['logged_in'] = True
            session['is_admin'] = True
            session['username'] = "WebAdmin"
            return redirect(url_for('dashboard.index'))
    
    ms_url = f"{MS_AUTHORITY}/oauth2/v2.0/authorize?client_id={MS_CLIENT_ID}&response_type=code&redirect_uri={MS_REDIRECT_URI}&scope=XboxLive.signin"
    return render_template('login.html', ms_url=ms_url)

@auth_bp.route('/callback')
def callback():
    code = request.args.get('code')
    if not code: return "Fehler beim MS Login", 400
    
    token_url = f"{MS_AUTHORITY}/oauth2/v2.0/token"
    data = {
        'client_id': MS_CLIENT_ID,
        'client_secret': MS_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': MS_REDIRECT_URI,
        'scope': 'XboxLive.signin'
    }
    
    try:
        r = requests.post(token_url, data=data)
        if r.status_code != 200:
            return f"<b>MS Token Fehler ({r.status_code}):</b><br><pre>{r.text}</pre>", 500
        ms_token = r.json().get('access_token')
    
        # Xbox Live
        xbl_url = "https://user.auth.xboxlive.com/user/authenticate"
        xbl_payload = {
            "Properties": {"AuthMethod": "RPS", "SiteName": "user.auth.xboxlive.com", "RpsTicket": f"d={ms_token}"},
            "RelyingParty": "http://auth.xboxlive.com", "TokenType": "JWT"
        }
        xbl_res = requests.post(xbl_url, json=xbl_payload).json()
        xbl_token = xbl_res['Token']
        uhs = xbl_res['DisplayClaims']['xui'][0]['uhs']

        # XSTS
        xsts_url = "https://xsts.auth.xboxlive.com/xsts/authorize"
        xsts_payload = {
            "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbl_token]},
            "RelyingParty": "http://xboxlive.com",
            "TokenType": "JWT"
        }
        xsts_res = requests.post(xsts_url, json=xsts_payload).json()
        
        if 'Token' not in xsts_res:
            return f"<b>XSTS Fehler:</b> konnte kein Token für das Xbox-Profil generieren.<br><pre>{json.dumps(xsts_res, indent=2)}</pre>", 500
            
        xsts_token = xsts_res['Token']

        # Xbox Profile
        profile_url = "https://profile.xboxlive.com/users/me/profile/settings?settings=Gamertag"
        headers = {
            "x-xbl-contract-version": "2",
            "Authorization": f"XBL3.0 x={uhs};{xsts_token}",
            "Accept": "application/json"
        }
        r = requests.get(profile_url, headers=headers)
       
        if r.status_code != 200:
            return f"<b>Xbox Profil Fehler ({r.status_code}):</b><br><pre>{r.text}</pre>", 500
            
        profile_data = r.json()
        try:
            username = profile_data['profileUsers'][0]['settings'][0]['value']
        except Exception:
            return f"Konnte Gamertag nicht in den Xbox-Daten finden.", 500

        session['logged_in'] = True
        session['username'] = username
        session['is_admin'] = False
        
        return redirect(url_for('dashboard.index'))
    except Exception as e:
        return f"Fehler bei der Xbox Authentifizierung: {str(e)}", 500

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
