import os
import warnings
from datetime import datetime

import pytest

os.environ.setdefault("MINIMAL_API_MODE", "true")
warnings.filterwarnings("ignore", category=UserWarning)

from src.models.common_models import AnalysisResult, Content

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")
from src.services.content_analysis import ContentAnalysisService


@pytest.fixture
async def service():
    svc = ContentAnalysisService()
    await svc.initialize()
    try:
        yield svc
    finally:
        await svc.shutdown()


def _make_content(content_id: str, text: str) -> Content:
    return Content(
        id=content_id,
        title=f"内容-{content_id}",
        content_type="text",
        data={"text": text},
        created_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_initialize_and_shutdown_toggle_state():
    svc = ContentAnalysisService()
    assert not getattr(svc, "_initialized", False)
    assert await svc.initialize() is True
    assert svc._initialized is True
    await svc.shutdown()
    assert svc._initialized is False


@pytest.mark.asyncio
async def test_analyze_content_returns_analysis(service):
    content = _make_content("match-101", "足球 比赛 分析 提供 胜负 预测")

    result = await service.analyze_content(content)

    assert isinstance(result, AnalysisResult)
    assert result.content_id == content.id
    assert result.analysis_type == "content_analysis"
    assert set(result.result.keys()) >= {
        "sentiment",
        "keywords",
        "category",
        "quality_score",
        "language",
        "word_count",
    }
    assert result.result["category"] in {"足球预测", "足球新闻", "一般内容"}
    assert 0.0 <= result.result["quality_score"] <= 1.0


@pytest.mark.asyncio
async def test_batch_analyze_handles_multiple_items(service):
    contents = [
        _make_content("batch-1", "足球 比赛 预测"),
        _make_content("batch-2", "球队 赛程 分析"),
    ]

    results = await service.batch_analyze(contents)

    assert len(results) == len(contents)
    assert {item.content_id for item in results} == {c.id for c in contents}


def test_analyze_text_structure():
    svc = ContentAnalysisService()

    text = os.getenv("TEST_CONTENT_ANALYSIS_SERVICE_TEXT_83")
    analysis = svc.analyze_text(text)

    assert analysis["word_count"] == len(text.split())
    assert analysis["character_count"] == len(text)
    assert analysis["language"] == "auto-detected"
    assert analysis["keywords"][:2] == ["football", "analytics"]
