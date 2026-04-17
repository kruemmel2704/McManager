# Minecraft Server Dashboard

A modern, web-based control panel to manage a local Minecraft server. Built with Flask, this dashboard provides real-time monitoring, player management, and server configuration tools with a premium, dark-themed user interface.

## Features

- **Real-time Monitoring**: Live CPU and RAM usage tracking for the Minecraft server process.
- **Integrated Console**: Full access to the server console with the ability to send commands and view real-time logs.
- **Player Management**:
  - View online players.
  - Track player history (last seen).
  - Quick actions: Kick, OP, and Whitelist players.
- **Server Management**:
  - Start/Stop the server from the web.
  - Install/Update Minecraft versions (Vanilla & PaperMC) directly from the UI.
  - Plugin management (Upload/Delete .jar files).
- **Configuration**:
  - Edit server.properties through an interactive grid.
  - Manage gamerules with easy-to-use switches and inputs.
- **Secure Authentication**:
  - Local Admin login.
  - Microsoft OAuth2 / Xbox Live integration for player-based access.
  - Role-based access control (Admin, OP, Viewer).

## Technology Stack

- **Backend**: Python 3, Flask
- **Frontend**: HTML5, Vanilla CSS, JavaScript (ES6+)
- **Process Management**: psutil, subprocess
- **Design**: Modern dark-mode aesthetic with CSS Glassmorphism and Inter/JetBrains Mono typography.

## Project Structure

```text
/opt/minecraft/dashboard/
├── app.py                # Main entry point (Application Factory)
├── mc_manager/           # Backend Logic
│   ├── core/             # Core utilities (Config, Process Handler)
│   └── blueprints/       # Modular Flask routes (API, Auth, Dashboard)
├── templates/            # UI Templates
│   ├── base.html         # Main layout & CSS
│   ├── index.html        # Dashboard Shell & JS
│   ├── login.html        # Authentication page
│   └── fragments/        # Tab-specific HTML components
├── .env                  # Environment Variables (Sensitive data)
└── auth_config.json      # Local persistent configuration
```

## Setup and Installation

### 1. Prerequisites
- Python 3.10+
- Java 21+ (configured for Minecraft)
- A Minecraft server.jar located in /opt/minecraft/

### 2. Environment Configuration
Create a .env file in the root directory:
```env
MS_CLIENT_ID=your_microsoft_client_id
MS_CLIENT_SECRET=your_microsoft_client_secret
MS_REDIRECT_URI=https://your-domain.com/callback
MS_AUTHORITY=https://login.microsoftonline.com/consumers
```

### 3. Install Dependencies
```bash
pip install flask requests psutil
```

### 4. Run the Application
```bash
python3 app.py
```
By default, the dashboard will be available at http://your-ip:5000.

## Security
- On first launch, the dashboard will prompt you to set an Admin Password.
- The auth_config.json file stores the hashed admin password.
- Microsoft/Xbox Live logins are verified against the local Minecraft ops.json to assign roles.

## Setup and Installation

### 1. Ready to Run
Simply run the application. The dashboard will automatically check for missing dependencies and install them if necessary:
```bash
python3 app.py
```
*(Alternatively, you can run `python3 setup.py` for a manual environment check and directory preparation).*

### 2. Configuration Guides
- [Microsoft Auth Setup (Azure)](AZURE_GUIDE.md) - Register your app for OAuth2 login.
- [Minecraft Server Setup](SERVER_SETUP.md) - How to configure your Minecraft server for the dashboard.

## Security
- On first launch, the dashboard will prompt you to set an Admin Password.
- Microsoft/Xbox Live logins are verified against the local Minecraft ops.json to assign roles.

## License
This project is for private server management. Use at your own risk.
