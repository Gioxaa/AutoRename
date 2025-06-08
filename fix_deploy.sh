#!/bin/bash

# Fix repository issues
echo "Fixing repository issues..."

# Find and disable problematic repositories
if [ -d "/etc/apt/sources.list.d" ]; then
  echo "Looking for problematic speedtest repositories..."
  sudo find /etc/apt/sources.list.d -name "*speedtest*" -exec sudo mv {} {}.disabled \; 2>/dev/null || echo "No speedtest repositories found"
  
  # Alternative method to disable the repository
  echo "Trying alternative method to disable speedtest repository..."
  if grep -r "packagecloud.io/ookla/speedtest-cli" /etc/apt/ > /dev/null; then
    echo "Found problematic repository reference, disabling..."
    sudo grep -l "packagecloud.io/ookla/speedtest-cli" /etc/apt/sources.list.d/* | xargs -r sudo sed -i 's/^deb/#deb/g'
  fi
fi

# Update source lists
echo "Updating apt sources with insecure repositories disabled..."
sudo apt-get update -o Acquire::AllowInsecureRepositories=false || true

echo "Repository fix complete. Now you can run the deploy script."
echo "./deploy.sh" 