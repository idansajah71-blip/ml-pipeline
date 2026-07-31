#!/bin/bash
set -e

# =====================================================
# ML Pipeline - Load Testing Script
# =====================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[LOADTEST]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

API_URL=${1:-http://localhost:8000}
TEST_TYPE=${2:-all}

print_status "Starting load tests against: $API_URL"
print_status "Test type: $TEST_TYPE"

# =====================================================
# 1. Check if API is running
# =====================================================
print_status "Checking if API is running..."

if ! curl -f "$API_URL/health" > /dev/null 2>&1; then
    print_error "API is not running at $API_URL"
    exit 1
fi

print_status "API is running!"

# =====================================================
# 2. Install dependencies
# =====================================================
print_status "Installing test dependencies..."

pip install locust aiohttp 2>/dev/null || true

if command -v npm &> /dev/null; then
    npm install -g k6 2>/dev/null || true
fi

# =====================================================
# 3. Run tests based on type
# =====================================================

run_locust_test() {
    print_status "Running Locust tests..."
    
    locust -f loadtest/locustfile.py \
        --host=$API_URL \
        --headless \
        -u 50 \
        -r 10 \
        --run-time 1m \
        --csv=loadtest/locust_results \
        --html=loadtest/locust_report.html \
        2>&1 | tee loadtest/locust_output.log
    
    print_status "Locust tests completed!"
}

run_k6_test() {
    print_status "Running k6 tests..."
    
    if command -v k6 &> /dev/null; then
        API_BASE_URL=$API_URL k6 run \
            --out json=loadtest/k6_results.json \
            loadtest/k6-load-test.js \
            2>&1 | tee loadtest/k6_output.log
        
        print_status "k6 tests completed!"
    else
        print_warning "k6 not installed. Skipping k6 tests."
        print_warning "Install with: sudo apt-get install k6"
    fi
}

run_benchmark() {
    print_status "Running Python benchmark..."
    
    cd loadtest
    python benchmark.py
    cd ..
    
    print_status "Benchmark completed!"
}

case $TEST_TYPE in
    locust)
        run_locust_test
        ;;
    k6)
        run_k6_test
        ;;
    benchmark)
        run_benchmark
        ;;
    all)
        run_locust_test
        run_k6_test
        run_benchmark
        ;;
    *)
        print_error "Unknown test type: $TEST_TYPE"
        print_error "Available types: locust, k6, benchmark, all"
        exit 1
        ;;
esac

# =====================================================
# 4. Generate summary
# =====================================================
print_status "Generating test summary..."

cat > loadtest/summary.md << EOF
# Load Test Summary

**Date:** $(date)
**Target:** $API_URL
**Test Type:** $TEST_TYPE

## Results

### Locust Results
$(if [ -f loadtest/locust_results_stats.csv ]; then
    echo "| Metric | Value |"
    echo "|--------|-------|"
    tail -1 loadtest/locust_results_stats.csv | awk -F',' '{print "| Requests | "$1" |"; print "| Fails | "$4" |"; print "| Avg Response Time | "$8"ms |"; print "| RPS | "$9" |"}'
else
    echo "No Locust results found"
fi)

### k6 Results
$(if [ -f loadtest/summary.json ]; then
    cat loadtest/summary.json | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'- Total Requests: {data.get(\"total_requests\", 0)}')
print(f'- Avg Response Time: {data.get(\"avg_response_time\", 0):.2f}ms')
print(f'- P95 Response Time: {data.get(\"p95_response_time\", 0):.2f}ms')
print(f'- RPS: {data.get(\"rps\", 0):.2f}')
print(f'- Error Rate: {data.get(\"error_rate\", 0)*100:.2f}%')
"
else
    echo "No k6 results found"
fi)

## Files Generated

- loadtest/locust_results_stats.csv
- loadtest/locust_report.html
- loadtest/k6_results.json
- loadtest/benchmark_*.json

EOF

print_status "=========================================="
print_status "Load tests completed!"
print_status "=========================================="
print_status ""
print_status "Results saved to: loadtest/"
print_status "View HTML report: loadtest/locust_report.html"
