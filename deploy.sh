#!/bin/bash

# Check for required files and directories
echo "Checking for required files and directories..."
if [ ! -d "./templates" ]; then
  echo "Error: templates directory not found!"
  echo "Make sure you're running this script from the application root directory."
  exit 1
fi

if [ ! -f "./app.py" ] || [ ! -f "./wsgi.py" ]; then
  echo "Error: Required application files not found!"
  echo "Make sure you're running this script from the application root directory."
  exit 1
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p uploads outputs
chmod 777 uploads outputs

# Update system with error handling
echo "Updating system packages..."
sudo apt-get update || echo "Warning: apt-get update encountered errors, continuing anyway..."
sudo apt-get upgrade -y || echo "Warning: apt-get upgrade encountered errors, continuing anyway..."

# Install required packages
echo "Installing required packages..."
sudo apt-get install -y python3-pip python3-dev build-essential nginx

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt
pip3 install gunicorn

# Configure Nginx
echo "Configuring Nginx..."
sudo cat > /etc/nginx/sites-available/autorename << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    # Increase max upload size
    client_max_body_size 50M;
}
EOF

# Enable the Nginx site
sudo ln -sf /etc/nginx/sites-available/autorename /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx

# Create a systemd service file
echo "Setting up systemd service..."
sudo cat > /etc/systemd/system/autorename.service << EOF
[Unit]
Description=AutoRename PDF Splitter
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=$(which gunicorn) --workers 3 --bind 127.0.0.1:8000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start and enable the service
sudo systemctl daemon-reload
sudo systemctl start autorename
sudo systemctl enable autorename

SERVER_IP=$(curl -s ifconfig.me || curl -s icanhazip.com || echo "YOUR_SERVER_IP")
echo "Deployment complete! Application should be running at http://$SERVER_IP"
echo "Check status with: sudo systemctl status autorename"