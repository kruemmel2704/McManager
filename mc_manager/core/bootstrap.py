import sys
import subprocess
import os
import re

def check_java_installer():
    """Checks if Java 21 is installed, otherwise attempts to install it."""
    try:
        # Check if java command exists
        result = subprocess.run(['java', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        version_output = result.stderr or result.stdout
        
        # Check if version 21 is present in the output
        if " 21." in version_output or " \"21\"" in version_output:
            return True
            
        print(f"[!] Java 21 not found (detected: {version_output.splitlines()[0] if version_output else 'none'}).")
    except FileNotFoundError:
        print("[!] Java is not installed.")
    except Exception as e:
        print(f"[!] Error checking Java version: {e}")

    print("[!] Attempting to install Java 21...")
    try:
        # Check if we are on a system with apt (Debian/Ubuntu)
        if os.path.exists("/usr/bin/apt-get"):
            print("[*] Running apt-get update...")
            subprocess.check_call(["sudo", "apt-get", "update"])
            print("[*] Installing openjdk-21-jre-headless...")
            subprocess.check_call(["sudo", "apt-get", "install", "-y", "openjdk-21-jre-headless"])
            print("[+] Java 21 installed successfully.")
            return True
        else:
            print("[!] apt-get not found. Please install Java 21 manually.")
            return False
    except Exception as e:
        print(f"[!] Automated Java installation failed: {e}")
        print("[!] Please install Java 21 manually (e.g., 'sudo apt install openjdk-21-jre-headless').")
        return False

def check_and_install_dependencies():
    """Checks if Java and required Python packages are installed, otherwise installs them."""
    # 1. Java Check
    check_java_installer()
    
    # 2. Python Dependencies Check
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

            subprocess.check_call([sys.executable, "-m", "pip", "install", "--break-system-packages", "-r", req_path])
            print("[+] Dependencies installed successfully. Please restart the application.")
            sys.exit(0) # Exit to allow the user/system to restart with new packages available
        except Exception as e:
            print(f"[!] Critical error during auto-installation: {e}")
            sys.exit(1)

if __name__ == "__main__":
    # If running directly, check dependencies first
    # Note: This only works if this script doesn't have top-level flask imports yet
    pass
