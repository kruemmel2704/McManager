import os
import subprocess
import threading
from collections import deque
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import requests

# Only import psutil if installed, but since we mandated it, we can just import
import psutil

import json
import time
import zipfile
import shutil
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = 2678400 # 31 Tage in Sekunden

@app.before_request
def make_session_permanent():
    session.permanent = True

# --- Konfiguration (.env laden) ---
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

load_env()
CONFIG_FILE = 'auth_config.json'
MS_CLIENT_ID = os.getenv("MS_CLIENT_ID")
MS_CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
MS_AUTHORITY = os.getenv("MS_AUTHORITY", "https://login.microsoftonline.com/consumers")
MS_REDIRECT_URI = os.getenv("MS_REDIRECT_URI")

def load_auth_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_auth_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def is_op(username):
    """Prüft ob ein Username in der ops.json steht."""
    ops_path = '/opt/minecraft/ops.json'
    if not os.path.exists(ops_path):
        return False
    try:
        with open(ops_path, 'r') as f:
            ops = json.load(f)
            return any(op['name'].lower() == username.lower() for op in ops)
    except:
        return False

def get_role():
    if not session.get('logged_in'):
        return None
    if session.get('is_admin'):
        return 'admin'
    if is_op(session.get('username', '')):
        return 'op'
    return 'viewer'

mc_process = None
log_lines = deque(maxlen=200)
online_players = set()
player_history = {} # {name: {"last_seen": timestamp}}

def load_player_history():
    global player_history
    history_path = '/opt/minecraft/player_history.json'
    usercache_path = '/opt/minecraft/usercache.json'
    if os.path.exists(history_path):
        try:
            with open(history_path, 'r') as f:
                player_history = json.load(f)
        except:
            player_history = {}
    else:
        # Import from usercache.json if available
        if os.path.exists(usercache_path):
            try:
                with open(usercache_path, 'r') as f:
                    cache = json.load(f)
                    for entry in cache:
                        player_history[entry['name']] = {"last_seen": "Unbekannt"}
            except: pass

def save_player_history():
    with open('/opt/minecraft/player_history.json', 'w') as f:
        json.dump(player_history, f)

load_player_history()

def load_properties():
    props = {}
    props_path = '/opt/minecraft/server.properties'
    if not os.path.exists(props_path):
        return props
    with open(props_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                props[k] = v
    return props

def save_properties(props):
    with open('/opt/minecraft/server.properties', 'w') as f:
        f.write("# Modified by Minecraft Server Panel\n")
        for k, v in props.items():
            f.write(f"{k}={v}\n")

def output_reader(process):
    global online_players
    try:
        for line in iter(process.stdout.readline, b''):
            decoded_line = line.decode('utf-8', errors='replace').strip()
            log_lines.append(decoded_line)
            
            # Simple player tracking
            if "joined the game" in decoded_line:
                parts = decoded_line.split()
                # Typical format: [HH:MM:SS] [Server thread/INFO]: PlayerName joined the game
                # Or just PlayerName joined the game if no prefix
                try:
                    # Find the word before 'joined'
                    idx = parts.index("joined")
                    player = parts[idx-1]
                    # Remove potential bracket/info prefixes if they exist (crude but often works for vanilla)
                    if ':' in player: player = player.split(':')[-1]
                    online_players.add(player)
                    
                    # Update history
                    player_history[player] = {"last_seen": time.strftime("%Y-%m-%d %H:%M:%S")}
                    save_player_history()
                except: pass
            elif "left the game" in decoded_line:
                parts = decoded_line.split()
                try:
                    idx = parts.index("left")
                    player = parts[idx-1]
                    if ':' in player: player = player.split(':')[-1]
                    online_players.discard(player)
                except: pass
    except Exception as e:
        log_lines.append(f"[Server Panel] Error reading output: {e}")

@app.route('/')
def index():
    config = load_auth_config()
    if not config.get('admin_password_hash'):
        return redirect(url_for('setup'))
    
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    return render_template('index.html', role=get_role(), username=session.get('username'))

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    config = load_auth_config()
    if config.get('admin_password_hash'):
        return "Setup bereits abgeschlossen.", 403
    
    if request.method == 'POST':
        pw = request.form.get('password')
        if pw:
            config['admin_password_hash'] = generate_password_hash(pw)
            save_auth_config(config)
            return redirect(url_for('login'))
    return '''
        <style>body{background:#050505;color:white;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}</style>
        <form method="post" style="background:#0f0f0f;padding:2rem;border-radius:12px;border:1px solid #333;">
            <h2>Initiales Admin-Setup</h2>
            <p>Lege ein Passwort für den direkten Web-Zugang fest.</p>
            <input type="password" name="password" placeholder="Passwort" required style="width:100%;padding:10px;margin:10px 0;background:#222;border:1px solid #444;color:white;">
            <button type="submit" style="width:100%;padding:10px;background:#4ade80;border:none;border-radius:5px;cursor:pointer;">Speichern</button>
        </form>
    '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Lokal Login
        pw = request.form.get('password')
        config = load_auth_config()
        if check_password_hash(config.get('admin_password_hash'), pw):
            session['logged_in'] = True
            session['is_admin'] = True
            session['username'] = "WebAdmin"
            return redirect(url_for('index'))
    
    # MS Login URL generieren
    ms_url = f"{MS_AUTHORITY}/oauth2/v2.0/authorize?client_id={MS_CLIENT_ID}&response_type=code&redirect_uri={MS_REDIRECT_URI}&scope=XboxLive.signin"
    return render_template('login.html', ms_url=ms_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code: return "Fehler beim MS Login", 400
    
    # 1. Microsoft Token holen
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
    
        # 2. Xbox Live Authentifizierung
        xbl_url = "https://user.auth.xboxlive.com/user/authenticate"
        xbl_payload = {
            "Properties": {"AuthMethod": "RPS", "SiteName": "user.auth.xboxlive.com", "RpsTicket": f"d={ms_token}"},
            "RelyingParty": "http://auth.xboxlive.com", "TokenType": "JWT"
        }
        xbl_res = requests.post(xbl_url, json=xbl_payload).json()
        xbl_token = xbl_res['Token']
        uhs = xbl_res['DisplayClaims']['xui'][0]['uhs']

        # 3. XSTS Authentifizierung (Speziell für das Xbox Profil)
        xsts_url = "https://xsts.auth.xboxlive.com/xsts/authorize"
        xsts_payload = {
            "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbl_token]},
            "RelyingParty": "http://xboxlive.com", # Geändert von Minecraft auf Xbox
            "TokenType": "JWT"
        }
        xsts_res = requests.post(xsts_url, json=xsts_payload).json()
        
        if 'Token' not in xsts_res:
            return f"<b>XSTS Fehler:</b> konnte kein Token für das Xbox-Profil generieren.<br><pre>{json.dumps(xsts_res, indent=2)}</pre>", 500
            
        xsts_token = xsts_res['Token']

        # 4. Xbox Profil abrufen (Gamertag)
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
        
        return redirect(url_for('index'))
    except Exception as e:
        return f"Fehler bei der Xbox Authentifizierung: {str(e)}", 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def is_server_running_ext():
    """Checks if ANY minecraft server process is running on the system."""
    try:
        for proc in psutil.process_iter(['cmdline']):
            if proc.info['cmdline'] and any('server.jar' in arg for arg in proc.info['cmdline']):
                return proc
    except: pass
    return None

@app.route('/api/status', methods=['GET'])
def get_status():
    global mc_process
    # Check our controlled process first
    running_here = mc_process is not None and mc_process.poll() is None
    
    # Check system-wide
    ext_proc = is_server_running_ext()
    
    return jsonify({
        "running": running_here or (ext_proc is not None),
        "managed": running_here,
        "pid": ext_proc.pid if ext_proc else None
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    global mc_process
    proc = None
    if mc_process is not None and mc_process.poll() is None:
        proc = psutil.Process(mc_process.pid)
    else:
        ext = is_server_running_ext()
        if ext: proc = ext

    if not proc:
        return jsonify({"cpu": 0.0, "ram": 0.0})
    
    try:
        proc = psutil.Process(mc_process.pid)
        # psutil returns CPU% representing total usage across all cores.
        cpu_percent = proc.cpu_percent(interval=None) 
        # RSS memory in MB
        ram_mb = proc.memory_info().rss / (1024 * 1024)
        return jsonify({"cpu": round(cpu_percent, 1), "ram": round(ram_mb, 1)})
    except Exception as e:
        return jsonify({"cpu": 0.0, "ram": 0.0})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify({"logs": list(log_lines)})

@app.route('/api/players', methods=['GET'])
def get_players():
    return jsonify({
        "online": list(online_players),
        "history": player_history
    })

@app.route('/api/properties', methods=['GET', 'POST'])
def handle_properties():
    if request.method == 'GET':
        return jsonify(load_properties())
    else:
        props = request.get_json()
        save_properties(props)
        return jsonify({"status": "success", "message": "Properties saved."})

@app.route('/api/gamerule', methods=['POST'])
def set_gamerule():
    if get_role() not in ['admin', 'op']:
        return jsonify({"status": "error", "message": "Keine Berechtigung"}), 403
    data = request.get_json()
    rule = data.get('rule')
    value = data.get('value')
    if rule and value is not None:
        command = f"gamerule {rule} {str(value).lower()}"
        return send_command_logic(command)
    return jsonify({"status": "error", "message": "Missing rule or value"}), 400

def send_command_logic(command):
    global mc_process
    if mc_process is None or mc_process.poll() is not None:
        return jsonify({"status": "error", "message": "Server is not running."}), 400
    try:
        mc_process.stdin.write(f"{command}\n".encode('utf-8'))
        mc_process.stdin.flush()
        log_lines.append(f"[Server Panel] Command sent: {command}")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/start', methods=['POST'])
def start_server():
    global mc_process
    if mc_process is not None and mc_process.poll() is None:
        return jsonify({"status": "error", "message": "Server is already running."}), 400

    data = request.get_json() or {}
    ram = data.get('ram', 2048)  # default 2048 MB
    cpu = data.get('cpu', 2)     # default 2 cores

    try:
        ram = int(ram)
        cpu = int(cpu)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid RAM or CPU value."}), 400

    java_path = "/usr/lib/jvm/java-25-openjdk-amd64/bin/java"
    if not os.path.exists(java_path):
        java_path = "java" # fallback

    try:
        mc_process = subprocess.Popen(
            [java_path, f"-Xmx{ram}M", f"-Xms{ram}M", f"-XX:ActiveProcessorCount={cpu}", "-jar", "server.jar", "nogui"],
            cwd="/opt/minecraft",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        
        t = threading.Thread(target=output_reader, args=(mc_process,))
        t.daemon = True
        t.start()
        
        log_lines.append(f"[Server Panel] Server started with {ram}MB RAM and {cpu} CPU threads.")
        return jsonify({"status": "success", "message": "Server started."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_server():
    global mc_process
    
    # Try controlled stop first
    if mc_process is not None and mc_process.poll() is None:
        try:
            mc_process.stdin.write(b"stop\n")
            mc_process.stdin.flush()
            log_lines.append("[Server Panel] Stop command sent.")
            return jsonify({"status": "success", "message": "Stop command sent."})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    # If not controlled by us, try to kill the process (Force Stop)
    ext = is_server_running_ext()
    if ext:
        try:
            ext.terminate()
            log_lines.append(f"[Server Panel] External server process (PID {ext.pid}) terminated.")
            return jsonify({"status": "success", "message": "External server terminated."})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Could not stop external process: {e}"}), 500

    return jsonify({"status": "error", "message": "Server is not running."}), 400

@app.route('/api/command', methods=['POST'])
def send_command():
    if get_role() not in ['admin', 'op']:
        return jsonify({"status": "error", "message": "Keine Berechtigung"}), 403
    global mc_process
    if mc_process is None or mc_process.poll() is not None:
        return jsonify({"status": "error", "message": "Server is not running."}), 400

    data = request.get_json()
    command = data.get('command', '').strip()
    
    if not command:
        return jsonify({"status": "error", "message": "No command provided."}), 400

    return send_command_logic(command)

# --- NEW: Versions, Plugins & CurseForge ---

@app.route('/api/versions/vanilla', methods=['GET'])
def get_vanilla_versions():
    try:
        manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        res = requests.get(manifest_url).json()
        # Nur Releases zurückgeben
        releases = [v for v in res['versions'] if v['type'] == 'release'][:15]
        return jsonify(releases)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/versions/paper', methods=['GET'])
def get_paper_versions():
    try:
        res = requests.get("https://api.papermc.io/v2/projects/paper").json()
        return jsonify(res['versions'][::-1][:15]) # Die neuesten 15
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/download/version', methods=['POST'])
def download_version():
    if get_role() not in ['admin']:
        return jsonify({"status": "error", "message": "Nur Admins können Versionen ändern"}), 403
    
    data = request.get_json()
    v_type = data.get('type') # 'vanilla' oder 'paper'
    version = data.get('version')
    
    if is_server_running_ext():
        return jsonify({"status": "error", "message": "Server muss gestoppt sein, um die Version zu ändern"}), 400

    try:
        target_path = "/opt/minecraft/server.jar"
        # Backup der alten jar
        if os.path.exists(target_path):
            shutil.move(target_path, f"{target_path}.bak")

        if v_type == 'paper':
            # Latest build für die Version holen
            builds_res = requests.get(f"https://api.papermc.io/v2/projects/paper/versions/{version}").json()
            latest_build = builds_res['builds'][-1]
            download_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{latest_build}/downloads/paper-{version}-{latest_build}.jar"
        else:
            # Vanilla
            res = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json").json()
            v_info_url = next(v['url'] for v in res['versions'] if v['id'] == version)
            v_data = requests.get(v_info_url).json()
            download_url = v_data['downloads']['server']['url']

        # Download mit Stream
        r = requests.get(download_url, stream=True)
        with open(target_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return jsonify({"status": "success", "message": f"Version {version} ({v_type}) erfolgreich installiert."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/plugins', methods=['GET'])
def list_plugins():
    plugin_dir = "/opt/minecraft/plugins"
    if not os.path.exists(plugin_dir):
        os.makedirs(plugin_dir)
    plugins = [f for f in os.listdir(plugin_dir) if f.endswith('.jar')]
    return jsonify(plugins)

@app.route('/api/plugins/upload', methods=['POST'])
def upload_plugin():
    if get_role() not in ['admin', 'op']:
        return jsonify({"status": "error", "message": "Keine Berechtigung"}), 403
    
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "Keine Datei gefunden"}), 400
    
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.jar'):
        return jsonify({"status": "error", "message": "Ungültige Datei. Nur .jar erlaubt."}), 400
    
    plugin_dir = "/opt/minecraft/plugins"
    if not os.path.exists(plugin_dir):
        os.makedirs(plugin_dir)
        
    file.save(os.path.join(plugin_dir, file.filename))
    return jsonify({"status": "success", "message": f"Plugin {file.filename} hochgeladen."})

@app.route('/api/plugins/delete', methods=['POST'])
def delete_plugin():
    if get_role() not in ['admin', 'op']:
        return jsonify({"status": "error", "message": "Keine Berechtigung"}), 403
    name = request.get_json().get('name')
    path = os.path.join("/opt/minecraft/plugins", name)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Datei nicht gefunden"}), 404

# CurseForge Mockup (für echte CurseForge API ist ein API Key nötig)
@app.route('/api/modpacks/search', methods=['GET'])
def search_modpacks():
    query = request.args.get('query', '')
    # In der Realität würden wir hier requests.get("https://api.curseforge.com/v1/mods/search", headers={"x-api-key": "..."}) nutzen
    return jsonify([
        {"id": 1, "name": "Better Minecraft [FORGE]", "version": "1.20.1"},
        {"id": 2, "name": "All the Mods 9", "version": "1.20.1"},
        {"id": 3, "name": "SkyFactory 4", "version": "1.12.2"}
    ])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
