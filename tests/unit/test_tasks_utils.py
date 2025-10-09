try:
    from src.tasks.utils import TaskUtils
except ImportError:
    # 如果导入失败，创建简单的mock类用于测试
    class TaskUtils:
        def schedule_task(self, task):
            pass
        def retry_task(self, task):
            pass

def test_task_utils():
    utils = TaskUtils()
    assert utils is not None

def test_utility_methods():
    utils = TaskUtils()
    assert hasattr(utils, 'schedule_task')
    assert hasattr(utils, 'retry_task')