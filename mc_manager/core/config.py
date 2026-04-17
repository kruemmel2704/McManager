import os
import json
from flask import session

# Path to the local authentication configuration file
CONFIG_FILE = 'auth_config.json'

def load_env():
    """
    Loads environment variables from a .env file located in the project root.
    Uses manual parsing to avoid external dependencies like python-dotenv.
    """
    # Navigate up two levels from mc_manager/core/config.py to reach the project root
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

def load_auth_config():
    """Loads the application authentication config (like admin password hash) from JSON."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_auth_config(config):
    """Saves the application authentication config to a JSON file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def get_permission_level(xuid, username):
    """
    Checks the permission level of a user.
    1. Checks permissions.json by XUID (Bedrock standard).
    2. Checks ops.json by username (Java standard fallback).
    Returns 'admin', 'op', 'member', or 'viewer'.
    """
    # 1. Check permissions.json (XUID based)
    perm_path = '/opt/minecraft/permissions.json'
    if xuid and os.path.exists(perm_path):
        try:
            with open(perm_path, 'r') as f:
                perms = json.load(f)
                for entry in perms:
                    if str(entry.get('xuid')) == str(xuid):
                        perm = entry.get('permission', 'member')
                        if perm == 'operator': return 'op'
                        return perm
        except Exception:
            pass

    # 2. Check ops.json (Username/UUID based fallback)
    ops_path = '/opt/minecraft/ops.json'
    if username and os.path.exists(ops_path):
        try:
            with open(ops_path, 'r') as f:
                ops = json.load(f)
                for op in ops:
                    if op.get('name', '').lower() == username.lower():
                        return 'op'
        except Exception:
            pass
            
    return 'viewer'

def get_role():
    """
    Determines the current user's role based on their session.
    Roles: 'admin', 'op', 'member', 'viewer'.
    """
    if not session.get('logged_in'):
        return None
    if session.get('is_admin'):
        return 'admin'
    
    return get_permission_level(session.get('xuid'), session.get('username'))

def load_properties():
    """
    Reads the Minecraft server.properties file and returns it as a dictionary.
    Skips comments and empty lines.
    """
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
    """Writes a dictionary of properties back to the server.properties file."""
    with open('/opt/minecraft/server.properties', 'w') as f:
        f.write("# Modified by Minecraft Server Panel\n")
        for k, v in props.items():
            f.write(f"{k}={v}\n")
