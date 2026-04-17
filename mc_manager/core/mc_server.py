import os
import subprocess
import threading
import time
import json
import psutil
from collections import deque

mc_process = None
log_lines = deque(maxlen=200)
online_players = set()
player_history = {}

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

def output_reader(process):
    global online_players
    try:
        for line in iter(process.stdout.readline, b''):
            decoded_line = line.decode('utf-8', errors='replace').strip()
            log_lines.append(decoded_line)
            
            if "joined the game" in decoded_line:
                parts = decoded_line.split()
                try:
                    idx = parts.index("joined")
                    player = parts[idx-1]
                    if ':' in player: player = player.split(':')[-1]
                    online_players.add(player)
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

def is_server_running_ext():
    try:
        for proc in psutil.process_iter(['cmdline']):
            if proc.info['cmdline'] and any('server.jar' in arg for arg in proc.info['cmdline']):
                return proc
    except: pass
    return None

def start_mc_server(ram=2048, cpu=2):
    global mc_process
    if mc_process is not None and mc_process.poll() is None:
        return False, "Server is already running."

    java_path = "/usr/lib/jvm/java-25-openjdk-amd64/bin/java"
    if not os.path.exists(java_path):
        java_path = "java"

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
        return True, "Server started."
    except Exception as e:
        return False, str(e)

def stop_mc_server():
    global mc_process
    if mc_process is not None and mc_process.poll() is None:
        try:
            mc_process.stdin.write(b"stop\n")
            mc_process.stdin.flush()
            log_lines.append("[Server Panel] Stop command sent.")
            return True, "Stop command sent."
        except Exception as e:
            return False, str(e)

    ext = is_server_running_ext()
    if ext:
        try:
            ext.terminate()
            log_lines.append(f"[Server Panel] External server process (PID {ext.pid}) terminated.")
            return True, "External server terminated."
        except Exception as e:
            return False, f"Could not stop external process: {e}"

    return False, "Server is not running."

def send_command_to_server(command):
    global mc_process
    if mc_process is None or mc_process.poll() is not None:
        return False, "Server is not running."
    try:
        mc_process.stdin.write(f"{command}\n".encode('utf-8'))
        mc_process.stdin.flush()
        log_lines.append(f"[Server Panel] Command sent: {command}")
        return True, "Command sent."
    except Exception as e:
        return False, str(e)

# Initialize
load_player_history()
