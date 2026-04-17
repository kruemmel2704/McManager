# Minecraft Server Configuration for McManager

For the dashboard to correctly manage and interact with your Minecraft server, follow these configuration steps.

## 1. Directory Structure

The dashboard expects the Minecraft server files to be located in specific paths (adjustable in `mc_manager/core/config.py`):

- **Main Directory**: `/opt/minecraft/`
- **Server Jar**: Should be named `server.jar` in that directory (or updated in settings).
- **Properties**: `/opt/minecraft/server.properties`
- **Permissions**: `/opt/minecraft/ops.json`

## 2. Java Installation

Minecraft 1.20.5+ requires **Java 21**. Ensure it is installed and available in your system path:

```bash
# Ubuntu/Debian
sudo apt install openjdk-21-jre-headless
```

## 3. Configure `server.properties`

The dashboard manages these automatically, but for the first start, ensure:
- `enable-query=true`: Recommended for detailed info (though current version uses process monitoring).
- `rcon.password`: (Not currently required as the dashboard uses direct console pipes).

## 4. Setting Up Roles (OPs)

The dashboard uses your server's `ops.json` to determine user roles:
- **Admin**: Users defined in the dashboard setup (Web Admin).
- **OP**: Players listed in `ops.json`. They can start/stop the server and change settings.
- **Viewer**: Authenticated players NOT in `ops.json`. They can only view the console and status.

To add an OP manually before the dashboard is running:
1. Create/Edit `/opt/minecraft/ops.json`.
2. Ensure the user's UUID and Name are correct.

## 5. File Permissions

The user running the dashboard MUST have write access to `/opt/minecraft/`.

```bash
sudo chown -R $USER:$USER /opt/minecraft
```

## 6. Running the Dashboard

Once the server is configured, run the setup script:

```bash
python3 setup.py
```
This will install dependencies and prepare the environment.
