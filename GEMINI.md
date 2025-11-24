# GEMINI.md - Football Prediction Project

## Project Overview

This is a Python-based Football Prediction system built with FastAPI. It serves as an enterprise-level application for predicting football match outcomes. The project uses a modern technology stack and a sophisticated architecture to deliver scalable and maintainable predictions.

## Architecture

The project employs a hybrid architecture that combines principles from **Microservices**, **CQRS (Command Query Responsibility Segregation)**, and **Domain-Driven Design (DDD)**.

*   **Microservices**: The system is structured to be deployed as independent services, allowing for scalability and separation of concerns.
*   **CQRS**: The application separates read operations (querying predictions) from write operations (triggering new inferences). This is evident in the separation of read/write logic within the services.
*   **DDD**: The codebase is organized around a domain model, with clear boundaries between the API, services, and data layers.

## Directory Structure

A well-defined directory structure separates concerns and makes the codebase easy to navigate.

*   `src/api/`: Contains the FastAPI web layer. It defines all HTTP endpoints, routers, and Pydantic models for request/response validation.
*   `src/services/`: Holds the core business logic.
    *   `inference_service.py`: The heart of the prediction engine. It loads a pre-trained XGBoost model, fetches features, and executes the prediction.
*   `src/models/`: Contains SQLAlchemy data model definitions, which map to the database tables.
*   `src/cqrs/` & `src/domain/`: These directories support the CQRS and DDD patterns, containing handlers, commands, and domain-specific logic.
*   `config/`: Stores application configuration files, including database settings, API keys, and environment-specific parameters.
*   `tests/`: Contains all automated tests for the application.
*   `models/`: Stores the pre-trained machine learning models (e.g., the XGBoost model file).

## Core Business Logic

The main prediction logic resides in `src/services/inference_service.py`. The typical workflow is as follows:

1.  An API request is received to predict a match (e.g., for a specific `match_id`).
2.  The `InferenceService` is invoked.
3.  The service loads a pre-trained XGBoost model from the `/models` directory.
4.  It queries the database (specifically the `features` table) to retrieve pre-calculated features for the given match.
5.  The features are fed into the model to generate a prediction (e.g., home win, draw, away win).
6.  The result is returned to the user through the API.

## Key API Endpoints

The main API for interacting with the prediction system is defined in `src/api/predictions/router.py`.

*   `GET /predictions/{match_id}`: Retrieves a cached prediction for a specific match.
*   `POST /predictions/{match_id}/predict`: Triggers a new, real-time prediction for a match.
*   `POST /predictions/batch`: Allows for triggering predictions for multiple matches in a single batch request.

## Database

The application uses a PostgreSQL database, managed via SQLAlchemy. A key table is:

*   `features`: Stores pre-computed feature vectors for matches. It contains at least `match_id` and `feature_data` (likely a JSONB column).

---

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

### Code Quality

*   **Run linting and formatting:**
    ```bash
    make fmt
    ```

*   **Run static type checking with mypy:**
    ```bash
    make type-check
    ```

## Development Conventions

*   **Dependency Management:** Dependencies are managed using `pip-tools`. The core dependencies are defined in `requirements/*.in` files.
*   **Code Style:** The project uses `ruff` for linting and formatting.
*   **Type Checking:** `mypy` is used for static type checking.
*   **Testing:** `pytest` is the testing framework.