"""
Mutation testing configuration for the football prediction system.

This configuration defines which files to test, which mutations to apply,
and how to run the mutation testing process.
"""

from pathlib import Path


class MutationConfig:
    """Configuration for mutation testing."""

    # Paths to include in mutation testing
    INCLUDE_PATTERNS = [
        "src/models/*.py",
        "src/services/*.py",
        "src/core/*.py",
        "src/utils/*.py",
    ]

    # Paths to exclude from mutation testing
    EXCLUDE_PATTERNS = [
        "*/migrations/*",
        "*/tests/*",
        "*/venv/*",
        "*/__pycache__/*",
        "*/.*",
        "src/main.py",
        "src/database/models.py",  # Complex ORM models, better to test manually
        "src/api/*",  # API layer, tested at integration level
        "src/monitoring/*",  # Monitoring code, hard to mutate effectively
        "src/streaming/*",  # External dependencies
        "src/tasks/*",  # Celery tasks, complex async code
        "src/data/collectors/*",  # External API integrations
    ]

    # Test runner command
    TEST_RUNNER = "python -m pytest tests/unit/ -x -q --tb=short"

    # Files that should have higher coverage requirements
    CRITICAL_FILES = [
        "src/models/prediction_service.py",
        "src/models/model_training.py",
        "src/services/data_processing.py",
        "src/core/config.py",
        "src/utils/data_validator.py",
    ]

    # Mutation thresholds
    THRESHOLDS = {
        "overall": 75.0,  # Overall mutation score threshold
        "critical": 85.0,  # Critical files mutation score threshold
        "high": 70.0,  # High importance files threshold
        "medium": 60.0,  # Medium importance files threshold
        "low": 50.0,  # Low importance files threshold
    }

    # Mutation testing options
    OPTIONS = {
        "max_workers": 4,  # Number of parallel workers
        "timeout": 30,  # Timeout per test in seconds
        "reraise": False,  # Whether to reraise exceptions
        "incremental": True,  # Whether to use incremental testing
        "cache_mutants": True,  # Whether to cache mutant results
    }

    # Test patterns to run for different file types
    TEST_PATTERNS = {
        "models": "tests/unit/ai/test_*.py",
        "services": "tests/unit/services/test_*.py",
        "core": "tests/unit/test_core_*.py",
        "utils": "tests/unit/test_utils_*.py",
    }

    @classmethod
    def get_include_paths(cls):
        """Get list of paths to include in mutation testing."""
        include_paths = []
        for pattern in cls.INCLUDE_PATTERNS:
            include_paths.extend(list(Path(".").glob(pattern)))
        return [str(p) for p in include_paths if p.is_file()]

    @classmethod
    def get_exclude_paths(cls):
        """Get list of paths to exclude from mutation testing."""
        exclude_paths = []
        for pattern in cls.EXCLUDE_PATTERNS:
            exclude_paths.extend(list(Path(".").glob(pattern)))
        return [str(p) for p in exclude_paths if p.is_file()]

    @classmethod
    def get_file_category(cls, file_path):
        """Determine the category/importance of a file."""
        file_path = str(file_path)

        if any(critical in file_path for critical in cls.CRITICAL_FILES):
            return "critical"
        elif "models/" in file_path:
            return "high"
        elif "services/" in file_path:
            return "high"
        elif "core/" in file_path:
            return "medium"
        elif "utils/" in file_path:
            return "medium"
        else:
            return "low"

    @classmethod
    def get_threshold_for_file(cls, file_path):
        """Get mutation threshold for a specific file."""
        category = cls.get_file_category(file_path)
        return cls.THRESHOLDS.get(category, cls.THRESHOLDS["low"])

    @classmethod
    def generate_mutmut_config(cls):
        """Generate mutmut configuration file."""
        config = {
            "paths_to_mutate": cls.get_include_paths(),
            "tests_dirs": ["tests/unit"],
            "test_runner_command": cls.TEST_RUNNER,
            "exclude_paths": cls.get_exclude_paths(),
            "max_workers": cls.OPTIONS["max_workers"],
            "timeout": cls.OPTIONS["timeout"],
            "incremental": cls.OPTIONS["incremental"],
            "cache_mutants": cls.OPTIONS["cache_mutants"],
            "thresholds": cls.THRESHOLDS,
            "critical_files": cls.CRITICAL_FILES,
        }

        return config


# Create mutmut.ini configuration file
def create_mutmut_ini():
    """Create mutmut.ini configuration file."""
    config_content = """[mutmut]
paths_to_mutate = src/models src/services src/core src/utils
tests_dirs = tests/unit
test_runner_command = python -m pytest tests/unit/ -x -q --tb=short
exclude_paths = */migrations/* */tests/* */venv/* */__pycache__/* */.* src/main.py src/database/models.py src/api/* src/monitoring/* src/streaming/* src/tasks/* src/data/collectors/*
max_workers = 4
timeout = 30
incremental = true
cache_mutants = true

[thresholds]
overall = 75.0
critical = 85.0
high = 70.0
medium = 60.0
low = 50.0

[critical_files]
src/models/prediction_service.py
src/models/model_training.py
src/services/data_processing.py
src/core/config.py
src/utils/data_validator.py
"""

    with open("mutmut.ini", "w") as f:
        f.write(config_content)


if __name__ == "__main__":
    create_mutmut_ini()
    print("mutmut.ini configuration file created successfully!")
