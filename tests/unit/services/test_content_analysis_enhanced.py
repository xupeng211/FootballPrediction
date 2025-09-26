"""
Enhanced test file for content_analysis.py service module
Provides comprehensive coverage for content analysis functionality and async operations
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
from typing import List, Dict, Any

# Import from src directory
from src.services.content_analysis import (
    ContentAnalysisService,
    ContentType,
    AnalysisResult,
    ContentAnalysisError,
    AnalysisConfig,
    AnalysisPriority
)
from src.services.base import BaseService


class TestContentType:
    """Test ContentType enum values and behavior"""

    def test_content_type_values(self):
        """Test ContentType enum has expected values"""
        assert ContentType.TEXT == "text"
        assert ContentType.HTML == "html"
        assert ContentType.JSON == "json"
        assert ContentType.XML == "xml"
        assert ContentType.MARKDOWN == "markdown"

    def test_content_type_from_string(self):
        """Test creating ContentType from string values"""
        # Test existing values
        assert ContentType("text") == ContentType.TEXT
        assert ContentType("html") == ContentType.HTML
        assert ContentType("json") == ContentType.JSON

        # Test invalid values
        with pytest.raises(ValueError):
            ContentType("invalid")


class TestAnalysisConfig:
    """Test AnalysisConfig dataclass and properties"""

    def test_analysis_config_creation(self):
        """Test AnalysisConfig creation with default values"""
        config = AnalysisConfig()

        assert config.max_length == 10000
        assert config.enable_sentiment_analysis is True
        assert config.enable_entity_extraction is True
        assert config.enable_keyword_extraction is True
        assert config.min_confidence == 0.7
        assert config.timeout == 30

    def test_analysis_config_custom_values(self):
        """Test AnalysisConfig creation with custom values"""
        config = AnalysisConfig(
            max_length=5000,
            enable_sentiment_analysis=False,
            enable_entity_extraction=True,
            enable_keyword_extraction=False,
            min_confidence=0.8,
            timeout=60
        )

        assert config.max_length == 5000
        assert config.enable_sentiment_analysis is False
        assert config.enable_entity_extraction is True
        assert config.enable_keyword_extraction is False
        assert config.min_confidence == 0.8
        assert config.timeout == 60

    def test_analysis_config_validation(self):
        """Test AnalysisConfig parameter validation"""
        # Test invalid max_length
        with pytest.raises(ValueError):
            AnalysisConfig(max_length=0)

        with pytest.raises(ValueError):
            AnalysisConfig(max_length=-100)

        # Test invalid min_confidence
        with pytest.raises(ValueError):
            AnalysisConfig(min_confidence=1.5)

        with pytest.raises(ValueError):
            AnalysisConfig(min_confidence=-0.1)

        # Test invalid timeout
        with pytest.raises(ValueError):
            AnalysisConfig(timeout=0)


class TestAnalysisResult:
    """Test AnalysisResult dataclass and methods"""

    def test_analysis_result_creation(self):
        """Test AnalysisResult creation with required fields"""
        result = AnalysisResult(
            content_id="test_id",
            content_type=ContentType.TEXT,
            score=0.85,
            sentiment="positive",
            entities=["team", "player"],
            keywords=["football", "match"]
        )

        assert result.content_id == "test_id"
        assert result.content_type == ContentType.TEXT
        assert result.score == 0.85
        assert result.sentiment == "positive"
        assert result.entities == ["team", "player"]
        assert result.keywords == ["football", "match"]
        assert result.confidence == 0.85  # Default score
        assert result.processing_time > 0
        assert result.error is None

    def test_analysis_result_full_creation(self):
        """Test AnalysisResult creation with all fields"""
        result = AnalysisResult(
            content_id="test_id",
            content_type=ContentType.TEXT,
            score=0.85,
            sentiment="positive",
            entities=["team", "player"],
            keywords=["football", "match"],
            confidence=0.9,
            processing_time=1.5,
            categories=["sports", "football"],
            metadata={"source": "api", "language": "en"}
        )

        assert result.content_id == "test_id"
        assert result.content_type == ContentType.TEXT
        assert result.score == 0.85
        assert result.sentiment == "positive"
        assert result.entities == ["team", "player"]
        assert result.keywords == ["football", "match"]
        assert result.confidence == 0.9
        assert result.processing_time == 1.5
        assert result.categories == ["sports", "football"]
        assert result.metadata == {"source": "api", "language": "en"}

    def test_analysis_result_to_dict(self):
        """Test AnalysisResult to_dict method"""
        result = AnalysisResult(
            content_id="test_id",
            content_type=ContentType.TEXT,
            score=0.85,
            sentiment="positive",
            entities=["team", "player"],
            keywords=["football", "match"],
            categories=["sports"]
        )

        result_dict = result.to_dict()

        assert result_dict["content_id"] == "test_id"
        assert result_dict["content_type"] == "text"
        assert result_dict["score"] == 0.85
        assert result_dict["sentiment"] == "positive"
        assert result_dict["entities"] == ["team", "player"]
        assert result_dict["keywords"] == ["football", "match"]
        assert result_dict["categories"] == ["sports"]
        assert "confidence" in result_dict
        assert "processing_time" in result_dict

    def test_analysis_result_from_dict(self):
        """Test AnalysisResult from_dict class method"""
        result_dict = {
            "content_id": "test_id",
            "content_type": "text",
            "score": 0.85,
            "sentiment": "positive",
            "entities": ["team", "player"],
            "keywords": ["football", "match"],
            "confidence": 0.9,
            "processing_time": 1.5,
            "categories": ["sports"]
        }

        result = AnalysisResult.from_dict(result_dict)

        assert result.content_id == "test_id"
        assert result.content_type == ContentType.TEXT
        assert result.score == 0.85
        assert result.sentiment == "positive"
        assert result.entities == ["team", "player"]
        assert result.keywords == ["football", "match"]
        assert result.confidence == 0.9
        assert result.processing_time == 1.5
        assert result.categories == ["sports"]

    def test_analysis_result_from_dict_missing_fields(self):
        """Test AnalysisResult from_dict with missing required fields"""
        result_dict = {
            "content_id": "test_id",
            "content_type": "text"
            # Missing required fields
        }

        with pytest.raises(KeyError):
            AnalysisResult.from_dict(result_dict)

    def test_analysis_result_to_json(self):
        """Test AnalysisResult to_json method"""
        result = AnalysisResult(
            content_id="test_id",
            content_type=ContentType.TEXT,
            score=0.85,
            sentiment="positive",
            entities=["team", "player"],
            keywords=["football", "match"]
        )

        json_str = result.to_json()
        parsed = json.loads(json_str)

        assert parsed["content_id"] == "test_id"
        assert parsed["content_type"] == "text"
        assert parsed["score"] == 0.85

    def test_analysis_result_from_json(self):
        """Test AnalysisResult from_json class method"""
        json_str = '{"content_id": "test_id", "content_type": "text", "score": 0.85, "sentiment": "positive", "entities": ["team"], "keywords": ["football"]}'

        result = AnalysisResult.from_json(json_str)

        assert result.content_id == "test_id"
        assert result.content_type == ContentType.TEXT
        assert result.score == 0.85
        assert result.sentiment == "positive"
        assert result.entities == ["team"]
        assert result.keywords == ["football"]


class TestContentAnalysisError:
    """Test ContentAnalysisError exception class"""

    def test_content_analysis_error_creation(self):
        """Test ContentAnalysisError creation"""
        error = ContentAnalysisError("Test error message")

        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_content_analysis_error_with_code(self):
        """Test ContentAnalysisError with error code"""
        error = ContentAnalysisError("Test error", code="ANALYSIS_FAILED")

        assert str(error) == "Test error"
        assert error.code == "ANALYSIS_FAILED"

    def test_content_analysis_error_inheritance(self):
        """Test ContentAnalysisError inherits from Exception"""
        error = ContentAnalysisError("Test error")

        assert isinstance(error, Exception)
        assert isinstance(error, ContentAnalysisError)


class TestContentAnalysisService:
    """Test ContentAnalysisService class methods and functionality"""

    @pytest.fixture
    def mock_database_manager(self):
        """Mock database manager for testing"""
        manager = Mock()
        manager.get_connection = AsyncMock()
        manager.close_connection = AsyncMock()
        return manager

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        config = Mock()
        config.content_analysis = Mock()
        config.content_analysis.max_concurrent_analyses = 5
        config.content_analysis.default_timeout = 30
        config.content_analysis.cache_ttl = 300
        return config

    @pytest.fixture
    def content_analysis_service(self, mock_database_manager, mock_config):
        """Create ContentAnalysisService instance for testing"""
        with patch('src.services.base.DatabaseManager', return_value=mock_database_manager), \
             patch('src.services.base.load_config', return_value=mock_config):
            service = ContentAnalysisService()
            return service

    def test_content_analysis_service_inheritance(self):
        """Test ContentAnalysisService inherits from BaseService"""
        assert issubclass(ContentAnalysisService, BaseService)

    def test_content_analysis_service_init(self, content_analysis_service):
        """Test ContentAnalysisService initialization"""
        assert content_analysis_service is not None
        assert hasattr(content_analysis_service, 'database_manager')
        assert hasattr(content_analysis_service, 'config')
        assert hasattr(content_analysis_service, 'logger')

    @pytest.mark.asyncio
    async def test_analyze_content_text(self, content_analysis_service):
        """Test analyze_content with text content"""
        content = "This is a test football match content"
        content_type = ContentType.TEXT

        # Mock the analysis methods
        content_analysis_service._extract_sentiment = AsyncMock(return_value="positive")
        content_analysis_service._extract_entities = AsyncMock(return_value=["football", "match"])
        content_analysis_service._extract_keywords = AsyncMock(return_value=["test", "content"])
        content_analysis_service._calculate_score = AsyncMock(return_value=0.85)

        result = await content_analysis_service.analyze_content(content, content_type)

        assert result.content_type == ContentType.TEXT
        assert result.sentiment == "positive"
        assert result.entities == ["football", "match"]
        assert result.keywords == ["test", "content"]
        assert result.score == 0.85
        assert result.content_id is not None

    @pytest.mark.asyncio
    async def test_analyze_content_json(self, content_analysis_service):
        """Test analyze_content with JSON content"""
        content = {"text": "Test content", "metadata": {"source": "api"}}
        content_type = ContentType.JSON

        # Mock the analysis methods
        content_analysis_service._extract_sentiment = AsyncMock(return_value="neutral")
        content_analysis_service._extract_entities = AsyncMock(return_value=["test"])
        content_analysis_service._extract_keywords = AsyncMock(return_value=["api"])
        content_analysis_service._calculate_score = AsyncMock(return_value=0.75)

        result = await content_analysis_service.analyze_content(content, content_type)

        assert result.content_type == ContentType.JSON
        assert result.sentiment == "neutral"
        assert result.entities == ["test"]
        assert result.keywords == ["api"]
        assert result.score == 0.75

    @pytest.mark.asyncio
    async def test_analyze_content_with_config(self, content_analysis_service):
        """Test analyze_content with custom configuration"""
        content = "Test content"
        content_type = ContentType.TEXT
        config = AnalysisConfig(
            max_length=1000,
            enable_sentiment_analysis=True,
            enable_entity_extraction=False,
            enable_keyword_extraction=True,
            min_confidence=0.8
        )

        # Mock the analysis methods
        content_analysis_service._extract_sentiment = AsyncMock(return_value="positive")
        content_analysis_service._extract_entities = AsyncMock(return_value=[])
        content_analysis_service._extract_keywords = AsyncMock(return_value=["test"])
        content_analysis_service._calculate_score = AsyncMock(return_value=0.9)

        result = await content_analysis_service.analyze_content(content, content_type, config)

        assert result.score == 0.9
        assert result.entities == []  # Entity extraction disabled

    @pytest.mark.asyncio
    async def test_analyze_content_empty_content(self, content_analysis_service):
        """Test analyze_content with empty content"""
        content = ""
        content_type = ContentType.TEXT

        with pytest.raises(ContentAnalysisError) as exc_info:
            await content_analysis_service.analyze_content(content, content_type)

        assert "Content cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_analyze_content_too_long(self, content_analysis_service):
        """Test analyze_content with content exceeding max length"""
        content = "x" * 20000  # Very long content
        content_type = ContentType.TEXT
        config = AnalysisConfig(max_length=1000)

        with pytest.raises(ContentAnalysisError) as exc_info:
            await content_analysis_service.analyze_content(content, content_type, config)

        assert "Content exceeds maximum length" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_analyze_content_analysis_error(self, content_analysis_service):
        """Test analyze_content when analysis fails"""
        content = "Test content"
        content_type = ContentType.TEXT

        # Mock analysis method to raise an exception
        content_analysis_service._extract_sentiment = AsyncMock(side_effect=Exception("Analysis failed"))

        with pytest.raises(ContentAnalysisError) as exc_info:
            await content_analysis_service.analyze_content(content, content_type)

        assert "Content analysis failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_analyze_batch_content(self, content_analysis_service):
        """Test analyze_batch_content with multiple content items"""
        content_items = [
            ("Content 1", ContentType.TEXT),
            ("Content 2", ContentType.TEXT),
            ("Content 3", ContentType.TEXT)
        ]

        # Mock the individual analysis method
        mock_result1 = AnalysisResult(
            content_id="id1",
            content_type=ContentType.TEXT,
            score=0.8,
            sentiment="positive",
            entities=["content"],
            keywords=["test"]
        )
        mock_result2 = AnalysisResult(
            content_id="id2",
            content_type=ContentType.TEXT,
            score=0.7,
            sentiment="neutral",
            entities=["content"],
            keywords=["test"]
        )
        mock_result3 = AnalysisResult(
            content_id="id3",
            content_type=ContentType.TEXT,
            score=0.9,
            sentiment="positive",
            entities=["content"],
            keywords=["test"]
        )

        with patch.object(content_analysis_service, 'analyze_content', side_effect=[mock_result1, mock_result2, mock_result3]):
            results = await content_analysis_service.analyze_batch_content(content_items)

            assert len(results) == 3
            assert results[0].content_id == "id1"
            assert results[1].content_id == "id2"
            assert results[2].content_id == "id3"

    @pytest.mark.asyncio
    async def test_analyze_batch_content_empty_list(self, content_analysis_service):
        """Test analyze_batch_content with empty content list"""
        content_items = []

        results = await content_analysis_service.analyze_batch_content(content_items)

        assert results == []

    @pytest.mark.asyncio
    async def test_analyze_batch_content_with_config(self, content_analysis_service):
        """Test analyze_batch_content with custom configuration"""
        content_items = [
            ("Content 1", ContentType.TEXT),
            ("Content 2", ContentType.TEXT)
        ]
        config = AnalysisConfig(max_length=1000)

        # Mock the individual analysis method
        mock_result = AnalysisResult(
            content_id="id1",
            content_type=ContentType.TEXT,
            score=0.8,
            sentiment="positive",
            entities=["content"],
            keywords=["test"]
        )

        with patch.object(content_analysis_service, 'analyze_content', return_value=mock_result) as mock_analyze:
            await content_analysis_service.analyze_batch_content(content_items, config)

            # Verify analyze_content was called with config
            mock_analyze.assert_called_with("Content 1", ContentType.TEXT, config)

    @pytest.mark.asyncio
    async def test_analyze_batch_content_partial_failure(self, content_analysis_service):
        """Test analyze_batch_content with partial failures"""
        content_items = [
            ("Content 1", ContentType.TEXT),
            ("Content 2", ContentType.TEXT),
            ("Content 3", ContentType.TEXT)
        ]

        # Mock individual analysis to fail for one item
        mock_result1 = AnalysisResult(
            content_id="id1",
            content_type=ContentType.TEXT,
            score=0.8,
            sentiment="positive",
            entities=["content"],
            keywords=["test"]
        )
        mock_result3 = AnalysisResult(
            content_id="id3",
            content_type=ContentType.TEXT,
            score=0.9,
            sentiment="positive",
            entities=["content"],
            keywords=["test"]
        )

        with patch.object(content_analysis_service, 'analyze_content', side_effect=[mock_result1, ContentAnalysisError("Failed"), mock_result3]):
            results = await content_analysis_service.analyze_batch_content(content_items)

            # Should return 2 successful results
            assert len(results) == 2
            assert results[0].content_id == "id1"
            assert results[1].content_id == "id3"

    @pytest.mark.asyncio
    async def test_extract_sentiment(self, content_analysis_service):
        """Test _extract_sentiment method"""
        content = "This is a great football match!"

        # Mock external sentiment analysis service
        with patch('src.services.content_analysis.sentiment_analysis', return_value={"score": 0.8, "label": "positive"}) as mock_sentiment:
            result = await content_analysis_service._extract_sentiment(content)

            assert result == "positive"
            mock_sentiment.assert_called_once_with(content)

    @pytest.mark.asyncio
    async def test_extract_sentiment_error(self, content_analysis_service):
        """Test _extract_sentiment method error handling"""
        content = "Test content"

        # Mock external service to raise an exception
        with patch('src.services.content_analysis.sentiment_analysis', side_effect=Exception("Service unavailable")):
            result = await content_analysis_service._extract_sentiment(content)

            assert result == "neutral"  # Default fallback

    @pytest.mark.asyncio
    async def test_extract_entities(self, content_analysis_service):
        """Test _extract_entities method"""
        content = "The football match between Manchester United and Liverpool"

        # Mock external entity extraction service
        mock_entities = ["Manchester United", "Liverpool", "football match"]
        with patch('src.services.content_analysis.entity_extraction', return_value=mock_entities) as mock_extract:
            result = await content_analysis_service._extract_entities(content)

            assert result == mock_entities
            mock_extract.assert_called_once_with(content)

    @pytest.mark.asyncio
    async def test_extract_entities_empty(self, content_analysis_service):
        """Test _extract_entities method with no entities"""
        content = "This is a simple text"

        # Mock external service to return empty list
        with patch('src.services.content_analysis.entity_extraction', return_value=[]):
            result = await content_analysis_service._extract_entities(content)

            assert result == []

    @pytest.mark.asyncio
    async def test_extract_keywords(self, content_analysis_service):
        """Test _extract_keywords method"""
        content = "Football match analysis with detailed statistics"

        # Mock external keyword extraction service
        mock_keywords = ["football", "match", "analysis", "statistics"]
        with patch('src.services.content_analysis.keyword_extraction', return_value=mock_keywords) as mock_extract:
            result = await content_analysis_service._extract_keywords(content)

            assert result == mock_keywords
            mock_extract.assert_called_once_with(content)

    @pytest.mark.asyncio
    async def test_extract_keywords_limit(self, content_analysis_service):
        """Test _extract_keywords method with keyword limit"""
        content = "Long content with many keywords"

        # Mock external service to return many keywords
        all_keywords = ["kw1", "kw2", "kw3", "kw4", "kw5", "kw6", "kw7", "kw8", "kw9", "kw10"]
        with patch('src.services.content_analysis.keyword_extraction', return_value=all_keywords):
            result = await content_analysis_service._extract_keywords(content, max_keywords=5)

            # Should be limited to 5 keywords
            assert len(result) == 5
            assert result == all_keywords[:5]

    @pytest.mark.asyncio
    async def test_calculate_score(self, content_analysis_service):
        """Test _calculate_score method"""
        sentiment = "positive"
        entities = ["team", "player"]
        keywords = ["football", "match"]

        result = await content_analysis_service._calculate_score(sentiment, entities, keywords)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_score_weights(self, content_analysis_service):
        """Test _calculate_score method with different weights"""
        # Test with strong positive sentiment
        score1 = await content_analysis_service._calculate_score("positive", ["team", "player"], ["football", "match"])

        # Test with neutral sentiment
        score2 = await content_analysis_service._calculate_score("neutral", ["team"], ["football"])

        # Test with negative sentiment
        score3 = await content_analysis_service._calculate_score("negative", [], ["football"])

        # Positive should generally score higher
        assert score1 > score3

    @pytest.mark.asyncio
    async def test_validate_content_length(self, content_analysis_service):
        """Test _validate_content_length method"""
        # Test valid content
        content = "Test content"
        max_length = 100

        # Should not raise exception
        await content_analysis_service._validate_content_length(content, max_length)

        # Test empty content
        with pytest.raises(ContentAnalysisError):
            await content_analysis_service._validate_content_length("", max_length)

        # Test content too long
        long_content = "x" * 200
        with pytest.raises(ContentAnalysisError):
            await content_analysis_service._validate_content_length(long_content, max_length)

    @pytest.mark.asyncio
    async def test_validate_content_type(self, content_analysis_service):
        """Test _validate_content_type method"""
        # Test valid content types
        valid_contents = [
            ("text", ContentType.TEXT),
            ('{"key": "value"}', ContentType.JSON),
            ("<html>content</html>", ContentType.HTML)
        ]

        for content, content_type in valid_contents:
            # Should not raise exception
            await content_analysis_service._validate_content_type(content, content_type)

        # Test invalid JSON
        with pytest.raises(ContentAnalysisError):
            await content_analysis_service._validate_content_type("invalid json", ContentType.JSON)

        # Test invalid HTML
        with pytest.raises(ContentAnalysisError):
            await content_analysis_service._validate_content_type("invalid html", ContentType.HTML)

    @pytest.mark.asyncio
    async def test_get_analysis_stats(self, content_analysis_service):
        """Test get_analysis_stats method"""
        # Mock database query
        mock_connection = AsyncMock()
        mock_connection.fetch.return_value = [
            {"content_type": "text", "count": 100, "avg_score": 0.75},
            {"content_type": "json", "count": 50, "avg_score": 0.80}
        ]

        content_analysis_service.database_manager.get_connection.return_value = mock_connection

        stats = await content_analysis_service.get_analysis_stats()

        assert "total_analyses" in stats
        assert "by_content_type" in stats
        assert "average_score" in stats
        assert stats["total_analyses"] == 150
        assert len(stats["by_content_type"]) == 2
        assert stats["average_score"] == 0.77  # Weighted average

    @pytest.mark.asyncio
    async def test_get_analysis_stats_error(self, content_analysis_service):
        """Test get_analysis_stats method error handling"""
        # Mock database connection to raise an exception
        content_analysis_service.database_manager.get_connection.side_effect = Exception("Database error")

        stats = await content_analysis_service.get_analysis_stats()

        assert stats == {"error": "Failed to retrieve analysis stats"}

    @pytest.mark.asyncio
    async def test_cache_analysis_result(self, content_analysis_service):
        """Test _cache_analysis_result method"""
        result = AnalysisResult(
            content_id="test_id",
            content_type=ContentType.TEXT,
            score=0.85,
            sentiment="positive",
            entities=["team"],
            keywords=["football"]
        )

        # Mock cache service
        with patch('src.services.content_analysis.cache_service') as mock_cache:
            await content_analysis_service._cache_analysis_result(result)

            mock_cache.set.assert_called_once()
            call_args = mock_cache.set.call_args
            assert "analysis:test_id" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_cached_analysis(self, content_analysis_service):
        """Test _get_cached_analysis method"""
        content_id = "test_id"

        # Mock cache hit
        cached_data = {
            "content_id": "test_id",
            "content_type": "text",
            "score": 0.85,
            "sentiment": "positive"
        }

        with patch('src.services.content_analysis.cache_service') as mock_cache:
            mock_cache.get.return_value = cached_data

            result = await content_analysis_service._get_cached_analysis(content_id)

            assert result is not None
            assert result.content_id == "test_id"
            mock_cache.get.assert_called_once_with(f"analysis:{content_id}")

    @pytest.mark.asyncio
    async def test_get_cached_analysis_miss(self, content_analysis_service):
        """Test _get_cached_analysis method with cache miss"""
        content_id = "test_id"

        # Mock cache miss
        with patch('src.services.content_analysis.cache_service') as mock_cache:
            mock_cache.get.return_value = None

            result = await content_analysis_service._get_cached_analysis(content_id)

            assert result is None
            mock_cache.get.assert_called_once_with(f"analysis:{content_id}")

    @pytest.mark.asyncio
    async def test_log_analysis(self, content_analysis_service):
        """Test _log_analysis method"""
        result = AnalysisResult(
            content_id="test_id",
            content_type=ContentType.TEXT,
            score=0.85,
            sentiment="positive",
            entities=["team"],
            keywords=["football"]
        )

        # Mock database connection
        mock_connection = AsyncMock()
        content_analysis_service.database_manager.get_connection.return_value = mock_connection

        await content_analysis_service._log_analysis(result)

        mock_connection.execute.assert_called_once()
        call_args = mock_connection.execute.call_args[0][0]
        assert "INSERT INTO content_analysis_logs" in call_args

    @pytest.mark.asyncio
    async def test_log_analysis_error(self, content_analysis_service):
        """Test _log_analysis method error handling"""
        result = AnalysisResult(
            content_id="test_id",
            content_type=ContentType.TEXT,
            score=0.85,
            sentiment="positive",
            entities=["team"],
            keywords=["football"]
        )

        # Mock database connection to raise an exception
        mock_connection = AsyncMock()
        mock_connection.execute.side_effect = Exception("Database error")
        content_analysis_service.database_manager.get_connection.return_value = mock_connection

        # Should not raise exception, just log error
        await content_analysis_service._log_analysis(result)

    @pytest.mark.asyncio
    async def test_health_check(self, content_analysis_service):
        """Test health_check method"""
        # Mock database health check
        content_analysis_service.database_manager.health_check = AsyncMock(return_value=True)

        # Mock external service health check
        with patch('src.services.content_analysis.external_service_health', return_value=True):
            health = await content_analysis_service.health_check()

            assert health["status"] == "healthy"
            assert health["database"] is True
            assert health["external_services"] is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, content_analysis_service):
        """Test health_check method when unhealthy"""
        # Mock database health check to fail
        content_analysis_service.database_manager.health_check = AsyncMock(return_value=False)

        health = await content_analysis_service.health_check()

        assert health["status"] == "unhealthy"
        assert health["database"] is False

    def test_generate_content_id(self, content_analysis_service):
        """Test _generate_content_id method"""
        content = "Test content"
        content_type = ContentType.TEXT

        content_id = content_analysis_service._generate_content_id(content, content_type)

        assert isinstance(content_id, str)
        assert len(content_id) > 0
        assert content_id.startswith("analysis_")

    def test_generate_content_id_uniqueness(self, content_analysis_service):
        """Test _generate_content_id method generates unique IDs"""
        content = "Test content"
        content_type = ContentType.TEXT

        id1 = content_analysis_service._generate_content_id(content, content_type)
        id2 = content_analysis_service._generate_content_id(content, content_type)

        # Should be different due to timestamp
        assert id1 != id2


class TestContentAnalysisIntegration:
    """Integration tests for content analysis service"""

    @pytest.mark.asyncio
    async def test_full_analysis_pipeline(self):
        """Test complete content analysis pipeline"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db.health_check = AsyncMock(return_value=True)
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.content_analysis = Mock()
            mock_conf.content_analysis.max_concurrent_analyses = 5
            mock_conf.content_analysis.default_timeout = 30
            mock_config.return_value = mock_conf

            # Create service
            service = ContentAnalysisService()

            # Mock external services
            with patch.object(service, '_extract_sentiment', return_value="positive"), \
                 patch.object(service, '_extract_entities', return_value=["football", "match"]), \
                 patch.object(service, '_extract_keywords', return_value=["test", "content"]), \
                 patch.object(service, '_calculate_score', return_value=0.85), \
                 patch.object(service, '_cache_analysis_result'), \
                 patch.object(service, '_log_analysis'):

                content = "Test football content"
                result = await service.analyze_content(content, ContentType.TEXT)

                # Verify complete pipeline
                assert result.content_type == ContentType.TEXT
                assert result.sentiment == "positive"
                assert result.entities == ["football", "match"]
                assert result.keywords == ["test", "content"]
                assert result.score == 0.85
                assert result.content_id is not None

    @pytest.mark.asyncio
    async def test_concurrent_analyses(self):
        """Test concurrent content analysis"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db.health_check = AsyncMock(return_value=True)
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.content_analysis = Mock()
            mock_conf.content_analysis.max_concurrent_analyses = 3
            mock_conf.content_analysis.default_timeout = 30
            mock_config.return_value = mock_conf

            # Create service
            service = ContentAnalysisService()

            # Mock analysis methods
            mock_result = AnalysisResult(
                content_id="test_id",
                content_type=ContentType.TEXT,
                score=0.85,
                sentiment="positive",
                entities=["test"],
                keywords=["content"]
            )

            with patch.object(service, 'analyze_content', return_value=mock_result):
                # Create multiple concurrent tasks
                tasks = []
                for i in range(5):
                    task = service.analyze_content(f"Content {i}", ContentType.TEXT)
                    tasks.append(task)

                # Run all tasks concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Verify all results
                assert len(results) == 5
                for result in results:
                    assert isinstance(result, AnalysisResult)
                    assert result.score == 0.85


class TestContentAnalysisErrorHandling:
    """Error handling tests for content analysis service"""

    @pytest.mark.asyncio
    async def test_external_service_timeout(self):
        """Test handling of external service timeouts"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.content_analysis = Mock()
            mock_conf.content_analysis.default_timeout = 1  # Very short timeout
            mock_config.return_value = mock_conf

            # Create service
            service = ContentAnalysisService()

            # Mock external service to timeout
            async def slow_sentiment_analysis(content):
                await asyncio.sleep(2)  # Sleep longer than timeout
                return "positive"

            with patch.object(service, '_extract_sentiment', side_effect=slow_sentiment_analysis):
                with pytest.raises(ContentAnalysisError) as exc_info:
                    await service.analyze_content("Test content", ContentType.TEXT)

                assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_memory_limit_handling(self):
        """Test handling of memory limit exceeded"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.content_analysis = Mock()
            mock_conf.content_analysis.max_content_size = 1000  # Small limit
            mock_config.return_value = mock_conf

            # Create service
            service = ContentAnalysisService()

            # Test with large content
            large_content = "x" * 2000

            with pytest.raises(ContentAnalysisError) as exc_info:
                await service.analyze_content(large_content, ContentType.TEXT)

            assert "memory" in str(exc_info.value).lower() or "size" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting for content analysis"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.content_analysis = Mock()
            mock_conf.content_analysis.rate_limit_per_minute = 2  # Very low limit
            mock_config.return_value = mock_conf

            # Create service
            service = ContentAnalysisService()

            # Mock successful analysis
            mock_result = AnalysisResult(
                content_id="test_id",
                content_type=ContentType.TEXT,
                score=0.85,
                sentiment="positive",
                entities=["test"],
                keywords=["content"]
            )

            with patch.object(service, '_extract_sentiment', return_value="positive"), \
                 patch.object(service, '_extract_entities', return_value=["test"]), \
                 patch.object(service, '_extract_keywords', return_value=["content"]), \
                 patch.object(service, '_calculate_score', return_value=0.85):

                # First two requests should succeed
                result1 = await service.analyze_content("Content 1", ContentType.TEXT)
                result2 = await service.analyze_content("Content 2", ContentType.TEXT)

                assert result1 is not None
                assert result2 is not None

                # Third request should be rate limited
                with pytest.raises(ContentAnalysisError) as exc_info:
                    await service.analyze_content("Content 3", ContentType.TEXT)

                assert "rate limit" in str(exc_info.value).lower()


class TestContentAnalysisPerformance:
    """Performance tests for content analysis service"""

    @pytest.mark.asyncio
    async def test_analysis_performance(self):
        """Test content analysis performance metrics"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.content_analysis = Mock()
            mock_conf.content_analysis.default_timeout = 30
            mock_config.return_value = mock_conf

            # Create service
            service = ContentAnalysisService()

            # Mock fast analysis methods
            with patch.object(service, '_extract_sentiment', return_value="positive"), \
                 patch.object(service, '_extract_entities', return_value=["test"]), \
                 patch.object(service, '_extract_keywords', return_value=["content"]), \
                 patch.object(service, '_calculate_score', return_value=0.85):

                # Measure performance
                start_time = asyncio.get_event_loop().time()

                result = await service.analyze_content("Test content", ContentType.TEXT)

                end_time = asyncio.get_event_loop().time()
                processing_time = end_time - start_time

                # Verify result and performance
                assert result is not None
                assert result.processing_time <= processing_time + 0.1  # Allow some tolerance
                assert processing_time < 1.0  # Should complete within 1 second

    @pytest.mark.asyncio
    async def test_batch_analysis_performance(self):
        """Test batch content analysis performance"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.content_analysis = Mock()
            mock_conf.content_analysis.max_concurrent_analyses = 10
            mock_config.return_value = mock_conf

            # Create service
            service = ContentAnalysisService()

            # Create batch content
            batch_content = [(f"Content {i}", ContentType.TEXT) for i in range(10)]

            # Mock fast analysis
            mock_result = AnalysisResult(
                content_id="test_id",
                content_type=ContentType.TEXT,
                score=0.85,
                sentiment="positive",
                entities=["test"],
                keywords=["content"]
            )

            with patch.object(service, 'analyze_content', return_value=mock_result):
                # Measure batch performance
                start_time = asyncio.get_event_loop().time()

                results = await service.analyze_batch_content(batch_content)

                end_time = asyncio.get_event_loop().time()
                processing_time = end_time - start_time

                # Verify results and performance
                assert len(results) == 10
                assert processing_time < 2.0  # Should complete within 2 seconds

    @pytest.mark.asyncio
    async def test_memory_usage_efficiency(self):
        """Test memory usage efficiency for large content analysis"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.content_analysis = Mock()
            mock_conf.content_analysis.max_content_size = 50000
            mock_config.return_value = mock_conf

            # Create service
            service = ContentAnalysisService()

            # Create large content
            large_content = "This is a test sentence. " * 1000  # ~25,000 characters

            # Mock analysis methods
            with patch.object(service, '_extract_sentiment', return_value="neutral"), \
                 patch.object(service, '_extract_entities', return_value=["test"]), \
                 patch.object(service, '_extract_keywords', return_value=["sentence"]), \
                 patch.object(service, '_calculate_score', return_value=0.5):

                # Analyze large content
                result = await service.analyze_content(large_content, ContentType.TEXT)

                # Verify analysis completed successfully
                assert result is not None
                assert result.content_type == ContentType.TEXT
                assert result.processing_time > 0


# Test class for edge cases and boundary conditions
class TestContentAnalysisEdgeCases:
    """Edge case tests for content analysis service"""

    @pytest.mark.asyncio
    async def test_special_characters_content(self):
        """Test content analysis with special characters"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.content_analysis = Mock()
            mock_config.return_value = mock_conf

            # Create service
            service = ContentAnalysisService()

            # Test content with special characters
            special_content = "Football ⚽ match with émojis 🎉 and spëcial chäracters!"

            with patch.object(service, '_extract_sentiment', return_value="positive"), \
                 patch.object(service, '_extract_entities', return_value=["football", "match"]), \
                 patch.object(service, '_extract_keywords', return_value=["emojis", "special"]), \
                 patch.object(service, '_calculate_score', return_value=0.8):

                result = await service.analyze_content(special_content, ContentType.TEXT)

                assert result is not None
                assert result.sentiment == "positive"

    @pytest.mark.asyncio
    async def test_multilingual_content(self):
        """Test content analysis with multilingual content"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.content_analysis = Mock()
            mock_config.return_value = mock_conf

            # Create service
            service = ContentAnalysisService()

            # Test content in different languages
            multilingual_content = "Football match Fußball partido フットボール 足球"

            with patch.object(service, '_extract_sentiment', return_value="positive"), \
                 patch.object(service, '_extract_entities', return_value=["football"]), \
                 patch.object(service, '_extract_keywords', return_value=["match"]), \
                 patch.object(service, '_calculate_score', return_value=0.7):

                result = await service.analyze_content(multilingual_content, ContentType.TEXT)

                assert result is not None
                assert result.entities == ["football"]

    @pytest.mark.asyncio
    async def test_extreme_scores(self):
        """Test content analysis with extreme scores"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.content_analysis = Mock()
            mock_config.return_value = mock_conf

            # Create service
            service = ContentAnalysisService()

            # Test with very positive content
            positive_content = "Absolutely amazing fantastic incredible football match!"

            with patch.object(service, '_extract_sentiment', return_value="positive"), \
                 patch.object(service, '_extract_entities', return_value=["football", "match"]), \
                 patch.object(service, '_extract_keywords', return_value=["amazing", "fantastic"]), \
                 patch.object(service, '_calculate_score', return_value=0.99):

                result = await service.analyze_content(positive_content, ContentType.TEXT)

                assert result is not None
                assert result.score >= 0.95

            # Test with very negative content
            negative_content = "Terrible horrible awful football match disaster!"

            with patch.object(service, '_extract_sentiment', return_value="negative"), \
                 patch.object(service, '_extract_entities', return_value=["football", "match"]), \
                 patch.object(service, '_extract_keywords', return_value=["terrible", "horrible"]), \
                 patch.object(service, '_calculate_score', return_value=0.01):

                result = await service.analyze_content(negative_content, ContentType.TEXT)

                assert result is not None
                assert result.score <= 0.05

    @pytest.mark.asyncio
    async def test_empty_analysis_results(self):
        """Test content analysis with empty results"""
        with patch('src.services.base.DatabaseManager') as mock_db_manager, \
             patch('src.services.base.load_config') as mock_config:

            # Setup mocks
            mock_db = Mock()
            mock_db.get_connection = AsyncMock()
            mock_db_manager.return_value = mock_db

            mock_conf = Mock()
            mock_conf.content_analysis = Mock()
            mock_config.return_value = mock_conf

            # Create service
            service = ContentAnalysisService()

            # Test content that yields no entities or keywords
            minimal_content = "x"

            with patch.object(service, '_extract_sentiment', return_value="neutral"), \
                 patch.object(service, '_extract_entities', return_value=[]), \
                 patch.object(service, '_extract_keywords', return_value=[]), \
                 patch.object(service, '_calculate_score', return_value=0.5):

                result = await service.analyze_content(minimal_content, ContentType.TEXT)

                assert result is not None
                assert result.entities == []
                assert result.keywords == []
                assert result.sentiment == "neutral"
                assert result.score == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])