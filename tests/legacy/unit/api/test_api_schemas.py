import os
import warnings
from datetime import datetime

import pytest

os.environ.setdefault("MINIMAL_API_MODE", "true")
warnings.filterwarnings("ignore", category=UserWarning)

from src.api.schemas import HealthCheckResponse, ServiceCheck  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


def test_health_check_response_serialization():
    payload = HealthCheckResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        service="football-prediction-api",
        version="1.0.0",
        uptime=12.5,
        response_time_ms=8.2,
        checks={
            "database": ServiceCheck(
                status="healthy",
                response_time_ms=1.0,
                details={"message": "db ok"},
            )
        },
    )

    serialized = payload.model_dump()
    assert serialized["status"] == "healthy"
    assert serialized["checks"]["database"]["status"] == "healthy"
    assert serialized["checks"]["database"]["details"]["message"] == "db ok"
