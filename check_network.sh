#!/bin/bash

echo "=== Network Status Checker ==="

echo -e "\n=== Firewall Status ==="
if command -v ufw &> /dev/null; then
    sudo ufw status
else
    echo "UFW not installed"
fi

echo -e "\n=== Open Ports ==="
sudo netstat -tuln

echo -e "\n=== Docker Containers ==="
docker ps

echo -e "\n=== Docker Networks ==="
docker network ls

echo -e "\n=== Testing Local Connection ==="
curl -v http://localhost:8080

echo -e "\n=== IP Configuration ==="
ip addr show

echo -e "\n=== Route Table ==="
ip route

echo -e "\n=== Check if process is listening on port 8080 ==="
sudo lsof -i :8080

echo -e "\n=== Done ===" 