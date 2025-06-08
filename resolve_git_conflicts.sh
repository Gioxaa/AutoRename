#!/bin/bash

# Resolve Git conflicts
echo "Resolving Git conflicts..."

# Save our custom changes
echo "Backing up our custom scripts..."
mkdir -p .backup
cp deploy.sh .backup/deploy.sh.custom
cp fix_deploy.sh .backup/fix_deploy.sh.custom

# Reset the files that have conflicts
git checkout -- deploy.sh fix_deploy.sh

# Pull latest changes
git pull

# Restore our custom changes
echo "Restoring our custom scripts..."
cp .backup/deploy.sh.custom deploy.sh
cp .backup/fix_deploy.sh.custom fix_deploy.sh

echo "Git conflicts resolved. You can now proceed with deployment."
echo "Run ./deploy.sh to deploy the application."
