# GEMINI.md

## Project Overview

This is a comprehensive, enterprise-grade Football Prediction system. It's built with a modern Python technology stack and is designed for production use. The project is heavily focused on MLOps, with a sophisticated architecture that includes a FastAPI-based API, a PostgreSQL database, Redis for caching, Kafka for data streaming, and a full suite of tools for monitoring, data lineage, and machine learning experiment tracking.

The project is containerized using Docker and Docker Compose, and it has a strong emphasis on code quality, testing, and CI/CD.

### Key Technologies

* **Backend**: Python, FastAPI
* **Database**: PostgreSQL, Redis
* **Data Streaming**: Kafka, Zookeeper
* **MLOps**: MLflow, Marquez, Feast, Great Expectations
* **Monitoring**: Prometheus, Grafana, Alertmanager
* **Containerization**: Docker, Docker Compose
* **Testing**: pytest, coverage.py
* **Code Quality**: flake8, mypy, black, isort

## Building and Running

The project uses a `Makefile` to streamline the development process. Here are the key commands:

* **`make install`**: Installs all the necessary dependencies.
* **`make test`**: Runs the test suite.
* **`make coverage`**: Runs the test suite with a coverage report.
* **`make lint`**: Runs the linter and type checker.
* **`make fmt`**: Formats the code.
* **`make ci`**: Runs a local simulation of the CI pipeline.
* **`make up`**: Starts the Docker Compose services.
* **`make down`**: Stops the Docker Compose services.

### Local CI Verification

The project includes a `ci-verify.sh` script that runs a comprehensive local CI check. This script should be run before pushing any code to the remote repository.

```bash
./ci-verify.sh
```

## Development Conventions

* **Code Style**: The project uses `black` for code formatting and `isort` for import sorting.
* **Type Hinting**: The project uses `mypy` for static type checking, and all code is expected to be fully type-hinted.
* **Testing**: The project uses `pytest` for testing. All new code should be accompanied by tests, and the test coverage should be maintained at a high level.
* **CI/CD**: The project has a strong focus on CI/CD. All code is expected to pass the local CI checks before being pushed to the remote repository.
