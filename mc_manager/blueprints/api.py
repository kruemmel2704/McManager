import os
import requests
import shutil
import psutil
from flask import Blueprint, request, jsonify, abort
from werkzeug.utils import secure_filename, safe_join
import mc_manager.core.mc_server as mc_server
from mc_manager.core.config import get_role, load_properties, save_properties
from mc_manager.core.mc_server import (
    is_server_running_ext, online_players, player_history,
    start_mc_server, stop_mc_server, send_command_to_server
)

# Central API blueprint for all dashboard functionalities
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/status', methods=['GET'])
def get_status():
    """Returns the current server running status and PID. Requires Viewer role."""
    if not get_role():
        return jsonify({"status": "error", "message": "Access denied"}), 403
    running_here = mc_server.mc_process is not None and mc_server.mc_process.poll() is None
    ext_proc = is_server_running_ext()
    
    # Check EULA status
    eula_accepted = False
    eula_path = "/opt/minecraft/eula.txt"
    if os.path.exists(eula_path):
        with open(eula_path, 'r') as f:
            eula_accepted = "eula=true" in f.read().lower()

    return jsonify({
        "running": running_here or (ext_proc is not None),
        "managed": running_here,
        "pid": ext_proc.pid if ext_proc else None,
        "eula_accepted": eula_accepted
    })

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Returns real-time CPU and RAM usage of the server process."""
    proc = None
    if mc_server.mc_process is not None and mc_server.mc_process.poll() is None:
        proc = psutil.Process(mc_server.mc_process.pid)
    else:
        ext = is_server_running_ext()
        if ext: proc = ext

    if not proc:
        return jsonify({"cpu": 0.0, "ram": 0.0})
    
    try:
        cpu_percent = proc.cpu_percent(interval=None) 
        ram_mb = proc.memory_info().rss / (1024 * 1024)
        return jsonify({"cpu": round(cpu_percent, 1), "ram": round(ram_mb, 1)})
    except Exception:
        return jsonify({"cpu": 0.0, "ram": 0.0})

@api_bp.route('/logs', methods=['GET'])
def get_logs():
    """Returns the current log buffer."""
    return jsonify({"logs": list(mc_server.log_lines)})

@api_bp.route('/players', methods=['GET'])
def get_players():
    """Returns currently online players and the overall player history."""
    return jsonify({
        "online": list(online_players),
        "history": player_history
    })

@api_bp.route('/properties', methods=['GET', 'POST'])
def handle_properties():
    """GET: Returns server.properties. POST: Updates server.properties. Requires OP/Admin."""
    if get_role() not in ['admin', 'op']:
        return jsonify({"status": "error", "message": "Access denied"}), 403
    if request.method == 'GET':
        return jsonify(load_properties())
    else:
        props = request.get_json()
        save_properties(props)
        return jsonify({"status": "success", "message": "Properties saved."})

@api_bp.route('/gamerule', methods=['POST'])
def set_gamerule():
    """Sets a Minecraft gamerule. Requires OP or Admin role."""
    if get_role() not in ['admin', 'op']:
        return jsonify({"status": "error", "message": "Access denied"}), 403
    data = request.get_json()
    rule = data.get('rule')
    value = data.get('value')
    if rule and value is not None:
        command = f"gamerule {rule} {str(value).lower()}"
        success, msg = send_command_to_server(command)
        return jsonify({"status": "success" if success else "error", "message": msg})
    return jsonify({"status": "error", "message": "Missing rule or value"}), 400

@api_bp.route('/start', methods=['POST'])
def start_server():
    """Starts the Minecraft server with provided resources. Requires OP/Admin."""
    if get_role() not in ['admin', 'op']:
        return jsonify({"status": "error", "message": "Access denied"}), 403
    data = request.get_json() or {}
    ram = data.get('ram', 2048)
    cpu = data.get('cpu', 2)
    try:
        ram, cpu = int(ram), int(cpu)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid RAM or CPU value."}), 400

    success, msg = start_mc_server(ram, cpu)
    return jsonify({"status": "success" if success else "error", "message": msg})

@api_bp.route('/stop', methods=['POST'])
def stop_server():
    """Stops the running Minecraft server. Requires Admin/OP."""
    if get_role() not in ['admin', 'op']:
        return jsonify({"status": "error", "message": "Access denied"}), 403
    success, msg = stop_mc_server()
    return jsonify({"status": "success" if success else "error", "message": msg})

@api_bp.route('/command', methods=['POST'])
def send_command():
    """Sends a raw command to the server console. Requires Admin/OP."""
    if get_role() not in ['admin', 'op']:
        return jsonify({"status": "error", "message": "Access denied"}), 403
    data = request.get_json()
    command = data.get('command', '').strip()
    if not command:
        return jsonify({"status": "error", "message": "No command provided."}), 400
    success, msg = send_command_to_server(command)
    return jsonify({"status": "success" if success else "error", "message": msg})

@api_bp.route('/versions/vanilla', methods=['GET'])
def get_vanilla_versions():
    """Fetches the latest Minecraft Vanilla releases from Mojang's API."""
    try:
        manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        res = requests.get(manifest_url).json()
        releases = [v for v in res['versions'] if v['type'] == 'release'][:15]
        return jsonify(releases)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/versions/paper', methods=['GET'])
def get_paper_versions():
    """Fetches the latest PaperMC versions from their API."""
    try:
        res = requests.get("https://api.papermc.io/v2/projects/paper").json()
        return jsonify(res['versions'][::-1][:15])
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/download/version', methods=['POST'])
def download_version():
    """Downloads and installs a specific Minecraft version .jar file."""
    if get_role() not in ['admin']:
        return jsonify({"status": "error", "message": "Admin access required"}), 403
    data = request.get_json()
    v_type, version = data.get('type'), data.get('version')
    if is_server_running_ext():
        return jsonify({"status": "error", "message": "Server must be stopped first"}), 400

    try:
        target_path = "/opt/minecraft/server.jar"
        if os.path.exists(target_path): shutil.move(target_path, f"{target_path}.bak")

        if v_type == 'paper':
            builds_res = requests.get(f"https://api.papermc.io/v2/projects/paper/versions/{version}").json()
            latest_build = builds_res['builds'][-1]
            download_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{latest_build}/downloads/paper-{version}-{latest_build}.jar"
        else:
            res = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json").json()
            v_info_url = next(v['url'] for v in res['versions'] if v['id'] == version)
            v_data = requests.get(v_info_url).json()
            download_url = v_data['downloads']['server']['url']

        r = requests.get(download_url, stream=True)
        with open(target_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        return jsonify({"status": "success", "message": f"Version {version} installed."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/plugins', methods=['GET'])
def list_plugins():
    """Lists all .jar files in the plugins folder."""
    plugin_dir = "/opt/minecraft/plugins"
    if not os.path.exists(plugin_dir): os.makedirs(plugin_dir)
    return jsonify([f for f in os.listdir(plugin_dir) if f.endswith('.jar')])

@api_bp.route('/plugins/upload', methods=['POST'])
def upload_plugin():
    """Handles plugin upload (.jar)."""
    if get_role() not in ['admin', 'op']: return jsonify({"status": "error", "message": "Access denied"}), 403
    if 'file' not in request.files: return jsonify({"status": "error", "message": "No file"}), 400
    file = request.files['file']
    filename = secure_filename(file.filename)
    plugin_dir = "/opt/minecraft/plugins"
    if not os.path.exists(plugin_dir): os.makedirs(plugin_dir)
    file.save(safe_join(plugin_dir, filename))
    return jsonify({"status": "success"})

@api_bp.route('/plugins/delete', methods=['POST'])
def delete_plugin():
    """Deletes a plugin file."""
    if get_role() not in ['admin', 'op']:
        return jsonify({"status": "error", "message": "Access denied"}), 403
    name = secure_filename(request.get_json().get('name', ''))
    plugin_dir = "/opt/minecraft/plugins"
    path = safe_join(plugin_dir, name)
    if path and os.path.exists(path):
        os.remove(path)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "File not found"}), 404

@api_bp.route('/modpacks/search', methods=['GET'])
def search_modpacks():
    """(Mock) search for CurseForge modpacks."""
    return jsonify([
        {"id": 1, "name": "Better Minecraft [FORGE]", "version": "1.20.1"},
        {"id": 2, "name": "All the Mods 9", "version": "1.20.1"},
        {"id": 3, "name": "SkyFactory 4", "version": "1.12.2"}
    ])

@api_bp.route('/eula/accept', methods=['POST'])
def accept_eula():
    """Accepts the Minecraft EULA by updating eula.txt. Requires Admin/OP."""
    if get_role() not in ['admin', 'op']:
        return jsonify({"status": "error", "message": "Access denied"}), 403
    
    eula_path = "/opt/minecraft/eula.txt"
    try:
        content = ""
        if os.path.exists(eula_path):
            with open(eula_path, 'r') as f:
                content = f.read()
        
        # Replace or append eula=true
        if "eula=" in content.lower():
            import re
            content = re.sub(r"(?i)eula\s*=\s*(false|true)?", "eula=true", content)
        else:
            if content and not content.endswith("\n"): content += "\n"
            content += "eula=true\n"
            
        with open(eula_path, 'w') as f:
            f.write(content)
            
        return jsonify({"status": "success", "message": "EULA accepted successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to update EULA: {e}"}), 500
