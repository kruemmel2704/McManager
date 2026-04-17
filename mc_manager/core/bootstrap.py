import sys
import subprocess
import os

def check_and_install_dependencies():
    """Checks if required packages are installed, otherwise installs them."""
    try:
        import flask
        import psutil
        import requests
    except ImportError:
        print("[!] Missing dependencies. Starting automated setup...")
        try:
            # requirements.txt is in the project root, two levels up from mc_manager/core/
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            req_path = os.path.join(base_path, "requirements.txt")
            
            if not os.path.exists(req_path):
                print(f"[!] Error: {req_path} not found. Cannot auto-install.")
                return

            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_path])
            print("[+] Dependencies installed successfully. Please restart the application.")
            sys.exit(0) # Exit to allow the user/system to restart with new packages available
        except Exception as e:
            print(f"[!] Critical error during auto-installation: {e}")
            sys.exit(1)

if __name__ == "__main__":
    # If running directly, check dependencies first
    # Note: This only works if this script doesn't have top-level flask imports yet
    pass
