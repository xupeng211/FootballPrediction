# GEMINI.md - Football Prediction Project

## Project Overview

This is a Python-based Football Prediction system built with FastAPI. It serves as an enterprise-level application for predicting football match outcomes. The project uses a modern technology stack, including:

*   **Backend:** Python 3.11+, FastAPI
*   **Database:** PostgreSQL (with SQLAlchemy and Alembic for migrations)
*   **Cache:** Redis
*   **Machine Learning:** scikit-learn, pandas, numpy
*   **Containerization:** Docker and Docker Compose
*   **Task Queue:** Celery

The project is well-structured with a clear separation of concerns, following modern software engineering best practices. It includes a comprehensive suite of development and operational tools, managed primarily through a detailed `Makefile`.

## Building and Running

The project uses a `Makefile` to streamline common development tasks.

### Environment Setup

1.  **Create a virtual environment and install dependencies:**
    ```bash
    make install
    ```

2.  **Load project context (important for AI-assisted development):**
    ```bash
    make context
    ```

### Running the Application

*   **Run the application locally using Docker Compose:**
    ```bash
    make up
    ```
    This will start the FastAPI application, PostgreSQL database, and Redis cache. The API will be available at `http://localhost:8000`.

*   **Stop the application:**
    ```bash
    make down
    ```

### Running Tests

*   **Run the full test suite:**
    ```bash
    make test
    ```

*   **Run tests with coverage:**
    ```bash
    make coverage
    ```
    The coverage report will be generated in the `htmlcov/` directory.

*   **Run tests in a clean Docker environment:**
    ```bash
    ./scripts/run_tests_in_docker.sh
    ```

### Code Quality

*   **Run linting and formatting:**
    ```bash
    make fmt
    ```

*   **Run static type checking with mypy:**
    ```bash
    make type-check
    ```

*   **Run a full CI simulation locally:**
    ```bash
    make ci
    ```

## Development Conventions

*   **Dependency Management:** Dependencies are managed using `pip-tools`. The core dependencies are defined in `requirements/*.in` files and locked into `requirements/*.lock` files. Use `make lock-deps` to update the lock files.
*   **Code Style:** The project uses `ruff` for linting and formatting, configured in `pyproject.toml`.
*   **Type Checking:** `mypy` is used for static type checking, with configurations in `mypy.ini`.
*   **Testing:** `pytest` is the testing framework. Tests are located in the `tests/` directory.
*   **Continuous Integration:** The project has CI/CD configured with GitHub Actions (`.github/workflows/`). A local CI verification script (`./ci-verify.sh`) is also available.
*   **Database Migrations:** `alembic` is used for database migrations. Migration scripts are located in the `alembic/versions/` directory.
