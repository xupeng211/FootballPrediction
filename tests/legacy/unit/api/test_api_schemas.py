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
        status = os.getenv("TEST_API_SCHEMAS_STATUS_17"),
        timestamp=datetime.utcnow().isoformat(),
        service = os.getenv("TEST_API_SCHEMAS_SERVICE_18"),
        version="1.0.0",
        uptime=12.5,
        response_time_ms=8.2,
        checks={
            "database": ServiceCheck(
                status = os.getenv("TEST_API_SCHEMAS_STATUS_17"),
                response_time_ms=1.0,
                details={"message": "db ok"},
            )
        },
    )

    serialized = payload.model_dump()
    assert serialized["status"] == "healthy"
    assert serialized["checks"]["database"]["status"] == "healthy"
    assert serialized["checks"]["database"]["details"]["message"] == "db ok"
