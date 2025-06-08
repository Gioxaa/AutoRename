#!/bin/bash

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install required packages
sudo apt-get install -y python3-pip python3-dev build-essential nginx

# Install Python dependencies
pip3 install -r requirements.txt
pip3 install gunicorn

# Configure Nginx
sudo cat > /etc/nginx/sites-available/autorename << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

# Enable the Nginx site
sudo ln -sf /etc/nginx/sites-available/autorename /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx

# Create a systemd service file
sudo cat > /etc/systemd/system/autorename.service << EOF
[Unit]
Description=AutoRename PDF Splitter
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=$(which gunicorn) --bind 127.0.0.1:8000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start and enable the service
sudo systemctl daemon-reload
sudo systemctl start autorename
sudo systemctl enable autorename

echo "Deployment complete! Application should be running at http://YOUR_SERVER_IP"