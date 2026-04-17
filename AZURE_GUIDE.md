# Deploying McManager on Microsoft Azure

This guide walks you through the process of setting up a Minecraft server and this dashboard on a Microsoft Azure Virtual Machine.

## 1. Create an Azure Virtual Machine

1. Log in to the [Azure Portal](https://portal.azure.com/).
2. Click **"Create a resource"** and search for **"Ubuntu Server 22.04 LTS"**.
3. **Instance Details**:
   - **Region**: Choose one closest to your players.
   - **Size**: For Minecraft, a **B2s** (4GB RAM) is the bare minimum, but **B2ms** (8GB RAM) is recommended for better performance.
4. **Administrator Account**:
   - Use **SSH Public Key** (more secure) or **Password**.
5. **Inbound Port Rules**:
   - Initially, allow **SSH (22)**. We will add more ports later.

## 2. Configure Networking (Firewall)

To access your dashboard and the Minecraft server, you need to open specific ports in the Azure Network Security Group (NSG).

1. Go to your VM's **Networking** tab.
2. Add **Inbound port rules**:
   - **Port 25565**: Protocol TCP (Minecraft Server).
   - **Port 5000**: Protocol TCP (McManager Dashboard).
   - **Port 19132** (Optional): Protocol UDP (If using Bedrock/Geyser).

## 3. Prepare the Server Environment

Connect to your VM via SSH and run the following commands:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Java 21 (Required for modern Minecraft)
sudo apt install openjdk-21-jre-headless -y

# Install Python and Pip
sudo apt install python3 python3-pip -y

# Create the standard directory
sudo mkdir -p /opt/minecraft
sudo chown $USER:$USER /opt/minecraft
```

## 4. Install McManager

1. **Clone the repository**:
   ```bash
   cd /opt/minecraft
   git clone <your-repo-url> dashboard
   cd dashboard
   ```

2. **Install Python dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Configure Environment**:
   Copy the example environment file and fill in your secrets.
   ```bash
   cp .env.example .env
   nano .env
   ```

## 5. Running as a Background Service

To keep the dashboard running even after you logout, use a systemd service.

1. **Create the service file**:
   ```bash
   sudo nano /etc/systemd/system/mcmanager.service
   ```

2. **Paste the following content** (update `User` and `WorkingDirectory` if necessary):
   ```ini
   [Unit]
   Description=Minecraft Manager Dashboard
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/opt/minecraft/dashboard
   ExecStart=/usr/bin/python3 app.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start the service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable mcmanager
   sudo systemctl start mcmanager
   ```

## 6. Accessing the Dashboard

You can now access your dashboard at:
`http://<your-azure-vm-ip>:5000`

> [!TIP]
> **Domain & SSL**: For production, it's recommended to set up a DNS record (like `mc.example.com`) and use **Nginx** with **Certbot** as a reverse proxy to provide HTTPS access.
