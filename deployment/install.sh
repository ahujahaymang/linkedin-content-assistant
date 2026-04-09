#!/bin/bash
set -e

echo "Installing Content Assistant on EC2..."

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS"
    exit 1
fi

# Install system dependencies
echo "Installing system dependencies..."
if [ "$OS" = "amzn" ] || [ "$OS" = "rhel" ] || [ "$OS" = "centos" ]; then
    # Amazon Linux / RHEL / CentOS
    sudo yum update -y
    sudo yum install -y python3.11 python3.11-pip git tar
elif [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    # Ubuntu / Debian
    sudo apt-get update
    sudo apt-get install -y python3.11 python3.11-venv python3-pip git tar
else
    echo "Unsupported OS: $OS"
    exit 1
fi

# Create application user
echo "Creating application user..."
if ! id -u content-assistant > /dev/null 2>&1; then
    sudo useradd -r -s /bin/bash -d /opt/content-assistant content-assistant
fi

# Create application directory
echo "Setting up application directory..."
sudo mkdir -p /opt/content-assistant
sudo chown content-assistant:content-assistant /opt/content-assistant

# Extract deployment package
echo "Extracting deployment package..."
cd /tmp
tar -xzf content-assistant-deploy.tar.gz
sudo cp -r content-assistant-deploy/* /opt/content-assistant/
sudo chown -R content-assistant:content-assistant /opt/content-assistant

# Create virtual environment
echo "Creating Python virtual environment..."
sudo -u content-assistant python3.11 -m venv /opt/content-assistant/venv

# Install Python dependencies
echo "Installing Python dependencies..."
sudo -u content-assistant /opt/content-assistant/venv/bin/pip install --upgrade pip
sudo -u content-assistant /opt/content-assistant/venv/bin/pip install -r /opt/content-assistant/requirements.txt

# Install application package
echo "Installing application package..."
cd /opt/content-assistant
sudo -u content-assistant /opt/content-assistant/venv/bin/pip install -e .

# Create .env file from example
if [ ! -f /opt/content-assistant/.env ]; then
    echo "Creating .env file..."
    sudo cp /opt/content-assistant/.env.example /opt/content-assistant/.env
    sudo chown content-assistant:content-assistant /opt/content-assistant/.env
    sudo chmod 600 /opt/content-assistant/.env
fi

# Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/content-assistant.service > /dev/null <<EOF
[Unit]
Description=Content Assistant
After=network.target

[Service]
Type=simple
User=content-assistant
Group=content-assistant
WorkingDirectory=/opt/content-assistant
Environment="PATH=/opt/content-assistant/venv/bin"
EnvironmentFile=/opt/content-assistant/.env
ExecStart=/opt/content-assistant/venv/bin/python3 -m linkedin_content_assistant.main listen --profile haymang
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=content-assistant

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload

echo ""
echo "✓ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit /opt/content-assistant/.env with your credentials"
echo "2. Upload your profile: scp profiles/active/haymang.yaml ec2-user@HOST:/tmp/"
echo "3. Upload your data: scp -r data/memory/haymang ec2-user@HOST:/tmp/"
echo "4. Move files: sudo cp /tmp/haymang.yaml /opt/content-assistant/profiles/active/"
echo "5. Move data: sudo cp -r /tmp/haymang /opt/content-assistant/data/memory/"
echo "6. Fix permissions: sudo chown -R content-assistant:content-assistant /opt/content-assistant"
echo "7. Start service: sudo systemctl start content-assistant"
echo "8. Enable auto-start: sudo systemctl enable content-assistant"
echo "9. Check status: sudo systemctl status content-assistant"
echo ""
