# Contributing to ML Pipeline

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 16+
- Redis 7+

### Local Development

```bash
# Clone the repository
git clone https://github.com/idansajah71-blip/ml-pipeline.git
cd ml-pipeline

# Backend setup
pip install -r requirements.txt
cp .env.example .env
python scripts/seed.py
python run.py

# Frontend setup (in another terminal)
cd frontend
npm install
npm run dev
```

### Docker Setup

```bash
docker-compose up -d
docker-compose exec app python scripts/seed.py
```

## Code Standards

### Python (Backend)

- **Formatter**: Black (line length: 100)
- **Linter**: Ruff
- **Type hints**: Required for all functions
- **Docstrings**: Google style for public APIs

```bash
# Format
black app/

# Lint
ruff check app/

# Type check
mypy app/
```

### TypeScript (Frontend)

- **Formatter**: Prettier (via Tailwind)
- **Linter**: ESLint (Next.js config)
- **Components**: Functional with hooks
- **Styling**: Tailwind CSS utility classes

```bash
cd frontend
npm run lint
npm run build
```

## Git Workflow

### Branch Naming

| Prefix | Description |
|--------|-------------|
| `feat/` | New features |
| `fix/` | Bug fixes |
| `docs/` | Documentation |
| `chore/` | Maintenance tasks |
| `refactor/` | Code refactoring |
| `test/` | Adding tests |

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add model comparison endpoint
fix: resolve dataset upload timeout
docs: update API reference
chore: bump dependencies
refactor: extract auth middleware
test: add model training tests
```

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear commits
3. Ensure all tests pass: `pytest` (backend) / `npm test` (frontend)
4. Update documentation if needed
5. Open a PR with a descriptive title and summary

## Testing

### Backend Tests

```bash
# Unit tests
pytest app/tests/ -v

# Integration tests
pytest app/tests/ -v -k "integration"

# With coverage
pytest app/tests/ --cov=app --cov-report=html
```

### Frontend Tests

```bash
cd frontend
npm test
npm run test:watch
```

## Project Structure

```
ml-pipeline/
├── app/                 # FastAPI backend
│   ├── api/            # Route handlers
│   ├── core/           # Config, security, database
│   ├── ml/             # ML pipeline (trainer, processor)
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Business logic
│   └── tests/          # Test suite
├── frontend/           # Next.js dashboard
│   └── src/
│       ├── app/        # Pages (App Router)
│       ├── components/ # React components
│       ├── lib/        # API client, auth, hooks
│       └── types/      # TypeScript types
├── scripts/            # DB init, seed scripts
├── deploy/             # Deployment scripts
├── docs/               # Documentation site
└── k8s/                # Kubernetes manifests
```

## API Guidelines

### Endpoint Naming

- **Plural nouns**: `/models`, `/datasets`, `/experiments`
- **Nested resources**: `/models/{id}/train`
- **Actions as sub-resources**: `/models/{id}/deploy`

### Response Format

```json
{
  "id": "uuid",
  "name": "Model Name",
  "status": "trained",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Error Format

```json
{
  "detail": "Human-readable error message"
}
```

## Getting Help

- Open an issue for bugs or feature requests
- Check existing docs in `/docs`
- Review API docs at `http://localhost:8000/docs` when running locally

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
