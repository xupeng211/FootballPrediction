from datetime import datetime

import pytest

from src.models import AnalysisResult, Content, ContentType
from src.services.content_analysis import ContentAnalysisService

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_content_analysis_requires_initialization() -> None:
    service = ContentAnalysisService()
    content = Content(
        id="c-1",
        title="Match Preview",
        content_type=ContentType.TEXT,
        data={"summary": "Team A vs Team B"},
        created_at=datetime.utcnow(),
    )

    with pytest.raises(RuntimeError):
        await service.analyze_content(content)

    assert await service.initialize() is True
    result = await service.analyze_content(content)

    assert isinstance(result, AnalysisResult)
    assert result.content_id == content.id
    assert result.result.get("sentiment") == "positive"


@pytest.mark.asyncio
async def test_batch_analyze_returns_results_for_each_content() -> None:
    service = ContentAnalysisService()
    await service.initialize()

    contents = [
        Content(
            id=f"item-{idx}",
            title=f"Article {idx}",
            content_type=ContentType.TEXT,
            data={"summary": f"Content {idx}"},
            created_at=datetime.utcnow(),
        )
        for idx in range(3)
    ]

    results = await service.batch_analyze(contents)

    assert len(results) == len(contents)
    assert all(r.content_id.startswith("item-") for r in results)


def test_analyze_text_handles_empty_and_non_empty_input() -> None:
    service = ContentAnalysisService()

    empty_result = service.analyze_text("")
    assert empty_result == {"error": "Empty text"}

    analysis = service.analyze_text("football prediction improves fan insight")
    assert analysis["word_count"] == 5
    assert analysis["keywords"] == [
        "football",
        "prediction",
        "improves",
        "fan",
        "insight",
    ]
