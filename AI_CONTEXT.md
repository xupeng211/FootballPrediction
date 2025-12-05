# AI Context - Football Prediction Project

## 🎯 Project Overview
This is a football data collection and prediction system that uses web scraping to collect Premier League match data from FotMob, with a focus on extracting xG (expected goals) statistics for machine learning applications.

## 🏗️ Core Technology Stack

### **Backend & Database**
- **Python 3.11+** with AsyncIO support
- **Requests + lxml** for web scraping (NO Playwright/Selenium)
- **SQLAlchemy 2.0+** with async support (`asyncpg`)
- **PostgreSQL 15** running in Docker containers
- **FastAPI** for API endpoints (optional)

### **Key Dependencies**
```python
# Core Web Scraping
requests>=2.31.0      # HTTP client
lxml>=4.9.0           # HTML/XML parsing
beautifulsoup4>=4.12.0 # HTML parsing

# Database
SQLAlchemy>=2.0.0     # ORM with async support
asyncpg>=0.28.0        # PostgreSQL async driver
psycopg2-binary>=2.9.0 # PostgreSQL sync driver
alembic>=1.12.0        # Database migrations

# Configuration & Async
python-dotenv>=1.0.0   # Environment variables
aiofiles>=23.0.0       # Async file operations
aiohttp>=3.8.0         # Async HTTP client
```

## 🚫 **CRITICAL: Anti-Scraping Strategy**
**NEVER use Playwright/Selenium/Puppeteer!** This project uses a sophisticated approach:

### **Our Method: requests + Manual GZIP + Stealth Headers**
1. **Direct HTTP requests** with `requests` library
2. **Manual GZIP decompression** for compressed responses
3. **Rotating User-Agent strings** (35 different browser signatures)
4. **Stealth headers** that mimic real browser behavior
5. **Request rate limiting** with random delays (2-4 seconds)

### **Why This Works**
- FotMob blocks browser automation tools but not well-configured HTTP requests
- Our approach mimics real browser traffic without the heavy browser overhead
- Faster, more reliable, and less resource-intensive

## 📊 Data Sources & Collection Strategy

### **L1 Data (League Overview)**
- **Source**: FotMob league pages (e.g., `https://www.fotmob.com/leagues/47/overview/premier-league`)
- **Extraction**: Next.js SSR data from `__NEXT_DATA__` script tags
- **Content**: Basic match information (teams, dates, league IDs)
- **Entry Point**: `src/jobs/run_season_fixtures.py`

### **L2 Data (Match Details)**
- **Source**: FotMob match pages (e.g., `https://www.fotmob.com/match/4813744`)
- **Challenge**: Pages return 404 but contain hidden Next.js data
- **Extraction**: Parse "fake 404" pages for actual match data
- **Content**: xG statistics, lineups, detailed match stats
- **Entry Point**: `src/jobs/run_l2_details.py`

## 🔧 Key Code Locations

### **Data Collection Pipeline**
```python
# Main entry points
src/jobs/run_season_fixtures.py    # L1 league data collection
src/jobs/run_l2_details.py         # L2 match details collection

# Core scraping components
src/collectors/html_fotmob_collector.py  # Main scraper with stealth capabilities
src/collectors/user_agent.py              # User-Agent rotation
src/collectors/rate_limiter.py            # Request rate limiting
src/collectors/proxy_pool.py              # Proxy management (future)

# Database layer
src/database/async_manager.py             # Async database operations
src/database/models/                       # SQLAlchemy models
```

### **Database Schema**
- **teams**: Team information with FotMob external IDs
- **matches**: Match data with completeness tracking
- **Data completeness states**:
  - `partial`: Basic L1 data collected
  - `complete`: Full L2 data with xG and stats

## 🚀 Standard Operations (Makefile)

### **Development Commands**
```bash
# Environment setup
make install          # Install dependencies
make dev              # Start development environment
make db-shell         # Access PostgreSQL

# Data collection
make run-l1           # Run L1 season data collection
make run-l2           # Run L2 match details collection
make db-reset         # Clear match data (safe reset)

# Testing
make test.fast        # Quick core tests
make coverage         # Generate coverage report
```

## 🎯 xG Data Extraction (Critical Component)

### **Why xG Matters**
Expected Goals (xG) is the most predictive feature for football match outcomes
Our L2 collector extracts xG with ~80% success rate

### **Extraction Pattern**
```python
# From FotMob's nested stats structure
stats = {
    'Periods': {
        'All': {
            'stats': [
                {
                    'title': 'Expected Goals',  # Look for this title
                    'stats': [home_xg, away_xg]  # Extract xG values
                }
            ]
        }
    }
}
```

## 🔍 Debugging & Monitoring

### **Common Issues**
1. **FotMob blocking**: Switch User-Agent, add delays
2. **404 responses**: Check if page actually contains hidden data
3. **GZIP compression**: Ensure proper decompression
4. **Database transactions**: Remember explicit `await session.commit()`

### **Monitoring Commands**
```bash
# Check data progress
docker-compose exec db psql -U postgres -d football_prediction -c "SELECT data_completeness, COUNT(*) FROM matches GROUP BY data_completeness;"

# Check xG extraction
docker-compose exec db psql -U postgres -d football_prediction -c "SELECT COUNT(*) FROM matches WHERE stats::text LIKE '%home_xg%';"
```

## 📈 Performance Characteristics

- **L1 Collection**: ~2 minutes for full Premier League season (380 matches)
- **L2 Collection**: ~4-5 seconds per match, ~25 minutes for full dataset
- **Success Rate**: 99.7% (379/380 matches collected successfully)
- **Data Quality**: High-quality xG data, complete lineup information

## 🛠️ Development Workflow

1. **Start with L1**: Collect basic match structure
2. **Run L2**: Extract detailed statistics and xG data
3. **Verify Quality**: Check xG extraction success rate
4. **Export Data**: Use provided SQL dump for ML training

## 🚨 Important Constraints

- **No browser automation**: Always use requests + manual parsing
- **Rate limiting**: Essential to avoid IP blocking
- **Transaction management**: Explicit commits required for async SQLAlchemy
- **Error handling**: Comprehensive logging for debugging web scraping issues

## 📊 Current Data Status

- **Total Matches**: 380 Premier League matches (2023-24 season)
- **Complete Data**: 379 matches with full L2 data
- **Data Format**: PostgreSQL + SQL export (`golden_dataset_premier_league_23_24.sql`)
- **Features Available**: xG statistics, lineups, match events, shot maps

---

**This project demonstrates production-ready web scraping without browser automation, achieving high success rates through intelligent HTTP client configuration and data extraction strategies.**