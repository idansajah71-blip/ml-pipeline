#!/bin/bash
set -e

# =====================================================
# ML Pipeline - Kubernetes Deployment Script
# =====================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[K8S]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

ENVIRONMENT=${1:-staging}

print_status "Deploying ML Pipeline to Kubernetes ($ENVIRONMENT)"

# =====================================================
# 1. Check prerequisites
# =====================================================
print_status "Checking prerequisites..."

if ! command -v kubectl &> /dev/null; then
    print_error "kubectl not found. Please install kubectl first."
    exit 1
fi

if ! command -v helm &> /dev/null; then
    print_error "helm not found. Please install Helm first."
    exit 1
fi

# Check cluster connection
if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster."
    exit 1
fi

print_status "Prerequisites OK!"

# =====================================================
# 2. Create namespace
# =====================================================
print_status "Creating namespace..."
kubectl create namespace ml-pipeline-$ENVIRONMENT --dry-run=client -o yaml | kubectl apply -f -

# =====================================================
# 3. Generate secrets
# =====================================================
print_status "Generating secrets..."
JWT_SECRET=$(openssl rand -hex 32)
DB_PASSWORD=$(openssl rand -base64 32)

# =====================================================
# 4. Deploy with Helm
# =====================================================
print_status "Deploying with Helm..."

cd k8s/helm/ml-pipeline

helm upgrade --install ml-pipeline-$ENVIRONMENT . \
    --namespace ml-pipeline-$ENVIRONMENT \
    --values values.yaml \
    --values values-$ENVIRONMENT.yaml \
    --set app.secrets.JWT_SECRET_KEY=$JWT_SECRET \
    --set app.secrets.POSTGRES_PASSWORD=$DB_PASSWORD \
    --set postgresql.auth.password=$DB_PASSWORD \
    --set postgresql.auth.postgresPassword=$DB_PASSWORD \
    --wait \
    --timeout 10m

# =====================================================
# 5. Verify deployment
# =====================================================
print_status "Verifying deployment..."

kubectl get pods -n ml-pipeline-$ENVIRONMENT
kubectl get services -n ml-pipeline-$ENVIRONMENT

# =====================================================
# 6. Get ingress URL
# =====================================================
print_status "Getting ingress URL..."

sleep 10

INGRESS_URL=$(kubectl get ingress -n ml-pipeline-$ENVIRONMENT -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")

if [ "$INGRESS_URL" = "pending" ]; then
    INGRESS_URL=$(kubectl get ingress -n ml-pipeline-$ENVIRONMENT -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "pending")
fi

print_status "=========================================="
print_status "Deployment completed!"
print_status "=========================================="
print_status ""
print_status "Namespace: ml-pipeline-$ENVIRONMENT"
print_status ""
print_status "URLs:"
if [ "$INGRESS_URL" != "pending" ]; then
    print_status "  - Frontend: http://$INGRESS_URL"
    print_status "  - API: http://$INGRESS_URL/api/v1"
    print_status "  - API Docs: http://$INGRESS_URL/api/v1/docs"
else
    print_status "  - Ingress is pending. Check with:"
    print_status "    kubectl get ingress -n ml-pipeline-$ENVIRONMENT"
fi
print_status ""
print_status "Useful commands:"
print_status "  - View pods: kubectl get pods -n ml-pipeline-$ENVIRONMENT"
print_status "  - View logs: kubectl logs -f deployment/ml-pipeline-$ENVIRONMENT-backend -n ml-pipeline-$ENVIRONMENT"
print_status "  - Scale: kubectl scale deployment/ml-pipeline-$ENVIRONMENT-backend --replicas=5 -n ml-pipeline-$ENVIRONMENT"
print_status "  - Delete: helm uninstall ml-pipeline-$ENVIRONMENT -n ml-pipeline-$ENVIRONMENT"
