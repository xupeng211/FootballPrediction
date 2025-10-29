"""
内容分析服务测试
Tests for Content Analysis Service
"""

from datetime import datetime

import pytest

from src.services.content_analysis import (
    AnalysisResult,
    Content,
    ContentAnalysisService,
    ContentType,
    UserProfile,
    UserRole,
)


@pytest.mark.unit
class TestContentAnalysisService:
    """内容分析服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return ContentAnalysisService()

    @pytest.fixture
    def sample_text_content(self):
        """示例文本内容"""
        return Content(
            content_id="test_001",
            content_type="text",
            _data={"text": "曼联今天在英超比赛中取得了胜利，这是一场非常精彩的比赛。"},
        )

    @pytest.fixture
    def sample_image_content(self):
        """示例图片内容"""
        return Content(
            content_id="test_002",
            content_type="image",
            _data={"url": "http://example.com/image.jpg", "size": "1024x768"},
        )

    @pytest.fixture
    def user_profile(self):
        """示例用户配置文件"""
        return UserProfile(
            user_id="user_123", preferences={"language": "zh", "category": "football"}
        )

    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """测试：服务初始化"""
        # Then
        assert service.name == "ContentAnalysisService"
        assert service._models_loaded is False
        assert service._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_success(self, service):
        """测试：成功初始化"""
        # When
        _result = await service.initialize()

        # Then
        assert _result is True
        assert service._initialized is True
        assert service._models_loaded is True

    @pytest.mark.asyncio
    async def test_initialize_failure(self, service):
        """测试：初始化失败"""
        # Given
        with patch.object(service, "_on_initialize", return_value=False):
            # When
            _result = await service.initialize()

            # Then
            assert _result is False
            assert service._initialized is False

    @pytest.mark.asyncio
    async def test_shutdown(self, service):
        """测试：关闭服务"""
        # Given
        await service.initialize()
        assert service._models_loaded is True

        # When
        await service.shutdown()

        # Then
        assert service._models_loaded is False

    @pytest.mark.asyncio
    async def test_get_service_info(self, service):
        """测试：获取服务信息"""
        # Given
        await service.initialize()

        # When
        info = await service._get_service_info()

        # Then
        assert info["name"] == "ContentAnalysisService"
        assert info["type"] == "ContentAnalysisService"
        assert info["description"] == "Content analysis service for football prediction system"
        assert info["version"] == "1.0.0"
        assert info["models_loaded"] is True

    @pytest.mark.asyncio
    async def test_analyze_text_content(self, service, sample_text_content):
        """测试：分析文本内容"""
        # Given
        await service.initialize()

        # When
        _result = await service.analyze_content(sample_text_content)

        # Then
        assert isinstance(result, AnalysisResult)
        assert _result.id == "analysis_test_001"
        assert _result.analysis_type == "content_analysis"
        assert _result.content_id == "test_001"
        assert _result.confidence == 0.85
        assert isinstance(result.timestamp, datetime)
        assert "sentiment" in result.result
        assert "keywords" in result.result
        assert "category" in result.result
        assert "quality_score" in result.result
        assert "language" in result.result
        assert "word_count" in result.result

    @pytest.mark.asyncio
    async def test_analyze_non_text_content(self, service, sample_image_content):
        """测试：分析非文本内容"""
        # Given
        await service.initialize()

        # When
        _result = await service.analyze_content(sample_image_content)

        # Then
        assert isinstance(result, AnalysisResult)
        assert _result._result["sentiment"] == "neutral"
        assert _result._result["category"] == "general"
        assert _result._result["quality_score"] == 0.5
        assert _result._result["language"] == "unknown"

    @pytest.mark.asyncio
    async def test_analyze_content_without_initialization(self, service, sample_text_content):
        """测试：未初始化时分析内容"""
        # When / Then
        with pytest.raises(RuntimeError, match="服务未初始化"):
            await service.analyze_content(sample_text_content)

    @pytest.mark.asyncio
    async def test_batch_analyze(self, service, sample_text_content, sample_image_content):
        """测试：批量分析内容"""
        # Given
        await service.initialize()
        contents = [sample_text_content, sample_image_content]

        # When
        results = await service.batch_analyze(contents)

        # Then
        assert len(results) == 2
        assert all(isinstance(r, AnalysisResult) for r in results)
        assert results[0].content_id == "test_001"
        assert results[1].content_id == "test_002"

    @pytest.mark.asyncio
    async def test_batch_analyze_empty_list(self, service):
        """测试：批量分析空列表"""
        # Given
        await service.initialize()

        # When
        results = await service.batch_analyze([])

        # Then
        assert results == []

    def test_categorize_football_content(self, service):
        """测试：足球内容分类"""
        # When
        category = service._categorize_content("曼联今天在英超比赛中进了两个球")

        # Then
        assert category == "足球新闻"

    def test_categorize_prediction_content(self, service):
        """测试：足球预测内容分类"""
        # Given - 需要同时包含足球关键词和预测关键词
        text = "曼联在英超比赛的预测，根据赔率分析曼联会赢"

        # When
        category = service._categorize_content(text)

        # Then
        # 同时包含足球关键词（曼联、英超）和预测关键词（预测、赔率）
        assert category == "足球预测"

    def test_categorize_general_content(self, service):
        """测试：一般内容分类"""
        # When
        category = service._categorize_content("今天天气很好，适合出门散步")

        # Then
        assert category == "一般内容"

    def test_calculate_quality_score_text(self, service):
        """测试：计算文本内容质量分数"""
        # Given
        content = Content(
            content_id="test",
            content_type="text",
            _data={"text": "这是一场关于足球比赛的详细分析，包含了多个关键因素。"},
        )

        # When
        score = service._calculate_quality_score(content)

        # Then
        assert 0.0 <= score <= 1.0
        assert score > 0.3  # 包含关键词应该有基础分数以上

    def test_calculate_quality_score_non_text(self, service, sample_image_content):
        """测试：计算非文本内容质量分数"""
        # When
        score = service._calculate_quality_score(sample_image_content)

        # Then
        assert score == 0.5

    def test_analyze_text_empty(self, service):
        """测试：分析空文本"""
        # When
        _result = service.analyze_text("")

        # Then
        assert "error" in result
        assert _result["error"] == "Empty text"

    def test_analyze_text_normal(self, service):
        """测试：分析普通文本"""
        # Given
        text = "曼联今天在英超比赛中取得了胜利"

        # When
        _result = service.analyze_text(text)

        # Then
        assert "word_count" in result
        assert "character_count" in result
        assert "sentiment" in result
        assert "keywords" in result
        assert "language" in result
        assert "entities" in result
        assert "summary" in result
        assert _result["word_count"] == len(text.split())
        assert _result["character_count"] == len(text)

    def test_extract_entities_teams(self, service):
        """测试：提取球队实体"""
        # Given
        text = "曼联对阵切尔西，巴塞罗那对战皇家马德里"

        # When
        entities = service.extract_entities(text)

        # Then
        assert len(entities) >= 3
        team_entities = [e for e in entities if e["type"] == "TEAM"]
        assert len(team_entities) >= 3
        assert all(e["confidence"] == 0.9 for e in team_entities)

    def test_extract_entities_persons(self, service):
        """测试：提取人物实体"""
        # Given
        text = "球员 C罗 在比赛中表现出色"

        # When
        entities = service.extract_entities(text)

        # Then
        person_entities = [e for e in entities if e["type"] == "PERSON"]
        assert len(person_entities) >= 1

    def test_classify_content_match_report(self, service):
        """测试：分类比赛报道内容"""
        # Given
        content = "比赛结束，比分为3:1，曼联在主场取得了胜利"

        # When
        _result = service.classify_content(content)

        # Then
        assert _result["category"] == "match_report"
        assert _result["confidence"] > 0
        assert "all_scores" in result

    def test_classify_content_transfer_news(self, service):
        """测试：分类转会新闻内容"""
        # Given
        content = "球员完成转会，签约新俱乐部"

        # When
        _result = service.classify_content(content)

        # Then
        assert _result["category"] == "transfer_news"
        assert _result["confidence"] > 0

    def test_classify_content_empty(self, service):
        """测试：分类空内容"""
        # When
        _result = service.classify_content("")

        # Then
        assert _result["category"] == "unknown"
        assert _result["confidence"] == 0.0

    def test_analyze_sentiment_positive(self, service):
        """测试：正面情感分析"""
        # Given
        text = "这是一场精彩的胜利，表现出色！"

        # When
        _result = service.analyze_sentiment(text)

        # Then
        assert "sentiment" in result
        assert "score" in result
        assert "positive_count" in result
        assert "negative_count" in result
        assert _result["positive_count"] > 0

    def test_analyze_sentiment_negative(self, service):
        """测试：负面情感分析"""
        # Given
        text = "糟糕的失败，令人失望"

        # When
        _result = service.analyze_sentiment(text)

        # Then
        assert _result["negative_count"] > 0
        assert _result["score"] < 0

    def test_analyze_sentiment_neutral(self, service):
        """测试：中性情感分析"""
        # Given
        text = "今天进行了比赛"

        # When
        _result = service.analyze_sentiment(text)

        # Then
        assert _result["sentiment"] == "neutral"
        assert _result["score"] == 0.0

    def test_analyze_sentiment_empty(self, service):
        """测试：空文本情感分析"""
        # When
        _result = service.analyze_sentiment("")

        # Then
        assert _result["sentiment"] == "neutral"
        assert _result["score"] == 0.0

    def test_generate_summary_short_text(self, service):
        """测试：生成短文本摘要"""
        # Given
        text = "这是一段短文本"

        # When
        summary = service.generate_summary(text, 100)

        # Then
        assert summary == text

    def test_generate_summary_long_text(self, service):
        """测试：生成长文本摘要"""
        # Given
        text = "这是一段很长的文本。包含了很多内容。需要进行摘要。超过了一百个字符的限制。" * 3

        # When
        summary = service.generate_summary(text, 50)

        # Then
        assert len(summary) <= 53  # 50 + "..."
        assert "..." in summary or summary.endswith("。")

    def test_generate_summary_empty(self, service):
        """测试：生成空文本摘要"""
        # When
        summary = service.generate_summary("", 100)

        # Then
        assert summary == ""

    def test_generate_summary_custom_max_length(self, service):
        """测试：自定义最大长度摘要"""
        # Given
        text = "这是一段测试文本，用于验证自定义长度功能。"

        # When
        summary = service.generate_summary(text, 20)

        # Then
        assert len(summary) <= 23  # 20 + "..."


class TestContentModel:
    """内容模型测试"""

    def test_content_creation(self):
        """测试：创建内容对象"""
        # Given & When
        content = Content(content_id="test_001", content_type="text", _data={"text": "测试内容"})

        # Then
        assert content.id == "test_001"
        assert content.content_type == "text"
        assert content._data["text"] == "测试内容"

    def test_user_profile_creation_default_preferences(self):
        """测试：创建用户配置文件（默认偏好）"""
        # Given & When
        profile = UserProfile(user_id="user_123")

        # Then
        assert profile.user_id == "user_123"
        assert profile.preferences == {}

    def test_user_profile_creation_with_preferences(self):
        """测试：创建用户配置文件（带偏好）"""
        # Given
        preferences = {"language": "zh", "category": "football"}

        # When
        profile = UserProfile(user_id="user_123", preferences=preferences)

        # Then
        assert profile.user_id == "user_123"
        assert profile.preferences == preferences

    def test_analysis_result_creation_default(self):
        """测试：创建分析结果（默认值）"""
        # Given & When
        _result = AnalysisResult()

        # Then
        assert _result.id == ""
        assert _result.analysis_type == ""
        assert _result._result == {}
        assert _result.confidence == 0.0
        assert isinstance(result.timestamp, datetime)
        assert _result.content_id == ""

    def test_analysis_result_creation_with_values(self):
        """测试：创建分析结果（带值）"""
        # Given
        timestamp = datetime.now()

        # When
        _result = AnalysisResult(
            id="analysis_001",
            analysis_type="sentiment",
            _result={"sentiment": "positive"},
            confidence=0.95,
            timestamp=timestamp,
            content_id="content_001",
        )

        # Then
        assert _result.id == "analysis_001"
        assert _result.analysis_type == "sentiment"
        assert _result._result["sentiment"] == "positive"
        assert _result.confidence == 0.95
        assert _result.timestamp == timestamp
        assert _result.content_id == "content_001"


class TestContentTypeEnum:
    """内容类型枚举测试"""

    def test_content_type_values(self):
        """测试：内容类型枚举值"""
        assert ContentType.TEXT.value == "text"
        assert ContentType.IMAGE.value == "image"
        assert ContentType.VIDEO.value == "video"
        assert ContentType.AUDIO.value == "audio"
        assert ContentType.DOCUMENT.value == "document"

    def test_user_role_values(self):
        """测试：用户角色枚举值"""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.USER.value == "user"
        assert UserRole.GUEST.value == "guest"
        assert UserRole.MODERATOR.value == "moderator"
