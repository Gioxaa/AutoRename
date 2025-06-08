#!/bin/bash

# Exit on error
set -e

echo "=== Setting up HTTPS for PDF Splitter & Auto Renamer ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

# Install Nginx and Certbot if not installed
echo "Installing Nginx and Certbot..."
apt update
apt install -y nginx certbot python3-certbot-nginx

# Ask for domain name
read -p "Enter your domain name (e.g., example.com): " DOMAIN_NAME

# Verify domain points to this server
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "Server IP: $SERVER_IP"
echo "Please make sure your domain $DOMAIN_NAME points to this IP address."
read -p "Continue? (y/n): " CONFIRM

if [[ $CONFIRM != "y" && $CONFIRM != "Y" ]]; then
  echo "Aborted."
  exit 1
fi

# Create Nginx configuration
echo "Setting up Nginx configuration..."
cat > /etc/nginx/sites-available/$DOMAIN_NAME << EOL
server {
    listen 80;
    server_name $DOMAIN_NAME;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Increase max upload size
    client_max_body_size 50M;
}
EOL

# Enable the site
ln -sf /etc/nginx/sites-available/$DOMAIN_NAME /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# Obtain SSL certificate
echo "Obtaining SSL certificate from Let's Encrypt..."
certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME --redirect

# Update docker-compose.yml to use SESSION_COOKIE_SECURE=true
echo "Updating docker-compose.yml for secure cookies..."
cd /root/autorename
sed -i 's/SESSION_COOKIE_SECURE=false/SESSION_COOKIE_SECURE=true/' docker-compose.yml

# Restart the container to apply changes
echo "Restarting Docker container..."
docker-compose down
docker-compose up -d

echo "=== HTTPS Setup Complete! ==="
echo "Your application is now available at https://$DOMAIN_NAME"
echo ""
echo "Certificate will auto-renew via Certbot's renewal service." 