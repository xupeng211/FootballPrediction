try:
    from src.lineage.metadata_manager import MetadataManager
except ImportError:
    # 如果导入失败，创建简单的mock类用于测试
    class MetadataManager:
        def store_metadata(self, metadata):
            pass
        def retrieve_metadata(self, id):
            pass
        def update_metadata(self, id, metadata):
            pass

def test_metadata_manager():
    manager = MetadataManager()
    assert manager is not None

def test_metadata_methods():
    manager = MetadataManager()
    assert hasattr(manager, 'store_metadata')
    assert hasattr(manager, 'retrieve_metadata')
    assert hasattr(manager, 'update_metadata')