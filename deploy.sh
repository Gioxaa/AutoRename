#!/bin/bash

# Exit on error
set -e

# Update system packages
echo "Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install required packages
echo "Installing required packages..."
sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx

# Create a Python virtual environment
echo "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt
pip install gunicorn

# Create Nginx configuration
echo "Setting up Nginx..."
read -p "Enter your domain name (e.g., example.com): " DOMAIN_NAME

# Create Nginx config file
sudo bash -c "cat > /etc/nginx/sites-available/pdfsplitter << 'EOL'
server {
    listen 80;
    server_name ${DOMAIN_NAME};

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Increase max upload size
    client_max_body_size 50M;
}
EOL"

# Enable the site
sudo ln -sf /etc/nginx/sites-available/pdfsplitter /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Set up SSL with Certbot
echo "Setting up HTTPS with Certbot..."
sudo certbot --nginx -d ${DOMAIN_NAME} --non-interactive --agree-tos --email admin@${DOMAIN_NAME}

# Create systemd service file
echo "Creating systemd service..."
sudo bash -c "cat > /etc/systemd/system/pdfsplitter.service << 'EOL'
[Unit]
Description=PDF Splitter & Auto Renamer
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
EOL"

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable pdfsplitter
sudo systemctl start pdfsplitter

echo "Deployment complete! Your application should be running at https://${DOMAIN_NAME}"
echo "Check status with: sudo systemctl status pdfsplitter" 