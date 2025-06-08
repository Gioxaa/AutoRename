#!/bin/bash

echo "Stopping and removing existing containers..."
docker-compose down

echo "Pulling latest changes..."
git pull

echo "Building and starting containers..."
docker-compose up -d --build

echo "Checking container status..."
docker ps

echo "Checking container logs..."
docker-compose logs

echo "Testing connection..."
curl -v http://localhost:8080

echo "Deployment complete!"
echo "Try accessing the application at http://YOUR_SERVER_IP:8080" 