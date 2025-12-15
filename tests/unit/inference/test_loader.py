"""
Unit Tests for Model Loader
模型加载器单元测试
"""

import pytest
import tempfile
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from src.inference.loader import ModelLoader, ModelMetadata, LoadedModel
from src.inference.errors import ModelLoadError, ErrorCode
from src.inference.schemas import ModelInfo, ModelType


@pytest.fixture
async def temp_model_dir():
    """创建临时模型目录"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # 创建测试模型文件
        model_file = temp_path / "test_model.pkl"
        # 创建一个简单的测试文件
        model_file.write_text("mock_model_data")

        # 创建模型元数据文件
        metadata_file = temp_path / "test_model.json"
        metadata = {
            "model_name": "test_model",
            "model_version": "1.0.0",
            "model_type": "xgboost",
            "created_at": datetime.utcnow().isoformat(),
            "file_size": model_file.stat().st_size,
            "accuracy": 0.85,
        }
        metadata_file.write_text(json.dumps(metadata, indent=2))

        yield temp_path


@pytest.fixture
async def model_loader(temp_model_dir):
    """创建模型加载器实例"""
    loader = ModelLoader(registry_path=str(temp_model_dir))
    await loader.initialize()
    yield loader
    await loader.cleanup()


class TestModelLoader:
    """模型加载器测试"""

    @pytest.mark.asyncio
    async def test_initialize_success(self, temp_model_dir):
        """测试初始化成功"""
        loader = ModelLoader(registry_path=str(temp_model_dir))
        await loader.initialize()

        assert len(loader._model_metadata) > 0
        assert "test_model" in loader._model_metadata

    @pytest.mark.asyncio
    async def test_load_model_success(self, model_loader):
        """测试成功加载模型"""
        with patch("joblib.load") as mock_load:
            mock_model = Mock()
            mock_load.return_value = mock_model

            loaded_model = await model_loader.load("test_model")

            assert loaded_model is not None
            assert isinstance(loaded_model, LoadedModel)
            assert loaded_model.model == mock_model
            mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_model_not_found(self, model_loader):
        """测试加载不存在的模型"""
        with pytest.raises(ModelLoadError) as exc_info:
            await model_loader.load("nonexistent_model")

        assert exc_info.value.error_code == ErrorCode.MODEL_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_model_cached(self, model_loader):
        """测试模型缓存"""
        with patch("joblib.load") as mock_load:
            mock_model = Mock()
            mock_load.return_value = mock_model

            # 第一次加载
            model1 = await model_loader.get("test_model")
            # 第二次获取（应该来自缓存）
            model2 = await model_loader.get("test_model")

            assert model1 == model2
            # joblib.load 应该只被调用一次
            mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_model_info(self, model_loader):
        """测试获取模型信息"""
        model_info = await model_loader.get_model_info("test_model")

        assert model_info is not None
        assert model_info.model_name == "test_model"
        assert model_info.model_version == "1.0.0"
        assert model_info.model_type == ModelType.XGBOOST

    @pytest.mark.asyncio
    async def test_list_models(self, model_loader):
        """测试列出所有模型"""
        models = await model_loader.list_models()

        assert len(models) >= 1
        assert any(m.model_name == "test_model" for m in models)

    @pytest.mark.asyncio
    async def test_set_default_model(self, model_loader):
        """测试设置默认模型"""
        await model_loader.set_default_model(ModelType.XGBOOST, "test_model")
        default_model = await model_loader.get_default_model(ModelType.XGBOOST)

        assert default_model == "test_model"

    @pytest.mark.asyncio
    async def test_unload_model(self, model_loader):
        """测试卸载模型"""
        with patch("joblib.load") as mock_load:
            mock_model = Mock()
            mock_load.return_value = mock_model

            # 先加载模型
            await model_loader.get("test_model")
            assert "test_model" in model_loader._loaded_models

            # 卸载模型
            await model_loader.unload_model("test_model")
            assert "test_model" not in model_loader._loaded_models

    @pytest.mark.asyncio
    async def test_reload_model(self, model_loader):
        """测试重新加载模型"""
        with patch("joblib.load") as mock_load:
            mock_model = Mock()
            mock_load.return_value = mock_model

            loaded_model = await model_loader.reload_model("test_model")

            assert loaded_model is not None
            assert isinstance(loaded_model, LoadedModel)
            assert mock_load.call_count == 2  # 第一次加载 + 重载

    def test_get_load_stats(self, model_loader):
        """测试获取加载统计"""
        stats = model_loader.get_load_stats()

        assert "total_loads" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "loaded_models" in stats
        assert "total_models" in stats

    def test_detect_model_type(self, model_loader):
        """测试模型类型检测"""
        assert (
            model_loader._detect_model_type(Path("xgboost_model.pkl"))
            == ModelType.XGBOOST
        )
        assert model_loader._detect_model_type(Path("lstm_model.h5")) == ModelType.LSTM
        assert (
            model_loader._detect_model_type(Path("ensemble_model.joblib"))
            == ModelType.ENSEMBLE
        )
        assert (
            model_loader._detect_model_type(Path("mock_model.pkl")) == ModelType.XGBOOST
        )


class TestModelMetadata:
    """模型元数据测试"""

    def test_create_metadata(self, temp_model_dir):
        """测试创建元数据"""
        model_file = temp_model_dir / "test_model.pkl"
        model_info = ModelInfo(
            model_name="test_model",
            model_version="1.0.0",
            model_type=ModelType.XGBOOST,
            created_at=datetime.utcnow(),
        )

        metadata = ModelMetadata(model_info, str(model_file))

        assert metadata.model_info.model_name == "test_model"
        assert metadata.file_path == str(model_file)
        assert metadata.file_hash is not None
        assert metadata.last_modified is not None

    def test_is_modified(self, temp_model_dir):
        """测试文件修改检查"""
        model_file = temp_model_dir / "test_model.pkl"
        model_info = ModelInfo(
            model_name="test_model",
            model_version="1.0.0",
            model_type=ModelType.XGBOOST,
            created_at=datetime.utcnow(),
        )

        metadata = ModelMetadata(model_info, str(model_file))

        # 初始状态应该未修改
        assert not metadata.is_modified()

        # 修改文件时间戳
        import time

        time.sleep(0.1)  # 确保时间差异
        model_file.touch()

        # 现在应该检测到修改
        assert metadata.is_modified()


class TestLoadedModel:
    """已加载模型测试"""

    def test_create_loaded_model(self, temp_model_dir):
        """测试创建已加载模型"""
        mock_model = Mock()
        model_info = ModelInfo(
            model_name="test_model",
            model_version="1.0.0",
            model_type=ModelType.XGBOOST,
            created_at=datetime.utcnow(),
        )
        metadata = ModelMetadata(model_info, str(temp_model_dir / "test_model.pkl"))

        loaded_model = LoadedModel(mock_model, metadata)

        assert loaded_model.model == mock_model
        assert loaded_model.metadata == metadata
        assert loaded_model.access_count == 0
        assert loaded_model.load_time is not None

    def test_access_model(self, temp_model_dir):
        """测试访问模型"""
        mock_model = Mock()
        model_info = ModelInfo(
            model_name="test_model",
            model_version="1.0.0",
            model_type=ModelType.XGBOOST,
            created_at=datetime.utcnow(),
        )
        metadata = ModelMetadata(model_info, str(temp_model_dir / "test_model.pkl"))

        loaded_model = LoadedModel(mock_model, metadata)

        # 访问模型
        returned_model = loaded_model.access()

        assert returned_model == mock_model
        assert loaded_model.access_count == 1
        assert loaded_model.last_access is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
