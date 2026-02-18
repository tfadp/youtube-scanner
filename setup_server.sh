#!/bin/bash
# Server setup script for YouTube Scanner
# Run this on your Digital Ocean droplet

echo "=========================================="
echo "YouTube Scanner - Server Setup"
echo "=========================================="

# Update system
echo "Updating system..."
apt update && apt upgrade -y

# Install Python and pip
echo "Installing Python..."
apt install -y python3 python3-pip python3-venv git

# Create app directory
echo "Creating app directory..."
mkdir -p /opt/youtube-scanner
cd /opt/youtube-scanner

# Create virtual environment
echo "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install google-api-python-client python-dotenv anthropic requests

# Create directories
mkdir -p output
mkdir -p memory

echo "=========================================="
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Upload your project files to /opt/youtube-scanner/"
echo "2. Create .env file with your API keys"
echo "3. Run: crontab -e and add the cron job"
echo "=========================================="
