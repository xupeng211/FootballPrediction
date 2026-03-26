# GEMINI.md - TITAN Football Prediction Platform

## Project Overview
TITAN is an industrial-grade, production-ready football data harvesting and machine learning prediction platform. It employs a sophisticated multi-layered architecture to discover, collect, and analyze football match data (odds, lineups, xG, etc.) to generate high-accuracy predictions (67.2% threshold).

### Core Technologies
- **Languages:** Node.js (V18+), Python (V3.11+).
- **Frontend/Scraping:** Playwright, Stealth Navigator, Ghost Protocol (30+ UA fingerprints).
- **Backend/ML:** FastAPI, XGBoost (3-Model Consensus), Scikit-learn, Pandas.
- **Data:** PostgreSQL (V15+), JSONB for dynamic feature storage.
- **Infrastructure:** Docker, Docker Compose, Redis (Circuit Breaking/Caching).
- **Quality Assurance:** ESLint, Prettier, Jest/Node:test, Ruff, 80%+ coverage threshold.

### System Architecture
The platform follows a four-layer pipeline architecture:
1.  **L1 Discovery (Node.js):** Automatically discovers upcoming matches (Playwright/FotMob API).
2.  **L2 Harvest (Node.js):** Collects raw odds and match data from multiple sources (22-node proxy pool).
3.  **L3 Smelt (Node.js/Python):** Generates high-dimensional feature vectors (12061D -> 11D "Pure" set).
4.  **ML Engine (Python):** XGBoost-based prediction engine with temporal isolation.

---

## Building and Running

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ & Python 3.11+
- PostgreSQL 15+

### Key Commands

| Action | Command |
| :--- | :--- |
| **Development Setup** | `docker-compose -f docker-compose.dev.yml up -d` |
| **Start Harvesting** | `npm run titan:start` (Production) or `npm run titan:watch` (Sentinel) |
| **Verify Environment** | `npm run titan:check` |
| **Run Unit Tests** | `npm run test:unit` or `node --test tests/unit/*.test.js` |
| **Check Coverage** | `npm run test:coverage` (Threshold: 80% Line/Branch) |
| **Linting (Full QA)** | `npm run qa` (ESLint + Markdownlint + Unit Tests) |
| **ML Training** | `python scripts/ops/TITAN_CORE_TRAIN.py` |
| **ML Prediction** | `python scripts/ops/predict_weekend.py` |
| **Database Status** | `npm run status:db` |

---

## Development Conventions

### Quality & Testing
- **Zero Compromise Policy:** 0 ESLint errors and 80%+ test coverage are enforced via pre-commit hooks.
- **Unit Testing:** Prefers Node.js built-in test runner (`node --test`) for harvesting components for maximum speed and minimal memory footprint.
- **JSDoc/Type Safety:** JSDoc is required for all Node.js core components; Python uses strict typing with Ruff/Mypy audits.

### Engineering Iron Rules
- **Language Policy:** All replies, comments, and logs must be in **Chinese** (project standard).
- **Container-First:** Operations should be executed within Docker containers (`dev` service) whenever possible.
- **Zero Simulation:** Never use `Math.random()` or mock data for core logic; all data must be real and from identified sources.
- **Idempotency:** All harvesting and processing tasks must be idempotent, allowing for safe retries and skipping completed work.
- **Minimal Change:** Prefer surgical, minimal modifications over broad refactoring to maintain system stability.

### ML Engineering Standards
- **Temporal Isolation:** Never use random splits for training/testing. Training must be on historical data (e.g., <= 2025) and testing on future data (e.g., >= 2026).
- **Feature Purity:** The "11-Dimension Combat Set" is the production standard (Elo, Market Value, H2H). Unverified features or post-match statistics (xG, shots) are strictly forbidden in prediction models.
- **Anti-Leakage Audit:** All models must pass a leakage audit (accuracy > 70% is treated as a critical failure due to data leakage).

### Resilience & Scraping
- **Ghost Protocol:** All browser-based harvesters must use `StealthNavigator` and `ProxyRotator`.
- **SOE (Single Source of Entry):** All data transformations must be idempotent and pass through unified engine entry points (e.g., `UltimateExtractor`).
- **Circuit Breaking:** Use `CircuitBreaker` and `RetryPolicy` (Exponential Backoff + Jitter) for all network-dependent operations.

### Deployment & Maintenance
- **Environment:** Configuration is managed via `config/.env` and `config/factory_config.js`.
- **Monitoring:** Prometheus/Grafana integration is available via `npm run monitor:up`.
- **Cookie Auth:** Manual session updates for harvesters are handled via `scripts/capture_auth_v3.js`.
