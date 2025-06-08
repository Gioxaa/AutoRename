#!/bin/bash

# Exit on error
set -e

echo "=== PDF Splitter & Auto Renamer Docker Deployment ==="
echo "Starting deployment process..."

# Update system packages
echo "Updating system packages..."
apt update --allow-insecure-repositories
apt upgrade -y

# Install Docker if not installed
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    apt install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io
fi

# Install Docker Compose if not installed
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Start Docker service
echo "Starting Docker service..."
systemctl start docker
systemctl enable docker

# Fix directory structure
echo "Fixing directory structure..."
cd /root/autorename

# Create templates directory if it doesn't exist
mkdir -p templates

# Move HTML files to templates directory if they exist in root
for file in base.html configure.html index.html result.html; do
    if [ -f "$file" ]; then
        echo "Moving $file to templates directory..."
        mv "$file" templates/
    fi
done

# Create necessary directories
mkdir -p uploads outputs

# Set permissions
chmod -R 755 templates uploads outputs

# Create .dockerignore if it doesn't exist
if [ ! -f ".dockerignore" ]; then
    echo "Creating .dockerignore file..."
    cat > .dockerignore << 'EOL'
# Git
.git
.gitignore

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/

# Application specific
uploads/*/
outputs/*/
*.log
*.zip

# Docker
Dockerfile
docker-compose.yml
.dockerignore

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS specific
.DS_Store
Thumbs.db
EOL
fi

# Build and start containers
echo "Building and starting Docker containers..."
docker-compose up -d

# Get server IP address
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "=== Deployment Complete! ==="
echo "Your application should be running at http://$SERVER_IP"
echo ""
echo "Useful Docker commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Restart containers: docker-compose restart"
echo "  - Stop containers: docker-compose down"
echo "  - Update and rebuild: docker-compose up -d --build" 