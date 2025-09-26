"""
Simple test file for content_analysis.py service module
Provides comprehensive coverage for the actual ContentAnalysisService implementation
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

# Import from src directory
from src.services.content_analysis import ContentAnalysisService
from src.models import AnalysisResult, Content
from src.services.base import BaseService


class TestContentAnalysisService:
    """Test ContentAnalysisService class methods and functionality"""

    @pytest.fixture
    def mock_content(self):
        """Create mock Content object for testing"""
        content = Mock(spec=Content)
        content.id = "test_content_123"
        content.text = "Test football content"
        content.metadata = {"source": "test"}
        return content

    @pytest.fixture
    def content_analysis_service(self):
        """Create ContentAnalysisService instance for testing"""
        with patch('src.services.base.BaseService.__init__') as mock_init:
            mock_init.return_value = None
            service = ContentAnalysisService()
            service.name = "ContentAnalysisService"
            service.logger = Mock()
            service._initialized = True
            return service

    def test_content_analysis_service_inheritance(self):
        """Test ContentAnalysisService inherits from BaseService"""
        assert issubclass(ContentAnalysisService, BaseService)

    def test_content_analysis_service_init(self):
        """Test ContentAnalysisService initialization"""
        with patch('src.services.base.BaseService.__init__') as mock_init:
            service = ContentAnalysisService()

            assert service is not None
            assert service._initialized is False
            mock_init.assert_called_once_with("ContentAnalysisService")

    @pytest.mark.asyncio
    async def test_initialize_success(self, content_analysis_service):
        """Test successful service initialization"""
        result = await content_analysis_service.initialize()

        assert result is True
        assert content_analysis_service._initialized is True
        content_analysis_service.logger.info.assert_called_with("正在初始化 ContentAnalysisService")

    @pytest.mark.asyncio
    async def test_shutdown(self, content_analysis_service):
        """Test service shutdown"""
        content_analysis_service._initialized = True

        await content_analysis_service.shutdown()

        assert content_analysis_service._initialized is False
        content_analysis_service.logger.info.assert_called_with("正在关闭 ContentAnalysisService")

    @pytest.mark.asyncio
    async def test_analyze_content_success(self, content_analysis_service, mock_content):
        """Test successful content analysis"""
        result = await content_analysis_service.analyze_content(mock_content)

        assert result is not None
        assert isinstance(result, AnalysisResult)
        assert result.id == "analysis_test_content_123"
        assert result.analysis_type == "content_analysis"
        assert result.confidence == 0.85
        assert result.content_id == "test_content_123"
        assert isinstance(result.timestamp, datetime)
        assert "sentiment" in result.result
        assert result.result["sentiment"] == "positive"
        assert "keywords" in result.result
        assert "category" in result.result
        assert result.result["category"] == "体育"

    @pytest.mark.asyncio
    async def test_analyze_content_not_initialized(self, content_analysis_service, mock_content):
        """Test content analysis when service not initialized"""
        content_analysis_service._initialized = False

        with pytest.raises(RuntimeError) as exc_info:
            await content_analysis_service.analyze_content(mock_content)

        assert "服务未初始化" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_analyze_content_logging(self, content_analysis_service, mock_content):
        """Test content analysis logging"""
        await content_analysis_service.analyze_content(mock_content)

        content_analysis_service.logger.info.assert_called_with("正在分析内容: test_content_123")

    @pytest.mark.asyncio
    async def test_batch_analyze_success(self, content_analysis_service):
        """Test successful batch content analysis"""
        # Create multiple mock contents
        contents = []
        for i in range(3):
            content = Mock(spec=Content)
            content.id = f"content_{i}"
            content.text = f"Test content {i}"
            contents.append(content)

        results = await content_analysis_service.batch_analyze(contents)

        assert len(results) == 3
        for i, result in enumerate(results):
            assert result is not None
            assert isinstance(result, AnalysisResult)
            assert result.id == f"analysis_content_{i}"
            assert result.content_id == f"content_{i}"

    @pytest.mark.asyncio
    async def test_batch_analyze_empty_list(self, content_analysis_service):
        """Test batch analysis with empty content list"""
        results = await content_analysis_service.batch_analyze([])

        assert results == []

    @pytest.mark.asyncio
    async def test_batch_analyze_partial_results(self, content_analysis_service):
        """Test batch analysis with some failed analyses"""
        # Create mock contents where one will fail
        contents = []
        for i in range(3):
            content = Mock(spec=Content)
            content.id = f"content_{i}"
            content.text = f"Test content {i}"
            contents.append(content)

        # Mock analyze_content to return None for one content
        original_analyze = content_analysis_service.analyze_content
        async def mock_analyze(content):
            if content.id == "content_1":
                return None
            return await original_analyze(content)

        with patch.object(content_analysis_service, 'analyze_content', side_effect=mock_analyze):
            results = await content_analysis_service.batch_analyze(contents)

            # Should return 2 results (one failed)
            assert len(results) == 2

    def test_analyze_text_success(self, content_analysis_service):
        """Test successful text analysis"""
        text = "This is a test football prediction analysis"
        result = content_analysis_service.analyze_text(text)

        assert result is not None
        assert isinstance(result, dict)
        assert "word_count" in result
        assert "character_count" in result
        assert "sentiment" in result
        assert "keywords" in result
        assert "language" in result

        assert result["word_count"] == 8
        assert result["character_count"] == len(text)
        assert result["sentiment"] == "neutral"
        assert result["language"] == "auto-detected"
        assert isinstance(result["keywords"], list)

    def test_analyze_text_empty(self, content_analysis_service):
        """Test text analysis with empty text"""
        result = content_analysis_service.analyze_text("")

        assert result is not None
        assert isinstance(result, dict)
        assert "error" in result
        assert result["error"] == "Empty text"

    def test_analyze_text_single_word(self, content_analysis_service):
        """Test text analysis with single word"""
        text = "football"
        result = content_analysis_service.analyze_text(text)

        assert result["word_count"] == 1
        assert result["character_count"] == 8
        assert result["keywords"] == ["football"]

    def test_analyze_text_long_text(self, content_analysis_service):
        """Test text analysis with long text"""
        text = "word " * 100  # 100 words
        result = content_analysis_service.analyze_text(text)

        assert result["word_count"] == 100
        assert len(result["keywords"]) == 5  # Should be limited to first 5 words

    def test_analyze_text_unicode(self, content_analysis_service):
        """Test text analysis with unicode characters"""
        text = "足球预测 ⚽ 分析"
        result = content_analysis_service.analyze_text(text)

        assert result is not None
        assert result["word_count"] == 4  # Unicode words
        assert result["character_count"] == len(text)

    def test_analyze_text_whitespace(self, content_analysis_service):
        """Test text analysis with whitespace"""
        text = "   multiple   spaces   between   words   "
        result = content_analysis_service.analyze_text(text)

        assert result["word_count"] == 4  # Should ignore extra spaces
        assert result["keywords"] == ["multiple", "spaces", "between", "words"]


class TestContentAnalysisServiceEdgeCases:
    """Edge case tests for ContentAnalysisService"""

    @pytest.mark.asyncio
    async def test_analyze_content_with_none(self, content_analysis_service):
        """Test content analysis with None content"""
        with pytest.raises(AttributeError):
            await content_analysis_service.analyze_content(None)

    @pytest.mark.asyncio
    async def test_analyze_content_with_invalid_object(self, content_analysis_service):
        """Test content analysis with invalid content object"""
        invalid_content = "not a content object"

        with pytest.raises(AttributeError):
            await content_analysis_service.analyze_content(invalid_content)

    @pytest.mark.asyncio
    async def test_batch_analyze_with_invalid_objects(self, content_analysis_service):
        """Test batch analysis with mixed valid and invalid objects"""
        # Create mixed list of valid and invalid contents
        contents = []
        for i in range(2):
            content = Mock(spec=Content)
            content.id = f"content_{i}"
            content.text = f"Test content {i}"
            contents.append(content)

        # Add invalid content
        contents.append("invalid_content")

        # This should fail when trying to analyze the invalid content
        with pytest.raises(AttributeError):
            await content_analysis_service.batch_analyze(contents)

    def test_analyze_text_none_input(self, content_analysis_service):
        """Test text analysis with None input"""
        with pytest.raises(AttributeError):
            content_analysis_service.analyze_text(None)

    def test_analyze_text_non_string_input(self, content_analysis_service):
        """Test text analysis with non-string input"""
        with pytest.raises(AttributeError):
            content_analysis_service.analyze_text(123)

    def test_analyze_text_special_characters(self, content_analysis_service):
        """Test text analysis with special characters"""
        text = "Football @#$%^&*() Match!"
        result = content_analysis_service.analyze_text(text)

        assert result is not None
        assert result["word_count"] == 3  # "Football", "Match", "@#$%^&*()"
        assert result["character_count"] == len(text)

    def test_analyze_text_numbers_and_mixed_content(self, content_analysis_service):
        """Test text analysis with numbers and mixed content"""
        text = "Match 123: TeamA 45 - TeamB 67 final score"
        result = content_analysis_service.analyze_text(text)

        assert result is not None
        assert result["word_count"] == 9
        assert "123" in result["keywords"]
        assert "TeamA" in result["keywords"]
        assert "TeamB" in result["keywords"]


class TestContentAnalysisServiceIntegration:
    """Integration tests for ContentAnalysisService"""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test complete service lifecycle"""
        with patch('src.services.base.BaseService.__init__'):
            service = ContentAnalysisService()
            service.logger = Mock()

            # Test initialization
            await service.initialize()
            assert service._initialized is True

            # Test content analysis
            content = Mock(spec=Content)
            content.id = "integration_test"
            content.text = "Integration test content"

            result = await service.analyze_content(content)
            assert result is not None
            assert result.content_id == "integration_test"

            # Test batch analysis
            contents = [content]
            batch_results = await service.batch_analyze(contents)
            assert len(batch_results) == 1
            assert batch_results[0].content_id == "integration_test"

            # Test shutdown
            await service.shutdown()
            assert service._initialized is False

    @pytest.mark.asyncio
    async def test_concurrent_analysis(self):
        """Test concurrent content analysis"""
        with patch('src.services.base.BaseService.__init__'):
            service = ContentAnalysisService()
            service.logger = Mock()
            service._initialized = True

            # Create multiple content objects
            contents = []
            for i in range(5):
                content = Mock(spec=Content)
                content.id = f"concurrent_{i}"
                content.text = f"Concurrent test content {i}"
                contents.append(content)

            # Create concurrent tasks
            tasks = []
            for content in contents:
                task = service.analyze_content(content)
                tasks.append(task)

            # Run all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all results
            assert len(results) == 5
            for i, result in enumerate(results):
                assert isinstance(result, AnalysisResult)
                assert result.content_id == f"concurrent_{i}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])