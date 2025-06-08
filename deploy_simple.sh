#!/bin/bash

# Simple deployment script for VPS without git conflicts

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p uploads outputs templates
chmod 777 uploads outputs

# Update system packages (ignore repository errors)
echo "Updating system packages..."
sudo apt-get update -o Acquire::AllowInsecureRepositories=false || echo "Update had errors, continuing..."
sudo apt-get install -y python3-pip python3-dev python3-venv build-essential nginx || exit 1

# Create and activate virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies in virtual environment
echo "Installing Python dependencies in virtual environment..."
pip install --upgrade pip
pip install -r requirements.txt || exit 1
pip install gunicorn || exit 1

# Find available port
echo "Finding available port..."
APP_PORT=5000
while netstat -tuln | grep -q ":$APP_PORT"; do
  echo "Port $APP_PORT is in use, trying next port..."
  APP_PORT=$((APP_PORT + 1))
done
echo "Using port $APP_PORT for application"

# Configure Nginx
echo "Configuring Nginx..."
sudo tee /etc/nginx/sites-available/autorename > /dev/null << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    # Increase max upload size
    client_max_body_size 50M;
}
EOF

# Enable the Nginx site
sudo ln -sf /etc/nginx/sites-available/autorename /etc/nginx/sites-enabled
sudo nginx -t && sudo systemctl restart nginx

# Create a systemd service file
echo "Setting up systemd service..."
sudo tee /etc/systemd/system/autorename.service > /dev/null << EOF
[Unit]
Description=AutoRename PDF Splitter
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:$APP_PORT wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Stop any existing service
sudo systemctl stop autorename 2>/dev/null || true

# Start and enable the service
sudo systemctl daemon-reload
sudo systemctl start autorename || {
  echo "Failed to start service. Check logs with: sudo journalctl -u autorename"
  exit 1
}
sudo systemctl enable autorename

# Get server IP and print access info
SERVER_IP=$(curl -s ifconfig.me || curl -s icanhazip.com || echo "YOUR_SERVER_IP")
echo ""
echo "==================================================="
echo "Deployment complete!"
echo "Application should be running at http://$SERVER_IP"
echo "Check status with: sudo systemctl status autorename"
echo "View logs with: sudo journalctl -u autorename"
echo "===================================================" 