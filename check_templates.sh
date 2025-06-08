#!/bin/bash

# Check if the templates directory exists
if [ ! -d "./templates" ]; then
  echo "Error: templates directory not found. Creating..."
  mkdir -p templates
fi

# Check if uploads and outputs directories exist
if [ ! -d "./uploads" ]; then
  echo "Creating uploads directory..."
  mkdir -p uploads
fi

if [ ! -d "./outputs" ]; then
  echo "Creating outputs directory..."
  mkdir -p outputs
fi

# Check if template files exist
echo "Checking required templates..."
cd templates

if [ ! -f "index.html" ] || [ ! -f "configure.html" ] || [ ! -f "result.html" ]; then
  echo "Warning: Some template files are missing. Please make sure all required template files exist."
fi

cd ..

echo "Checks complete. Now continuing with deployment..." 