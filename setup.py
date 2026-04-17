import os
import subprocess
import sys
import shutil

def print_step(message):
    print(f"\n[+] {message}")

def check_requirements():
    print_step("Installing dependencies from requirements.txt...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed successfully.")
    except Exception as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

def setup_env():
    print_step("Configuring environment variables (.env)...")
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            shutil.copy(".env.example", ".env")
            print("Created .env from .env.example. PLEASE EDIT THIS FILE LATER!")
        else:
            with open(".env", "w") as f:
                f.write("MS_CLIENT_ID=\nMS_CLIENT_SECRET=\nMS_REDIRECT_URI=http://localhost:5000/callback\n")
            print("Created empty .env file.")
    else:
        print(".env already exists, skipping.")

def setup_directories():
    print_step("Checking directory structure...")
    target_dir = "/opt/minecraft"
    if not os.path.exists(target_dir):
        print(f"Warning: {target_dir} does not exist.")
        try:
            # Try to create it if we have permissions, otherwise warn
            os.makedirs(target_dir, exist_ok=True)
            print(f"Created {target_dir}")
        except Exception as e:
            print(f"Could not create {target_dir}: {e}")
            print("Please create it manually or update mc_manager/core/config.py")
    else:
        print(f"{target_dir} is ready.")

def main():
    print("========================================")
    print("   McManager Setup & Installation")
    print("========================================")
    
    check_requirements()
    setup_env()
    setup_directories()
    
    print("\n" + "="*40)
    print("Setup Complete!")
    print("1. Edit the .env file with your Azure App credentials.")
    print("2. Place your server.jar in /opt/minecraft/")
    print("3. Start the dashboard with: python3 app.py")
    print("="*40)

if __name__ == "__main__":
    main()
