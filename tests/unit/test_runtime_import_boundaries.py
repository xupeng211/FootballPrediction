"""PR-A1 runtime import-boundary contracts.

lifecycle: permanent
component: runtime import contract tests
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_python(source: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONPATH": str(REPO_ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return subprocess.run(
        [sys.executable, "-c", source],
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def _assert_subprocess_success(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"


def test_network_packages_import_with_truthful_exports() -> None:
    result = _run_python(
        """
import importlib

network = importlib.import_module('src.infrastructure.network')
python_network = importlib.import_module('src.infrastructure.network.python')
stealth = importlib.import_module('src.infrastructure.network.stealth_client')
assert importlib.import_module('src.infrastructure.network') is network
assert importlib.import_module('src.infrastructure.network.python') is python_network

for module in (network, python_network):
    for name in getattr(module, '__all__', ()):
        assert hasattr(module, name), (module.__name__, name)

assert network.__all__ == ()
assert python_network.__all__ == ()
assert not hasattr(network, 'NetworkShield')
assert not hasattr(python_network, 'NetworkShield')
assert hasattr(stealth, 'StealthClient')
"""
    )
    _assert_subprocess_success(result)


def test_network_import_does_not_create_repository_entries() -> None:
    result = _run_python(
        """
from pathlib import Path

root = Path.cwd()

def snapshot():
    return tuple(
        sorted(
            str(path.relative_to(root))
            for path in root.rglob('*')
            if path.parts[0] != '.git'
        )
    )

before = snapshot()
import src.infrastructure.network
import src.infrastructure.network.python
import src.infrastructure.network.stealth_client
after = snapshot()
assert before == after
"""
    )
    _assert_subprocess_success(result)


def test_ml_engine_delegates_only_to_canonical_inference() -> None:
    result = _run_python(
        """
import importlib

canonical = importlib.import_module('src.ml.inference.model_dispatcher')
compatibility = importlib.import_module('src.ml.engine')

assert compatibility.ModelDispatcher is canonical.ModelDispatcher
assert compatibility.Predictor is canonical.Predictor
assert compatibility.V26ModelDispatcher is canonical.ModelDispatcher
assert compatibility.V26Predictor is canonical.Predictor
assert 'V17MLEngine' not in compatibility.__all__
assert 'main' not in compatibility.__all__
assert not hasattr(compatibility, 'V17MLEngine')
assert not hasattr(compatibility, 'main')
"""
    )
    _assert_subprocess_success(result)


def test_decommissioned_service_container_is_not_importable() -> None:
    result = _run_python(
        """
import importlib
import importlib.util

services = importlib.import_module('src.services')
assert importlib.util.find_spec('src.services.service_container') is None
assert not hasattr(services, 'service_container')
"""
    )
    _assert_subprocess_success(result)


def test_canonical_ml_imports_remain_available() -> None:
    result = _run_python(
        """
from src.ml.inference import ModelDispatcher, Predictor
from src.ml.training import canonical_training_producer

assert ModelDispatcher is not None
assert Predictor is not None
assert canonical_training_producer is not None
"""
    )
    _assert_subprocess_success(result)
