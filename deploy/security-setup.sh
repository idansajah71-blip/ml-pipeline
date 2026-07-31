#!/bin/bash
set -e

# =====================================================
# ML Pipeline - Security Setup Script
# =====================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[SECURITY]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_status "Setting up security configurations..."

# =====================================================
# 1. Generate secure keys
# =====================================================
print_status "Generating secure keys..."

JWT_SECRET=$(openssl rand -hex 32)
API_SECRET=$(openssl rand -base64 32)
DB_PASSWORD=$(openssl rand -base64 32)

print_status "Generated keys:"
echo "JWT_SECRET: $JWT_SECRET"
echo "API_SECRET: $API_SECRET"
echo "DB_PASSWORD: $DB_PASSWORD"

# =====================================================
# 2. Update .env file
# =====================================================
if [ -f ".env" ]; then
    print_status "Updating .env file..."
    
    sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET/" .env
    sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$DB_PASSWORD/" .env
    
    print_status ".env updated"
else
    print_warning ".env file not found. Please update manually."
fi

# =====================================================
# 3. Setup SSL/TLS
# =====================================================
read -p "Do you want to setup SSL/TLS? (y/n): " setup_ssl
if [ "$setup_ssl" = "y" ]; then
    read -p "Enter your domain: " domain
    
    print_status "Installing Certbot..."
    sudo apt-get install -y certbot python3-certbot-nginx
    
    print_status "Obtaining SSL certificate..."
    sudo certbot --nginx -d $domain --non-interactive --agree-tos --email admin@$domain
    
    print_status "SSL/TLS setup completed!"
fi

# =====================================================
# 4. Setup firewall
# =====================================================
read -p "Do you want to configure firewall? (y/n): " setup_firewall
if [ "$setup_firewall" = "y" ]; then
    print_status "Configuring UFW firewall..."
    
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow ssh
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    
    sudo ufw enable
    
    print_status "Firewall configured!"
fi

# =====================================================
# 5. Setup fail2ban
# =====================================================
read -p "Do you want to install fail2ban? (y/n): " setup_fail2ban
if [ "$setup_fail2ban" = "y" ]; then
    print_status "Installing fail2ban..."
    
    sudo apt-get install -y fail2ban
    
    cat > /tmp/jail.local << EOF
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600
EOF
    
    sudo cp /tmp/jail.local /etc/fail2ban/jail.local
    sudo systemctl restart fail2ban
    
    print_status "fail2ban installed!"
fi

# =====================================================
# 6. Setup audit logging
# =====================================================
print_status "Configuring audit logging..."

if [ ! -d "/var/log/ml-pipeline" ]; then
    sudo mkdir -p /var/log/ml-pipeline
    sudo chown $USER:$USER /var/log/ml-pipeline
fi

print_status "=========================================="
print_status "Security setup completed!"
print_status "=========================================="
print_status ""
print_status "Important:"
print_status "  1. Save the generated keys securely"
print_status "  2. Update your production .env file"
print_status "  3. Test your application"
print_status "  4. Run security scan: ./deploy/security-scan.sh"
