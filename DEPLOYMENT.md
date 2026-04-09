# Deployment Guide - Content Assistant

## Overview

This guide covers deploying the Content Assistant to an AWS EC2 instance in account `601084425795`.

## Prerequisites

- AWS CLI configured with credentials for account `601084425795`
- SSH key pair for EC2 access
- Telegram bot token and chat ID
- AWS credentials with Bedrock access

## Deployment Architecture

```
┌─────────────────────────────────────────┐
│         EC2 Instance (t3.small)         │
│  ┌───────────────────────────────────┐  │
│  │  Content Assistant                │  │
│  │  - Python 3.11                    │  │
│  │  - systemd service                │  │
│  │  - Auto-restart on failure        │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  Data Storage                     │  │
│  │  - /opt/content-assistant/data    │  │
│  │  - /opt/content-assistant/logs    │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
           │                    │
           │                    │
           ▼                    ▼
    AWS Bedrock          Telegram API
    (Claude Sonnet)
```

## Step 1: Launch EC2 Instance

### Option A: Using AWS Console

1. Go to EC2 Console in `us-west-2` region
2. Launch Instance:
   - **Name**: `content-assistant`
   - **AMI**: Amazon Linux 2023 or Ubuntu 22.04 LTS
   - **Instance Type**: `t3.small` (2 vCPU, 2 GB RAM)
   - **Key Pair**: Select or create new
   - **Network**: Default VPC
   - **Security Group**: 
     - Allow SSH (port 22) from your IP
     - Allow HTTPS (port 443) outbound
   - **Storage**: 20 GB gp3
   - **IAM Role**: Create role with Bedrock access (see below)

### Option B: Using AWS CLI

```bash
# Create IAM role for EC2 with Bedrock access
aws iam create-role \
  --role-name ContentAssistantEC2Role \
  --assume-role-policy-document file://deployment/ec2-trust-policy.json

aws iam attach-role-policy \
  --role-name ContentAssistantEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

aws iam create-instance-profile \
  --instance-profile-name ContentAssistantEC2Profile

aws iam add-role-to-instance-profile \
  --instance-profile-name ContentAssistantEC2Profile \
  --role-name ContentAssistantEC2Role

# Launch EC2 instance
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.small \
  --key-name YOUR_KEY_NAME \
  --iam-instance-profile Name=ContentAssistantEC2Profile \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=content-assistant}]' \
  --block-device-mappings 'DeviceName=/dev/xvda,Ebs={VolumeSize=20,VolumeType=gp3}' \
  --region us-west-2
```

## Step 2: Prepare Deployment Package

On your local machine:

```bash
# Create deployment package
./deployment/create-package.sh

# This creates: content-assistant-deploy.tar.gz
```

## Step 3: Deploy to EC2

```bash
# Get EC2 instance public IP
INSTANCE_IP=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=content-assistant" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text \
  --region us-west-2)

# Copy deployment package
scp -i ~/.ssh/YOUR_KEY.pem content-assistant-deploy.tar.gz ec2-user@$INSTANCE_IP:/tmp/

# Run deployment script
ssh -i ~/.ssh/YOUR_KEY.pem ec2-user@$INSTANCE_IP 'bash -s' < deployment/install.sh
```

## Step 4: Configure Environment

SSH into the instance and configure:

```bash
ssh -i ~/.ssh/YOUR_KEY.pem ec2-user@$INSTANCE_IP

# Edit environment file
sudo nano /opt/content-assistant/.env

# Add your credentials:
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
AWS_REGION=us-west-2
```

## Step 5: Start the Service

```bash
# Start the service
sudo systemctl start content-assistant

# Enable auto-start on boot
sudo systemctl enable content-assistant

# Check status
sudo systemctl status content-assistant

# View logs
sudo journalctl -u content-assistant -f
```

## Step 6: Upload Profile and History

From your local machine:

```bash
# Copy profile configuration
scp -i ~/.ssh/YOUR_KEY.pem \
  profiles/active/haymang.yaml \
  ec2-user@$INSTANCE_IP:/tmp/

ssh -i ~/.ssh/YOUR_KEY.pem ec2-user@$INSTANCE_IP \
  "sudo cp /tmp/haymang.yaml /opt/content-assistant/profiles/active/"

# Copy historical data
scp -i ~/.ssh/YOUR_KEY.pem -r \
  data/memory/haymang \
  ec2-user@$INSTANCE_IP:/tmp/

ssh -i ~/.ssh/YOUR_KEY.pem ec2-user@$INSTANCE_IP \
  "sudo cp -r /tmp/haymang /opt/content-assistant/data/memory/ && \
   sudo chown -R content-assistant:content-assistant /opt/content-assistant/data"
```

## Service Management

### Start/Stop/Restart

```bash
sudo systemctl start content-assistant
sudo systemctl stop content-assistant
sudo systemctl restart content-assistant
```

### View Logs

```bash
# Real-time logs
sudo journalctl -u content-assistant -f

# Last 100 lines
sudo journalctl -u content-assistant -n 100

# Logs since today
sudo journalctl -u content-assistant --since today

# Application logs
sudo tail -f /opt/content-assistant/logs/linkedin_content_assistant.log
```

### Check Status

```bash
sudo systemctl status content-assistant
```

## Manual Operations

### Generate a Post

```bash
sudo -u content-assistant /opt/content-assistant/venv/bin/python3 \
  -m linkedin_content_assistant.main generate-once --profile haymang
```

### Listen for Commands

The service runs this automatically, but you can test manually:

```bash
sudo -u content-assistant /opt/content-assistant/venv/bin/python3 \
  -m linkedin_content_assistant.main listen --profile haymang
```

### Analyze Content

```bash
sudo -u content-assistant /opt/content-assistant/venv/bin/python3 \
  -m linkedin_content_assistant.main analyze-content --profile haymang --refresh
```

## Monitoring

### CloudWatch Logs (Optional)

Install CloudWatch agent:

```bash
sudo yum install amazon-cloudwatch-agent -y

# Configure to send logs to CloudWatch
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/content-assistant/deployment/cloudwatch-config.json
```

### Disk Space Monitoring

```bash
# Check disk usage
df -h

# Check application data size
du -sh /opt/content-assistant/data
du -sh /opt/content-assistant/logs
```

## Backup and Recovery

### Backup Data

```bash
# On EC2 instance
sudo tar -czf /tmp/content-assistant-backup-$(date +%Y%m%d).tar.gz \
  -C /opt/content-assistant \
  data profiles config

# Download to local machine
scp -i ~/.ssh/YOUR_KEY.pem \
  ec2-user@$INSTANCE_IP:/tmp/content-assistant-backup-*.tar.gz \
  ./backups/
```

### Restore Data

```bash
# Upload backup to EC2
scp -i ~/.ssh/YOUR_KEY.pem \
  ./backups/content-assistant-backup-20240409.tar.gz \
  ec2-user@$INSTANCE_IP:/tmp/

# Restore on EC2
ssh -i ~/.ssh/YOUR_KEY.pem ec2-user@$INSTANCE_IP
sudo systemctl stop content-assistant
sudo tar -xzf /tmp/content-assistant-backup-20240409.tar.gz -C /opt/content-assistant
sudo chown -R content-assistant:content-assistant /opt/content-assistant/data
sudo systemctl start content-assistant
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status content-assistant

# Check logs for errors
sudo journalctl -u content-assistant -n 50

# Check Python dependencies
sudo -u content-assistant /opt/content-assistant/venv/bin/pip list

# Test configuration
sudo -u content-assistant /opt/content-assistant/venv/bin/python3 \
  -c "from linkedin_content_assistant.config.config import Config; print(Config.load())"
```

### Bedrock Access Issues

```bash
# Check IAM role
aws sts get-caller-identity

# Test Bedrock access
aws bedrock list-foundation-models --region us-west-2

# Check if model is available
aws bedrock get-foundation-model \
  --model-identifier us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --region us-west-2
```

### Telegram Connection Issues

```bash
# Test Telegram bot token
curl https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe

# Test sending message
curl -X POST https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage \
  -d chat_id=${TELEGRAM_CHAT_ID} \
  -d text="Test message"
```

### High Memory Usage

```bash
# Check memory usage
free -h

# Check process memory
ps aux | grep python

# Restart service to clear memory
sudo systemctl restart content-assistant
```

## Cost Estimation

### EC2 Instance (t3.small)
- **On-Demand**: ~$15/month (us-west-2)
- **1-Year Reserved**: ~$10/month
- **Spot Instance**: ~$5/month (with interruptions)

### AWS Bedrock (Claude Sonnet 4.5)
- **Input**: $3 per 1M tokens
- **Output**: $15 per 1M tokens
- **Estimated**: ~$5-10/month (1 post/day)

### Storage (20 GB gp3)
- **Cost**: ~$2/month

### Total Estimated Cost
- **Monthly**: $22-27 (on-demand)
- **Monthly**: $17-22 (reserved instance)

## Security Best Practices

1. **Restrict SSH Access**: Update security group to allow SSH only from your IP
2. **Use IAM Roles**: Never store AWS credentials in files
3. **Rotate Telegram Token**: Periodically regenerate bot token
4. **Enable CloudWatch Logs**: Monitor for suspicious activity
5. **Regular Updates**: Keep system packages updated
6. **Backup Regularly**: Automate daily backups to S3

## Automation

### Daily Backup to S3

Add to crontab:

```bash
# Edit crontab
sudo crontab -e

# Add daily backup at 2 AM
0 2 * * * /opt/content-assistant/deployment/backup-to-s3.sh
```

### Auto-Update System Packages

```bash
# Enable automatic security updates (Amazon Linux)
sudo yum install yum-cron -y
sudo systemctl enable yum-cron
sudo systemctl start yum-cron
```

## Next Steps

1. Set up CloudWatch alarms for service health
2. Configure S3 backup automation
3. Set up SNS notifications for errors
4. Consider using Elastic IP for static IP address
5. Set up Route53 for custom domain (optional)
