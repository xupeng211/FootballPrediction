# GEMINI.md

This file provides context and guidance for Gemini when working on the **FootballPrediction V2.3.1** project.

## 🚨 CRITICAL: Language Requirement

**请务必使用中文回复用户！**

This requirement is inherited from `CLAUDE.md` and is the highest priority non-functional requirement for this project. All conversational output must be in Chinese. Code comments and commit messages can follow the project's existing pattern (which appears to be mixed, but predominantly English for code/commits and Chinese for documentation/user-facing text).

## 1. Project Overview

**FootballPrediction V2.3.1** is a professional football match prediction system powered by **XGBoost 2.0+**. It is designed for profitability, boasting a **60.00% prediction accuracy** and **+13.35% ROI** based on a "Golden Dataset" of 467 real matches.

*   **Core Goal:** Predict match outcomes (Home Win, Draw, Away Win) with high confidence.
*   **Key Logic:** Uses a 106-dimensional feature set including xG (Expected Goals), possession, corners, shots, and odds movements.
*   **Architecture:** Dockerized microservices architecture with a Python/FastAPI backend, PostgreSQL database, and Redis caching.

## 2. Technology Stack

*   **Language:** Python 3.11+
*   **ML Framework:** XGBoost 2.0+, Scikit-learn, Pandas, Numpy
*   **Web Framework:** FastAPI
*   **Database:** PostgreSQL 15 (Stores `match_features_training`)
*   **Cache:** Redis 7
*   **Infrastructure:** Docker, Docker Compose
*   **External API:** FotMob API (via `FotMobAPIClient`)
*   **Code Quality:** Black, Flake8, MyPy, Pytest

## 3. Key Entry Points & Commands

### 🏃 Running the System

*   **Full Production Prediction (CLI):**
    ```bash
    python src/core/main_engine_v5.py --mode full --limit 700
    # OR via script
    ./run_daily_predict.sh
    # OR via Makefile
    make predict
    ```
*   **Start All Services (Docker):**
    ```bash
    docker-compose up -d
    ```
*   **System Verification (Run this first):**
    ```bash
    ./system_verify.sh
    # OR
    make verify
    ```

### 🧪 Testing & Quality

*   **Run Unit Tests:**
    ```bash
    make test
    ```
*   **Full Quality Check (Format + Lint + Type + Security):**
    ```bash
    make quality
    ```
    *Note: Always run `make quality` before committing changes.*
*   **Test Prediction Mode (Verify code changes):**
    ```bash
    python src/core/main_engine_v5.py --mode test
    ```

## 4. Project Structure

*   **`src/core/`**: The heart of the application.
    *   `main_engine_v5.py`: Primary entry point for data harvesting and prediction orchestration.
    *   `inference_engine.py`: Manages the XGBoost model, loading artifacts, and performing inference.
*   **`src/api/`**: External communication.
    *   `fotmob_client.py`: Client for the FotMob API.
*   **`src/data_access/`**: Database and Feature logic.
    *   `processors/advanced_feature_extractor.py`: Calculates the 106 features.
*   **`data/`**: Data persistence.
    *   `models/`: Stores `.joblib` model files and metadata.
    *   `postgres/`: Database storage.
*   **`configs/`** & **`src/config_unified.py`**: Configuration management using Pydantic.

## 5. Development Guidelines

1.  **Strict Mode:** This project enforces strict type checking (MyPy) and code style (Black/Flake8). Do not bypass these checks.
2.  **Database Access:** Always use `src.config_unified.get_settings()` to retrieve DB credentials. **NEVER** hardcode credentials. Use `RealDictCursor` for PostgreSQL connections.
3.  **Feature Engineering:** The system relies on 106 specific features. When modifying feature extraction logic, ensure consistency with `match_features_training` schema in `src/core/main_engine_v5.py`.
4.  **Memory Management:** For large data operations, use paginated queries or generators. The system is designed to handle hundreds of matches.

## 6. Common Tasks

*   **Fixing a Bug:**
    1.  Reproduce with a test case in `tests/`.
    2.  Fix the code.
    3.  Run `make test`.
    4.  Run `make quality`.
*   **Adding a Feature:**
    1.  Investigate `src/core/` to see where it fits.
    2.  Implement following strict typing.
    3.  Add tests.
    4.  Verify with `./system_verify.sh`.

## 7. Troubleshooting

*   **Model Loading Failures:** Check `data/models/` for the existence of `.joblib` files.
*   **DB Connection:** Ensure Docker container `db` is healthy (`docker-compose ps`).
*   **Verification Fails:** Read the output of `./system_verify.sh` carefully; it provides specific fix suggestions.
