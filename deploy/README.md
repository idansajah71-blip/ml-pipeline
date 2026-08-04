# Deployment Scripts

This directory contains deployment scripts for various cloud providers.

## AWS EC2

```bash
# SSH into your EC2 instance
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Run the deployment script
curl -sL https://raw.githubusercontent.com/idansajah71-blip/ml-pipeline/main/deploy/aws-ec2.sh | bash
```

## GCP Compute Engine

```bash
# SSH into your GCP VM
gcloud compute ssh ml-pipeline-vm

# Run the deployment script
curl -sL https://raw.githubusercontent.com/idansajah71-blip/ml-pipeline/main/deploy/gcp-compute.sh | bash
```

## Backup & Restore

```bash
# Create backup
./deploy/backup.sh

# List backups
ls -la backups/

# Restore from backup
./deploy/restore.sh 20240101_120000
```

## Health Check

```bash
# Run health check
./deploy/healthcheck.sh
```

## Update

```bash
# Update to latest version
./deploy/update.sh
```

## Prerequisites

- Ubuntu 22.04 LTS
- Docker & Docker Compose
- Git
- 4GB+ RAM recommended
- 20GB+ disk space

## Security Notes

- Change default passwords before deployment
- Use SSH keys for authentication
- Enable firewall (UFW)
- Setup SSL/TLS for production
- Regular backups recommended
