# ML Pipeline

Production-ready Machine Learning Pipeline with FastAPI backend and Next.js dashboard.

## Features

### Backend
- **FastAPI** - High-performance async API
- **scikit-learn** - ML algorithms (Random Forest, Gradient Boosting, SVM, etc.)
- **PostgreSQL** - Data persistence
- **Redis** - Caching & session management
- **JWT Auth** - Authentication & RBAC (Admin, Data Scientist, User)
- **Model Registry** - Version control for ML models
- **A/B Testing** - Model comparison framework
- **Monitoring** - System & model metrics

### Frontend Dashboard
- **Next.js 14** - React with App Router
- **Tailwind CSS** - Modern UI styling
- **Recharts** - Data visualization
- **Real-time** - Live monitoring updates

### CI/CD
- **GitHub Actions** - Automated testing and deployment
- **Docker** - Containerized builds
- **Multi-stage** - Staging and production environments

## Quick Start

### Docker (Recommended)

```bash
# Clone and setup
cp .env.example .env

# Start all services
docker-compose up -d

# Seed database
docker-compose exec app python scripts/seed.py

# Access
# Dashboard: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### Local Development

```bash
# Backend
pip install -r requirements.txt
docker-compose up -d postgres redis
python scripts/seed.py
python run.py

# Frontend
cd frontend
npm install
npm run dev
```

## CI/CD Pipeline

### Workflows

| Workflow | Trigger | Description |
|----------|---------|-------------|
| `ci.yml` | Push/PR to main/develop | Run tests, linting, Docker build |
| `docker-publish.yml` | Push tag v*.*.* | Build and push Docker images |
| `deploy-staging.yml` | Push to develop | Deploy to staging server |

### Setup Secrets

Add these secrets in GitHub Settings > Secrets:

```
PRODUCTION_HOST=your-server-ip
PRODUCTION_USER=deploy
PRODUCTION_SSH_KEY=your-ssh-private-key

STAGING_HOST=your-staging-server-ip
STAGING_USER=deploy
STAGING_SSH_KEY=your-ssh-private-key
```

### Release Process

```bash
# Update version
git tag v1.0.0
git push origin v1.0.0

# GitHub Actions will:
# 1. Run tests
# 2. Build Docker images
# 3. Push to GitHub Container Registry
# 4. Deploy to production server
```

## Dashboard Pages

| Page | Description |
|------|-------------|
| Dashboard | Overview stats, recent models & datasets |
| Datasets | Upload CSV/Excel, preview data |
| Models | Create, train, deploy ML models |
| Experiments | View training experiment results |
| Predictions | Make real-time predictions |
| A/B Tests | Compare model performance |
| Monitoring | System metrics (CPU, Memory, Disk) |

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/api-key` - Generate API key

### Datasets
- `POST /api/v1/datasets` - Upload dataset (CSV/Excel)
- `GET /api/v1/datasets` - List your datasets
- `GET /api/v1/datasets/{id}/preview` - Preview dataset

### Models
- `POST /api/v1/models` - Create model
- `POST /api/v1/models/{id}/train` - Train model
- `POST /api/v1/models/{id}/predict` - Make predictions
- `POST /api/v1/models/{id}/deploy` - Deploy model

### Experiments
- `GET /api/v1/experiments` - List experiments
- `GET /api/v1/experiments/{id}` - Get experiment details

### A/B Testing
- `POST /api/v1/ab-tests` - Create A/B test
- `POST /api/v1/ab-tests/{id}/route` - Route prediction

### Monitoring
- `GET /api/v1/monitoring/stats` - System statistics
- `GET /api/v1/monitoring/system` - System info

## Default Users

| Email | Password | Role |
|-------|----------|------|
| admin@mlpipeline.com | admin123 | Admin |
| datascientist@mlpipeline.com | ds123456 | Data Scientist |
| user@mlpipeline.com | user1234 | User |

## ML Algorithms

- Random Forest
- Gradient Boosting
- Logistic Regression
- SVM
- KNN
- Decision Tree
- AdaBoost
- Bagging
- MLP Neural Network

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Alembic
- **Frontend**: Next.js 14, Tailwind CSS, Recharts
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **ML**: scikit-learn, pandas, numpy
- **Auth**: JWT + API Key
- **CI/CD**: GitHub Actions
- **Deployment**: Docker, Nginx

## Project Structure

```
ml-pipeline/
├── .github/workflows/       # CI/CD workflows
│   ├── ci.yml              # Main CI pipeline
│   ├── docker-publish.yml  # Docker build & push
│   └── deploy-staging.yml  # Staging deployment
├── app/                    # FastAPI backend
│   ├── api/               # API routes
│   ├── core/              # Config, database, security
│   ├── ml/                # ML pipeline
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   └── tests/             # Unit tests
├── frontend/              # Next.js dashboard
│   └── src/
│       ├── app/           # Pages (App Router)
│       ├── components/    # React components
│       ├── lib/           # API client, auth
│       └── types/         # TypeScript types
├── nginx/                 # Nginx config
├── scripts/               # Database scripts
├── docker-compose.yml     # Development
├── docker-compose.prod.yml # Production
└── requirements.txt
```

## Contributing

1. Create a feature branch (`git checkout -b feature/amazing-feature`)
2. Commit your changes (`git commit -m 'Add amazing feature'`)
3. Push to the branch (`git push origin feature/amazing-feature`)
4. Open a Pull Request

## License

This project is licensed under the MIT License.
