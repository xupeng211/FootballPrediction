"""
Unit Tests for Hot Reload Manager
模型热更新管理器单元测试

测试模型文件监控、自动重载、版本管理和回滚功能。
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch, mock_open

from src.inference.hot_reload import (
    HotReloadManager,
    ModelFileHandler,
    get_hot_reload_manager,
    get_hot_reload_manager_sync,
)
from src.inference.errors import HotReloadError


class TestModelFileHandler:
    """模型文件处理器测试类"""

    @pytest.fixture
    def hot_reload_manager(self):
        """热更新管理器mock"""
        return Mock(spec=HotReloadManager)

    @pytest.fixture
    def file_handler(self, hot_reload_manager):
        """文件处理器实例"""
        return ModelFileHandler(hot_reload_manager)

    def test_is_model_file_valid_extensions(self, file_handler):
        """测试模型文件识别 - 有效扩展名"""
        valid_files = [
            "/path/to/model.pkl",
            "/path/to/model.joblib",
            "/path/to/model.model",
            "/path/to/model.h5",
        ]

        for file_path in valid_files:
            assert file_handler._is_model_file(file_path) is True

    def test_is_model_file_invalid_extensions(self, file_handler):
        """测试模型文件识别 - 无效扩展名"""
        invalid_files = [
            "/path/to/model.txt",
            "/path/to/model.csv",
            "/path/to/model.json",
            "/path/to/model.py",
            "/path/to/.hidden",
        ]

        for file_path in invalid_files:
            assert file_handler._is_model_file(file_path) is False

    def test_on_modified_ignores_directories(self, file_handler):
        """测试忽略目录修改事件"""
        mock_event = Mock()
        mock_event.is_directory = True

        # 应该不处理目录事件
        file_handler.on_modified(mock_event)

        # 验证没有调用处理逻辑
        file_handler.hot_reload_manager.handle_file_change.assert_not_called()

    def test_on_modified_ignores_non_model_files(self, file_handler):
        """测试忽略非模型文件"""
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = "/path/to/data.txt"

        # 应该不处理非模型文件
        file_handler.on_modified(mock_event)

        # 验证没有调用处理逻辑
        file_handler.hot_reload_manager.handle_file_change.assert_not_called()

    def test_on_modified_handles_model_files(self, file_handler):
        """测试处理模型文件"""
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = "/path/to/model.pkl"

        with patch("asyncio.create_task") as mock_create_task:
            file_handler.on_modified(mock_event)

            # 验证创建了异步任务
            mock_create_task.assert_called_once()
            args = mock_create_task.call_args[0]
            assert len(args) == 1
            # 验证任务调用了处理函数
            assert args[0] == file_handler.hot_reload_manager.handle_file_change(
                "/path/to/model.pkl"
            )

    def test_debounce_time_logic(self, file_handler):
        """测试防抖逻辑"""
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = "/path/to/model.pkl"

        with patch("asyncio.create_task") as mock_create_task:
            # 第一次修改
            file_handler.on_modified(mock_event)
            first_call_count = mock_create_task.call_count

            # 立即第二次修改（应该被防抖）
            file_handler.on_modified(mock_event)
            second_call_count = mock_create_task.call_count

            # 调用次数应该相同（防抖生效）
            assert first_call_count == second_call_count


class TestHotReloadManager:
    """热更新管理器测试类"""

    @pytest.fixture
    def temp_model_dir(self, tmp_path):
        """临时模型目录"""
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        return model_dir

    @pytest.fixture
    def hot_reload_manager(self, temp_model_dir):
        """热更新管理器实例"""
        return HotReloadManager(
            model_directory=str(temp_model_dir),
            check_interval=0.1,  # 快速检查用于测试
            max_workers=2,
        )

    @pytest.fixture
    def mock_model_loader(self):
        """模拟模型加载器"""
        loader = AsyncMock()
        loader.get.return_value = Mock()
        loader.reload_model.return_value = True
        loader.unload_model.return_value = True
        loader.get_load_stats.return_value = {"load_errors": 0}
        return loader

    def test_manager_initialization(self, hot_reload_manager):
        """测试管理器初始化"""
        assert hot_reload_manager.check_interval == 0.1
        assert hot_reload_manager.max_workers == 2
        assert hot_reload_manager._is_monitoring is False
        assert hot_reload_manager._reloading_models == set()
        assert hot_reload_manager._stats["total_reloads"] == 0

    def test_extract_model_name_simple(self, hot_reload_manager):
        """测试提取简单模型名称"""
        file_path = "/path/to/xgboost_model.pkl"
        model_name = hot_reload_manager._extract_model_name(file_path)
        assert model_name == "xgboost_model"

    def test_extract_model_name_with_version(self, hot_reload_manager):
        """测试提取带版本的模型名称"""
        file_path = "/path/to/xgboost_model_v1_2_0.pkl"
        model_name = hot_reload_manager._extract_model_name(file_path)
        assert model_name == "xgboost_model_v1_2"

    def test_extract_model_name_invalid_path(self, hot_reload_manager):
        """测试提取无效路径的模型名称"""
        invalid_paths = ["", "/", "no_extension", ".hidden"]

        for path in invalid_paths:
            model_name = hot_reload_manager._extract_model_name(path)
            assert model_name is None

    @pytest.mark.asyncio
    async def test_validate_new_model_success(self, hot_reload_manager, temp_model_dir):
        """测试验证新模型成功"""
        # 创建有效的模型文件
        model_file = temp_model_dir / "test_model.pkl"
        model_file.write_bytes(b"fake model data")

        with patch.object(hot_reload_manager, "_test_model_load") as mock_test_load:
            mock_test_load.return_value = None  # 成功

            # 应该不抛出异常
            await hot_reload_manager._validate_new_model(str(model_file))

    @pytest.mark.asyncio
    async def test_validate_new_model_file_not_exists(self, hot_reload_manager):
        """测试验证不存在的模型文件"""
        with pytest.raises(HotReloadError) as exc_info:
            await hot_reload_manager._validate_new_model("/path/to/nonexistent.pkl")

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_new_model_empty_file(
        self, hot_reload_manager, temp_model_dir
    ):
        """测试验证空模型文件"""
        empty_file = temp_model_dir / "empty.pkl"
        empty_file.write_bytes(b"")

        with pytest.raises(HotReloadError) as exc_info:
            await hot_reload_manager._validate_new_model(str(empty_file))

        assert "is empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_new_model_invalid_format(
        self, hot_reload_manager, temp_model_dir
    ):
        """测试验证无效格式文件"""
        invalid_file = temp_model_dir / "model.txt"
        invalid_file.write_bytes(b"some data")

        with pytest.raises(HotReloadError) as exc_info:
            await hot_reload_manager._validate_new_model(str(invalid_file))

        assert "Unsupported model file format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_new_model_load_failure(
        self, hot_reload_manager, temp_model_dir
    ):
        """测试验证模型加载失败"""
        model_file = temp_model_dir / "invalid_model.pkl"
        model_file.write_bytes(b"invalid model data")

        with patch.object(hot_reload_manager, "_test_model_load") as mock_test_load:
            mock_test_load.side_effect = RuntimeError("Load failed")

            with pytest.raises(HotReloadError) as exc_info:
                await hot_reload_manager._validate_new_model(str(model_file))

            assert "Model validation failed" in str(exc_info.value)

    def test_test_model_load_joblib(self, hot_reload_manager, temp_model_dir):
        """测试模型加载 - joblib格式"""
        with patch("joblib.load") as mock_load:
            mock_load.return_value = "fake model"

            model_file = temp_model_dir / "model.pkl"
            model_file.write_bytes(b"data")

            # 应该不抛出异常
            hot_reload_manager._test_model_load(str(model_file))
            mock_load.assert_called_once_with(str(model_file))

    def test_test_model_load_pickle(self, hot_reload_manager, temp_model_dir):
        """测试模型加载 - pickle格式"""
        with patch("builtins.open", mock_open(read_data=b"fake model")):
            with patch("pickle.load") as mock_pickle_load:
                mock_pickle_load.return_value = "fake model"

                model_file = temp_model_dir / "model.h5"
                model_file.write_bytes(b"data")

                # 应该不抛出异常
                hot_reload_manager._test_model_load(str(model_file))
                mock_pickle_load.assert_called_once()

    def test_test_model_load_failure(self, hot_reload_manager, temp_model_dir):
        """测试模型加载失败"""
        model_file = temp_model_dir / "corrupted.pkl"
        model_file.write_bytes(b"corrupted data")

        with pytest.raises(RuntimeError) as exc_info:
            hot_reload_manager._test_model_load(str(model_file))

        assert "Model load test failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_load_new_model_success(self, hot_reload_manager):
        """测试加载新模型成功"""
        with patch.object(hot_reload_manager, "_load_model_sync") as mock_load:
            mock_load.return_value = "loaded model"

            result = await hot_reload_manager._load_new_model("/path/to/model.pkl")

            assert result == "loaded model"
            mock_load.assert_called_once_with("/path/to/model.pkl")

    @pytest.mark.asyncio
    async def test_load_new_model_failure(self, hot_reload_manager):
        """测试加载新模型失败"""
        with patch.object(hot_reload_manager, "_load_model_sync") as mock_load:
            mock_load.side_effect = RuntimeError("Load failed")

            with pytest.raises(HotReloadError) as exc_info:
                await hot_reload_manager._load_new_model("/path/to/model.pkl")

            assert "Failed to load new model" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_reload_success(self, hot_reload_manager, mock_model_loader):
        """测试验证重载成功"""
        with patch(
            "src.inference.hot_reload.get_model_loader", return_value=mock_model_loader
        ):
            loaded_model = Mock()
            loaded_model.model = "test_model"
            mock_model_loader.get.return_value = loaded_model

            # 应该不抛出异常
            await hot_reload_manager._verify_reload("test_model")

    @pytest.mark.asyncio
    async def test_verify_reload_model_not_available(
        self, hot_reload_manager, mock_model_loader
    ):
        """测试验证重载 - 模型不可用"""
        with patch(
            "src.inference.hot_reload.get_model_loader", return_value=mock_model_loader
        ):
            mock_model_loader.get.return_value = None

            with pytest.raises(HotReloadError) as exc_info:
                await hot_reload_manager._verify_reload("test_model")

            assert "not available after reload" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rollback_model_success(self, hot_reload_manager, mock_model_loader):
        """测试模型回滚成功"""
        with patch(
            "src.inference.hot_reload.get_model_loader", return_value=mock_model_loader
        ):
            # 应该不抛出异常
            await hot_reload_manager._rollback_model("test_model")

            mock_model_loader.unload_model.assert_called_once_with("test_model")

    @pytest.mark.asyncio
    async def test_rollback_model_failure(self, hot_reload_manager, mock_model_loader):
        """测试模型回滚失败"""
        with patch(
            "src.inference.hot_reload.get_model_loader", return_value=mock_model_loader
        ):
            mock_model_loader.unload_model.side_effect = Exception("Unload failed")

            with pytest.raises(HotReloadError) as exc_info:
                await hot_reload_manager._rollback_model("test_model")

            assert "Model rollback failed" in str(exc_info.value)

    def test_record_reload_success(self, hot_reload_manager):
        """测试记录成功重载"""
        start_time = datetime.utcnow()

        hot_reload_manager._record_reload_success(
            "test_model", "/path/to/model.pkl", start_time
        )

        assert hot_reload_manager._stats["successful_reloads"] == 1
        assert hot_reload_manager._stats["total_reloads"] == 1
        assert len(hot_reload_manager._reload_history) == 1

        record = hot_reload_manager._reload_history[0]
        assert record["model_name"] == "test_model"
        assert record["status"] == "success"
        assert "reload_time_seconds" in record

    def test_record_reload_failure(self, hot_reload_manager):
        """测试记录失败重载"""
        start_time = datetime.utcnow()
        error = "Load failed"

        hot_reload_manager._record_reload_failure(
            "test_model", "/path/to/model.pkl", start_time, error
        )

        assert hot_reload_manager._stats["failed_reloads"] == 1
        assert hot_reload_manager._stats["total_reloads"] == 1
        assert len(hot_reload_manager._reload_history) == 1

        record = hot_reload_manager._reload_history[0]
        assert record["model_name"] == "test_model"
        assert record["status"] == "failed"
        assert record["error"] == error

    @pytest.mark.asyncio
    async def test_trigger_reload_callbacks(self, hot_reload_manager):
        """测试触发重载回调"""
        callback1 = AsyncMock()
        callback2 = Mock()
        callback3 = AsyncMock(side_effect=Exception("Callback error"))

        hot_reload_manager._reload_callbacks = [callback1, callback2, callback3]

        await hot_reload_manager._trigger_reload_callbacks("test_model", "success")

        # 验证所有回调都被调用
        callback1.assert_called_once_with("test_model", "success", None)
        callback2.assert_called_once_with("test_model", "success", None)
        callback3.assert_called_once_with("test_model", "success", None)

    def test_add_remove_reload_callbacks(self, hot_reload_manager):
        """测试添加和移除重载回调"""
        callback1 = Mock()
        callback2 = Mock()

        # 添加回调
        hot_reload_manager.add_reload_callback(callback1)
        hot_reload_manager.add_reload_callback(callback2)
        assert len(hot_reload_manager._reload_callbacks) == 2

        # 移除回调
        hot_reload_manager.remove_reload_callback(callback1)
        assert len(hot_reload_manager._reload_callbacks) == 1
        assert hot_reload_manager._reload_callbacks[0] == callback2

    @pytest.mark.asyncio
    async def test_force_reload_success(self, hot_reload_manager, temp_model_dir):
        """测试强制重载成功"""
        # 创建模型文件
        model_file = temp_model_dir / "test_model.pkl"
        model_file.write_bytes(b"model data")

        with patch.object(hot_reload_manager, "_reload_model") as mock_reload:
            mock_reload.return_value = None

            await hot_reload_manager.force_reload("test_model", str(model_file))

            mock_reload.assert_called_once_with("test_model", str(model_file))

    @pytest.mark.asyncio
    async def test_force_reload_file_not_found(self, hot_reload_manager):
        """测试强制重载 - 文件未找到"""
        with pytest.raises(HotReloadError) as exc_info:
            await hot_reload_manager.force_reload("nonexistent_model")

        assert "No model file found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_loop(self, hot_reload_manager, mock_model_loader):
        """测试健康检查循环"""
        hot_reload_manager._is_monitoring = True

        with patch(
            "src.inference.hot_reload.get_model_loader", return_value=mock_model_loader
        ):
            with patch("asyncio.sleep", side_effect=Exception("Stop loop")):
                try:
                    await hot_reload_manager._health_check_loop()
                except Exception as e:
                    if str(e) != "Stop loop":
                        raise

                # 验证执行了健康检查
                mock_model_loader.get_load_stats.assert_called()

    @pytest.mark.asyncio
    async def test_perform_health_check_success(
        self, hot_reload_manager, mock_model_loader
    ):
        """测试执行健康检查成功"""
        mock_model_loader.get_load_stats.return_value = {"load_errors": 5}

        with patch(
            "src.inference.hot_reload.get_model_loader", return_value=mock_model_loader
        ):
            # 应该不抛出异常
            await hot_reload_manager._perform_health_check()

        assert hot_reload_manager._last_health_check is not None

    @pytest.mark.asyncio
    async def test_perform_health_check_high_error_rate(
        self, hot_reload_manager, mock_model_loader
    ):
        """测试执行健康检查 - 高错误率"""
        mock_model_loader.get_load_stats.return_value = {"load_errors": 15}

        with patch(
            "src.inference.hot_reload.get_model_loader", return_value=mock_model_loader
        ):
            with patch("src.inference.hot_reload.logger") as mock_logger:
                # 应该不抛出异常，但会记录警告
                await hot_reload_manager._perform_health_check()

                # 验证记录了警告
                mock_logger.warning.assert_called()

    def test_get_reload_stats(self, hot_reload_manager):
        """测试获取重载统计"""
        hot_reload_manager._stats["successful_reloads"] = 8
        hot_reload_manager._stats["failed_reloads"] = 2
        hot_reload_manager._stats["monitoring_start"] = datetime.utcnow()
        hot_reload_manager._reloading_models.add("model1")

        stats = hot_reload_manager.get_reload_stats()

        assert stats["total_reloads"] == 10
        assert stats["successful_reloads"] == 8
        assert stats["failed_reloads"] == 2
        assert stats["success_rate"] == 80.0
        assert stats["is_monitoring"] is False
        assert "model1" in stats["reloading_models"]
        assert "uptime_seconds" in stats

    def test_get_reload_history(self, hot_reload_manager):
        """测试获取重载历史"""
        # 添加一些历史记录
        for i in range(5):
            hot_reload_manager._reload_history.append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "model_name": f"model_{i}",
                    "status": "success",
                }
            )

        history = hot_reload_manager.get_reload_history(limit=3)

        assert len(history) == 3
        # 应该返回最新的3条记录
        assert history[0]["model_name"] == "model_4"
        assert history[1]["model_name"] == "model_3"
        assert history[2]["model_name"] == "model_2"

    @pytest.mark.asyncio
    async def test_cleanup(self, hot_reload_manager):
        """测试清理资源"""
        hot_reload_manager._reloading_models.add("model1")
        hot_reload_manager._reload_history.append({"test": "data"})
        hot_reload_manager._reload_callbacks.append(Mock())

        await hot_reload_manager.cleanup()

        assert len(hot_reload_manager._reloading_models) == 0
        assert len(hot_reload_manager._reload_history) == 0
        assert len(hot_reload_manager._reload_callbacks) == 0

    @pytest.mark.asyncio
    async def test_get_hot_reload_manager_singleton(self):
        """测试全局热更新管理器实例"""
        with patch.dict(
            "os.environ",
            {"MODEL_DIRECTORY": "/tmp/models", "HOT_RELOAD_CHECK_INTERVAL": "0.5"},
        ):
            manager1 = await get_hot_reload_manager()
            manager2 = await get_hot_reload_manager()

            # 应该返回同一个实例
            assert manager1 is manager2

    def test_get_hot_reload_manager_sync_success(self):
        """测试同步获取热更新管理器"""
        # 先设置全局实例
        manager = HotReloadManager()
        import src.inference.hot_reload

        src.inference.hot_reload._hot_reload_manager = manager

        # 同步获取应该成功
        result = get_hot_reload_manager_sync()
        assert result is manager

    def test_get_hot_reload_manager_sync_not_initialized(self):
        """测试同步获取未初始化的管理器"""
        # 清除全局实例
        import src.inference.hot_reload

        src.inference.hot_reload._hot_reload_manager = None

        with pytest.raises(RuntimeError) as exc_info:
            get_hot_reload_manager_sync()

        assert "HotReloadManager not initialized" in str(exc_info.value)
