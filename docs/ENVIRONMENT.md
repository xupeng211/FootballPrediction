# Environment Specification - V139.1

**Generated**: 2026-01-05
**Status**: Environment-Frozen Stable Base

---

## System Environment

| Component | Version | Status |
|-----------|---------|--------|
| **Python** | 3.11.9 | ✅ Stable |
| **Playwright** | 1.57.0 | ✅ Latest |
| **Playwright Stealth** | 2.0.0 | ✅ Active |

---

## Browser Drivers (Playwright)

```
Playwright version: 1.57.0
Chromium: 131.0.6778.86
Firefox: 123.0
WebKit: 18.2
```

**Installation Command**:
```bash
playwright install --with-deps chromium
```

---

## Core Dependencies (V139.1 Frozen)

### Machine Learning
- `xgboost==3.0.5`
- `lightgbm==4.6.0`
- `scikit-learn==1.6.1`

### Browser Automation
- `playwright==1.57.0`
- `playwright-stealth==2.0.0`
- `beautifulsoup4==4.14.3`

### Database
- `asyncpg==0.31.0`
- `psycopg2-binary==2.9.10`
- `alembic==1.17.2`

### API & HTTP
- `fastapi==0.124.4`
- `aiohttp==3.13.2`
- `httpx==0.28.1`

---

## Installation Instructions

### 1. Create Virtual Environment
```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 2. Install Dependencies
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 3. Install Playwright Browsers
```bash
playwright install --with-deps chromium
```

### 4. Verify Installation
```bash
python --version      # Should be 3.11.9
playwright --version  # Should be 1.57.0
pytest tests/unit/    # Run unit tests
```

---

## Known Issues & Solutions

### Issue 1: Playwright Browser Download
**Symptom**: `playwright install` fails with timeout
**Solution**:
```bash
# Set environment variable for China mainland
export PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/
playwright install --with-deps chromium
```

### Issue 2: PostgreSQL Connection
**Symptom**: `connection refused` to database
**Solution**:
```bash
# Start PostgreSQL service
docker-compose up -d db
# or
sudo systemctl start postgresql
```

### Issue 3: Redis Connection
**Symptom**: `Error connecting to Redis`
**Solution**:
```bash
# Start Redis service
docker-compose up -d redis
# or
sudo systemctl start redis
```

---

## Version Locking Policy

**Policy**: All dependencies are frozen to specific versions in `requirements.txt`.

**Rationale**:
- Ensures reproducible deployments
- Prevents unexpected breaking changes
- Facilitates rollback capabilities
- Supports long-term stability

**Update Process**:
1. Test new dependency versions in development environment
2. Run full test suite (`pytest tests/`)
3. Update requirements.txt with verified versions
4. Commit with version bump (e.g., V139.2)
5. Tag release in Git

---

## Environment Variables Reference

See `.env.example` for the complete list of required environment variables.

**Critical Variables** (must be set):
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
- `ENVIRONMENT` (development/staging/production)

---

## Support Matrix

| Python Version | Playwright | Status |
|----------------|------------|--------|
| 3.11.x | 1.57.0 | ✅ Supported (Current) |
| 3.12.x | 1.57.0 | ⚠️ Experimental |
| 3.10.x | 1.57.0 | ❌ Deprecated |

**Recommendation**: Use Python 3.11.9 for optimal compatibility.

---

**Document Owner**: DevOps Team
**Last Updated**: 2026-01-05
**Next Review**: 2026-02-05
