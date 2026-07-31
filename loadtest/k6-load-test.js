import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

const API_BASE = __ENV.API_BASE_URL || 'http://localhost:8000';

const requestCounter = new Counter('requests');
const errorRate = new Rate('errors');
const requestDuration = new Trend('request_duration');

export const options = {
  scenarios: {
    constant_rate: {
      executor: 'constant-arrival-rate',
      rate: 100,
      timeUnit: '1s',
      duration: '2m',
      preAllocatedVUs: 50,
      maxVUs: 200,
    },
    ramp_up: {
      executor: 'ramping-arrival-rate',
      startRate: 10,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 200,
      stages: [
        { target: 50, duration: '1m' },
        { target: 100, duration: '2m' },
        { target: 50, duration: '1m' },
        { target: 0, duration: '30s' },
      ],
    },
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 100 },
        { duration: '1m', target: 200 },
        { duration: '30s', target: 100 },
        { duration: '30s', target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.1'],
    errors: ['rate<0.1'],
  },
};

function getRandomFloat(min, max) {
  return Math.random() * (max - min) + min;
}

function getRandomString(length) {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  return Array(length).fill(chars).map(c => c[Math.floor(Math.random() * c.length)]).join('');
}

export default function () {
  group('Health Check', () => {
    const res = http.get(`${API_BASE}/health`);
    check(res, {
      'status is 200': (r) => r.status === 200,
      'response time < 100ms': (r) => r.timings.duration < 100,
    });
    requestCounter.add(1);
    errorRate.add(res.status !== 200);
    requestDuration.add(res.timings.duration);
  });

  group('Get Algorithms', () => {
    const res = http.get(`${API_BASE}/api/v1/algorithms`);
    check(res, {
      'status is 200': (r) => r.status === 200,
      'has algorithms': (r) => r.json('algorithms') && r.json('algorithms').length > 0,
    });
    requestCounter.add(1);
    errorRate.add(res.status !== 200);
    requestDuration.add(res.timings.duration);
  });

  group('Authentication', () => {
    const loginRes = http.post(`${API_BASE}/api/v1/auth/login`, JSON.stringify({
      email: 'admin@mlpipeline.com',
      password: 'admin123',
    }), {
      headers: { 'Content-Type': 'application/json' },
    });

    check(loginRes, {
      'login successful': (r) => r.status === 200,
      'has token': (r) => r.json('access_token') !== undefined,
    });

    requestCounter.add(1);
    errorRate.add(loginRes.status !== 200);
    requestDuration.add(loginRes.timings.duration);

    const token = loginRes.json('access_token');

    if (token) {
      const authHeaders = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      };

      group('List Models', () => {
        const res = http.get(`${API_BASE}/api/v1/models`, {
          headers: authHeaders,
        });
        check(res, {
          'status is 200': (r) => r.status === 200,
        });
        requestCounter.add(1);
        errorRate.add(res.status !== 200);
        requestDuration.add(res.timings.duration);
      });

      group('Create Model', () => {
        const algorithms = ['random_forest', 'gradient_boosting', 'logistic_regression'];
        const res = http.post(`${API_BASE}/api/v1/models`, JSON.stringify({
          name: `TestModel_${getRandomString(6)}`,
          algorithm: algorithms[Math.floor(Math.random() * algorithms.length)],
          target_column: 'target',
        }), {
          headers: authHeaders,
        });
        check(res, {
          'model created': (r) => r.status === 201,
        });
        requestCounter.add(1);
        errorRate.add(res.status !== 201);
        requestDuration.add(res.timings.duration);
      });

      group('Monitoring Stats', () => {
        const res = http.get(`${API_BASE}/api/v1/monitoring/stats`, {
          headers: authHeaders,
        });
        check(res, {
          'status is 200': (r) => r.status === 200,
        });
        requestCounter.add(1);
        errorRate.add(res.status !== 200);
        requestDuration.add(res.timings.duration);
      });
    }
  });

  group('API Documentation', () => {
    const res = http.get(`${API_BASE}/docs`);
    check(res, {
      'docs accessible': (r) => r.status === 200,
    });
    requestCounter.add(1);
    errorRate.add(res.status !== 200);
    requestDuration.add(res.timings.duration);
  });

  sleep(Math.random() * 3 + 1);
}

export function handleSummary(data) {
  const summary = {
    timestamp: new Date().toISOString(),
    total_requests: data.metrics.http_reqs?.values?.count || 0,
    failed_requests: data.metrics.http_req_failed?.values?.passes || 0,
    avg_response_time: data.metrics.http_req_duration?.values?.avg || 0,
    p95_response_time: data.metrics.http_req_duration?.values['p(95)'] || 0,
    p99_response_time: data.metrics.http_req_duration?.values['p(99)'] || 0,
    rps: data.metrics.http_reqs?.values?.rate || 0,
  };

  console.log(JSON.stringify(summary, null, 2));

  return {
    'loadtest/summary.json': JSON.stringify(summary, null, 2),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}
