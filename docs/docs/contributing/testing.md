---
sidebar_position: 2
title: Testing
---

# Testing Guide

Run and write tests for the ML Pipeline.

## Running Tests

### Backend Tests

```bash
# Run all tests
pytest app/tests/ -v

# Run specific test file
pytest app/tests/test_auth.py -v

# Run with coverage
pytest app/tests/ --cov=app --cov-report=html
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run in watch mode
npm run test:watch
```

### Load Tests

```bash
# Run all load tests
./loadtest/run-tests.sh http://localhost:8000 all

# Run Locust
locust -f loadtest/locustfile.py --host=http://localhost:8000

# Run k6
k6 run loadtest/k6-load-test.js
```

### Security Scan

```bash
./deploy/security-scan.sh
```

## Test Structure

### Backend Tests

```
app/tests/
├── conftest.py           # Fixtures (DB, client)
├── test_auth.py          # Authentication tests
├── test_datasets.py      # Dataset upload/list tests
├── test_models.py        # Model CRUD tests
├── test_ml_pipeline.py   # ML pipeline unit tests
└── test_security.py      # Security scanner tests
```

### Frontend Tests

```
frontend/src/__tests__/
├── StatsCard.test.tsx
├── StatusBadge.test.tsx
├── Pagination.test.tsx
├── SearchInput.test.tsx
└── LoadingSpinner.test.tsx
```

## Writing Tests

### Backend Test Example

```python
@pytest.mark.asyncio
async def test_create_model(client: AsyncClient):
    # Register and login
    await client.post("/api/v1/auth/register", json={...})
    login = await client.post("/api/v1/auth/login", json={...})
    token = login.json()["access_token"]

    # Create model
    response = await client.post(
        "/api/v1/models",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test", "algorithm": "random_forest", "target_column": "target"}
    )
    assert response.status_code == 201
```

### Frontend Test Example

```tsx
import { render, screen } from '@testing-library/react';
import StatsCard from '@/components/StatsCard';
import { Brain } from 'lucide-react';

describe('StatsCard', () => {
  it('renders title and value', () => {
    render(<StatsCard title="Models" value={42} icon={Brain} />);
    expect(screen.getByText('Models')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });
});
```

## CI/CD Testing

Tests run automatically on:
- **Push to main/develop** - Full test suite
- **Pull Request** - Full test suite + linting
- **Tag push** - Full test suite + Docker build

See `.github/workflows/ci.yml` for details.
