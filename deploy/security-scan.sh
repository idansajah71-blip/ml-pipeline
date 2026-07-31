#!/bin/bash
set -e

# =====================================================
# ML Pipeline - Security Scanning Script
# =====================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[SECURITY]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "Starting security scan..."

# =====================================================
# 1. Python Security Scan
# =====================================================
print_status "Running Python security scan..."

pip install bandit safety 2>/dev/null

print_status "Running Bandit (static analysis)..."
bandit -r app/ -ll -f json -o bandit-report.json || true

if [ -f bandit-report.json ]; then
    ISSUES=$(cat bandit-report.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('metrics', {}).get('_totals', {}).get('SEVERITY.HIGH', 0))" 2>/dev/null || echo "0")
    if [ "$ISSUES" -gt 0 ]; then
        print_warning "High severity issues found in bandit report"
    else
        print_status "Bandit scan passed"
    fi
fi

print_status "Running Safety check..."
safety check -r requirements.txt --json > safety-report.json 2>/dev/null || true

# =====================================================
# 2. Docker Security Scan
# =====================================================
print_status "Running Docker security scan..."

if command -v trivy &> /dev/null; then
    print_status "Scanning Docker images with Trivy..."
    trivy image --severity HIGH,CRITICAL ml-pipeline-backend:latest || true
    trivy image --severity HIGH,CRITICAL ml-pipeline-frontend:latest || true
else
    print_warning "Trivy not installed. Skipping Docker scan."
    print_warning "Install with: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh"
fi

# =====================================================
# 3. Dependency Scan
# =====================================================
print_status "Scanning dependencies..."

if command -v npm &> /dev/null && [ -d "frontend" ]; then
    cd frontend
    npm audit --json > npm-audit.json 2>/dev/null || true
    cd ..
fi

# =====================================================
# 4. Secret Scan
# =====================================================
print_status "Scanning for secrets..."

if command -v gitleaks &> /dev/null; then
    gitleaks detect --report-format json --report-path gitleaks-report.json || true
else
    print_warning "Gitleaks not installed. Skipping secret scan."
    print_warning "Install with: brew install gitleaks"
fi

# =====================================================
# 5. Configuration Audit
# =====================================================
print_status "Auditing configuration..."

AUDIT_RESULTS=()

# Check .env file
if [ -f ".env" ]; then
    if grep -q "JWT_SECRET_KEY=dev-secret" .env; then
        AUDIT_RESULTS+=("CRITICAL: Default JWT secret detected")
    fi
    if grep -q "POSTGRES_PASSWORD=password" .env; then
        AUDIT_RESULTS+=("CRITICAL: Default database password detected")
    fi
fi

# Check for debug mode
if grep -q "DEBUG=true" .env 2>/dev/null; then
    AUDIT_RESULTS+=("WARNING: Debug mode enabled")
fi

# Check for weak passwords
if [ -f ".env" ]; then
    if grep -q "PASSWORD=123456" .env || grep -q "PASSWORD=password" .env; then
        AUDIT_RESULTS+=("CRITICAL: Weak password detected")
    fi
fi

if [ ${#AUDIT_RESULTS[@]} -gt 0 ]; then
    print_warning "Configuration issues found:"
    for result in "${AUDIT_RESULTS[@]}"; do
        echo "  - $result"
    done
else
    print_status "Configuration audit passed"
fi

# =====================================================
# 6. Generate Report
# =====================================================
print_status "Generating security report..."

cat > security-report.md << EOF
# Security Scan Report

**Date:** $(date)
**Scanner:** ML Pipeline Security Scanner

## Summary

### Static Analysis (Bandit)
$(if [ -f bandit-report.json ]; then cat bandit-report.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'High: {data.get(\"metrics\", {}).get(\"_totals\", {}).get(\"SEVERITY.HIGH\", 0)}'); print(f'Medium: {data.get(\"metrics\", {}).get(\"_totals\", {}).get(\"SEVERITY.MEDIUM\", 0)}'); print(f'Low: {data.get(\"metrics\", {}).get(\"_totals\", {}).get(\"SEVERITY.LOW\", 0)}')" 2>/dev/null; else echo "Not run"; fi)

### Dependency Scan (Safety)
$(if [ -f safety-report.json ]; then echo "See safety-report.json"; else echo "Not run"; fi)

### Configuration Audit
$(for result in "${AUDIT_RESULTS[@]}"; do echo "- $result"; done)

## Recommendations

1. Always use strong, unique passwords
2. Keep dependencies up to date
3. Enable HTTPS in production
4. Use environment variables for secrets
5. Regular security audits recommended

EOF

print_status "Security scan completed!"
print_status "Report saved to: security-report.md"
