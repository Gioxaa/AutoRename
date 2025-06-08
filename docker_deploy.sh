#!/bin/bash

# Exit on error
set -e

# Update system packages
echo "Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install Docker and Docker Compose
echo "Installing Docker and Docker Compose..."
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add current user to docker group
sudo usermod -aG docker $USER
echo "You may need to log out and back in for docker group changes to take effect"

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Build and start the containers
echo "Building and starting Docker containers..."
docker-compose up -d

# Get server IP address
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "Deployment complete! Your application should be running at http://$SERVER_IP"
echo ""
echo "IMPORTANT: Your application is running without HTTPS. This is not recommended for production use."
echo ""
echo "Useful Docker commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Restart containers: docker-compose restart"
echo "  - Stop containers: docker-compose down"
echo "  - Update and rebuild: docker-compose up -d --build" 