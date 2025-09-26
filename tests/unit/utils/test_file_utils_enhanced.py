"""
Enhanced test file for file_utils.py utility module
Provides comprehensive coverage for file processing utilities
"""

import pytest
import json
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from unittest.mock import patch, Mock, mock_open, call

# Import directly to avoid NumPy reload issues
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from utils.file_utils import FileUtils


class TestFileUtilsEnsureDir:
    """Test ensure_dir method"""

    def test_ensure_dir_creates_directory(self, tmp_path):
        """Test that ensure_dir creates directory if it doesn't exist"""
        new_dir = tmp_path / "new" / "nested" / "directory"
        assert not new_dir.exists()

        result = FileUtils.ensure_dir(new_dir)

        assert result == new_dir
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_dir_existing_directory(self, tmp_path):
        """Test that ensure_dir works with existing directory"""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        assert existing_dir.exists()

        result = FileUtils.ensure_dir(existing_dir)

        assert result == existing_dir
        assert existing_dir.exists()

    def test_ensure_dir_with_string_path(self, tmp_path):
        """Test ensure_dir with string path"""
        path_str = str(tmp_path / "string" / "path")
        result = FileUtils.ensure_dir(path_str)

        assert isinstance(result, Path)
        assert result.exists()
        assert result.is_dir()

    def test_ensure_dir_parent_directories(self, tmp_path):
        """Test ensure_dir creates parent directories"""
        deep_path = tmp_path / "level1" / "level2" / "level3"
        assert not deep_path.exists()

        result = FileUtils.ensure_dir(deep_path)

        assert result == deep_path
        assert deep_path.exists()
        assert deep_path.parent.exists()
        assert deep_path.parent.parent.exists()

    @patch('utils.file_utils.Path.mkdir')
    def test_ensure_dir_permission_error(self, mock_mkdir):
        """Test ensure_dir handles permission errors"""
        mock_mkdir.side_effect = PermissionError("Permission denied")

        with pytest.raises(PermissionError):
            FileUtils.ensure_dir("/restricted/path")

    def test_ensure_dir_alias_method(self, tmp_path):
        """Test ensure_directory alias method"""
        new_dir = tmp_path / "alias_test"

        result1 = FileUtils.ensure_dir(new_dir)
        result2 = FileUtils.ensure_directory(new_dir)

        assert result1 == result2
        assert new_dir.exists()


class TestFileUtilsReadJson:
    """Test read_json method"""

    def test_read_json_valid_file(self, tmp_path):
        """Test reading valid JSON file"""
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        json_file = tmp_path / "test.json"

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)

        result = FileUtils.read_json(json_file)
        assert result == test_data

    def test_read_json_unicode_content(self, tmp_path):
        """Test reading JSON with Unicode content"""
        test_data = {"中文": "测试", "emoji": "🎉", "special": "©®™"}
        json_file = tmp_path / "unicode.json"

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)

        result = FileUtils.read_json(json_file)
        assert result == test_data

    def test_read_json_nested_data(self, tmp_path):
        """Test reading JSON with nested data structures"""
        test_data = {
            "level1": {
                "level2": {
                    "deep": {"value": "nested"},
                    "list": [1, {"nested": "item"}]
                }
            }
        }
        json_file = tmp_path / "nested.json"

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)

        result = FileUtils.read_json(json_file)
        assert result == test_data

    def test_read_json_file_not_found(self, tmp_path):
        """Test reading non-existent JSON file"""
        non_existent = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError) as exc_info:
            FileUtils.read_json(non_existent)

        assert "无法读取JSON文件" in str(exc_info.value)
        assert str(non_existent) in str(exc_info.value)

    def test_read_json_invalid_json(self, tmp_path):
        """Test reading invalid JSON file"""
        invalid_json = tmp_path / "invalid.json"

        with open(invalid_json, 'w', encoding='utf-8') as f:
            f.write('{"invalid": json, "missing": quote}')

        with pytest.raises(FileNotFoundError) as exc_info:
            FileUtils.read_json(invalid_json)

    def test_read_json_empty_file(self, tmp_path):
        """Test reading empty JSON file"""
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("", encoding='utf-8')

        with pytest.raises(FileNotFoundError):
            FileUtils.read_json(empty_file)

    def test_read_json_with_string_path(self, tmp_path):
        """Test read_json with string path"""
        test_data = {"test": "value"}
        json_file = tmp_path / "string_test.json"

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        result = FileUtils.read_json(str(json_file))
        assert result == test_data

    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_read_json_permission_error(self, mock_open):
        """Test read_json handles permission errors"""
        with pytest.raises(FileNotFoundError):
            FileUtils.read_json("/restricted/file.json")


class TestFileUtilsWriteJson:
    """Test write_json method"""

    def test_write_json_basic(self, tmp_path):
        """Test basic JSON writing"""
        test_data = {"key": "value", "number": 42}
        json_file = tmp_path / "write_test.json"

        FileUtils.write_json(test_data, json_file)

        assert json_file.exists()
        with open(json_file, 'r', encoding='utf-8') as f:
            result = json.load(f)
        assert result == test_data

    def test_write_json_unicode_content(self, tmp_path):
        """Test writing JSON with Unicode content"""
        test_data = {"中文": "测试", "emoji": "🎉"}
        json_file = tmp_path / "unicode_write.json"

        FileUtils.write_json(test_data, json_file)

        with open(json_file, 'r', encoding='utf-8') as f:
            result = json.load(f)
        assert result == test_data

    def test_write_json_complex_data(self, tmp_path):
        """Test writing complex data structures"""
        test_data = {
            "string": "value",
            "number": 3.14159,
            "boolean": True,
            "none": None,
            "list": [1, 2, {"nested": "item"}],
            "nested": {"deep": {"very": {"deep": "value"}}}
        }
        json_file = tmp_path / "complex.json"

        FileUtils.write_json(test_data, json_file)

        with open(json_file, 'r', encoding='utf-8') as f:
            result = json.load(f)
        assert result == test_data

    def test_write_json_create_parent_directories(self, tmp_path):
        """Test write_json creates parent directories"""
        test_data = {"test": "value"}
        deep_path = tmp_path / "parent" / "child" / "grandchild" / "data.json"

        FileUtils.write_json(test_data, deep_path)

        assert deep_path.exists()
        assert deep_path.parent.exists()
        assert deep_path.parent.parent.exists()

    def test_write_json_existing_file(self, tmp_path):
        """Test write_json overwrites existing file"""
        original_data = {"original": "data"}
        new_data = {"new": "data"}
        json_file = tmp_path / "overwrite.json"

        # Write original data
        FileUtils.write_json(original_data, json_file)

        # Write new data
        FileUtils.write_json(new_data, json_file)

        # Verify new data
        with open(json_file, 'r', encoding='utf-8') as f:
            result = json.load(f)
        assert result == new_data

    def test_write_json_without_ensure_dir(self, tmp_path):
        """Test write_json without ensuring directory"""
        test_data = {"test": "value"}
        json_file = tmp_path / "no_ensure" / "data.json"

        # Should fail if directory doesn't exist
        with pytest.raises(FileNotFoundError):
            FileUtils.write_json(test_data, json_file, ensure_dir=False)

    def test_write_json_with_string_path(self, tmp_path):
        """Test write_json with string path"""
        test_data = {"test": "value"}
        json_file = tmp_path / "string_write.json"

        FileUtils.write_json(test_data, str(json_file))

        assert json_file.exists()

    @patch('json.dump', side_effect=TypeError("Cannot serialize"))
    def test_write_json_serialization_error(self, mock_dump, tmp_path):
        """Test write_json handles serialization errors"""
        # Create non-serializable data
        non_serializable = {"function": lambda x: x}
        json_file = tmp_path / "error.json"

        with pytest.raises(TypeError):
            FileUtils.write_json(non_serializable, json_file)

    def test_write_json_large_data(self, tmp_path):
        """Test writing large JSON data"""
        # Create large data structure
        large_data = {"items": [{"id": i, "data": f"item_{i}" * 100} for i in range(1000)]}
        json_file = tmp_path / "large.json"

        FileUtils.write_json(large_data, json_file)

        assert json_file.exists()
        assert json_file.stat().st_size > 0

    def test_write_json_encoding(self, tmp_path):
        """Test JSON file encoding"""
        test_data = {"encoding": "测试", "utf8": "🎉"}
        json_file = tmp_path / "encoding.json"

        FileUtils.write_json(test_data, json_file)

        # Verify UTF-8 encoding
        with open(json_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "测试" in content
        assert "🎉" in content


class TestFileUtilsGetFileHash:
    """Test get_file_hash method"""

    def test_get_file_hash_basic(self, tmp_path):
        """Test basic file hash calculation"""
        test_content = "Hello, World!"
        test_file = tmp_path / "hash_test.txt"
        test_file.write_text(test_content, encoding='utf-8')

        hash_result = FileUtils.get_file_hash(test_file)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 32  # MD5 hash length
        # Verify consistency
        assert FileUtils.get_file_hash(test_file) == hash_result

    def test_get_file_hash_empty_file(self, tmp_path):
        """Test hash of empty file"""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding='utf-8')

        hash_result = FileUtils.get_file_hash(empty_file)

        assert len(hash_result) == 32
        # Empty file should have consistent hash
        assert hash_result == "d41d8cd98f00b204e9800998ecf8427e"

    def test_get_file_hash_binary_content(self, tmp_path):
        """Test hash of binary content"""
        binary_content = b"\x00\x01\x02\x03\x04\x05"
        binary_file = tmp_path / "binary.bin"
        binary_file.write_bytes(binary_content)

        hash_result = FileUtils.get_file_hash(binary_file)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 32

    def test_get_file_hash_large_file(self, tmp_path):
        """Test hash of large file"""
        large_content = "A" * 10000  # 10KB of 'A's
        large_file = tmp_path / "large.txt"
        large_file.write_text(large_content, encoding='utf-8')

        hash_result = FileUtils.get_file_hash(large_file)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 32

    def test_get_file_hash_unicode_content(self, tmp_path):
        """Test hash of Unicode content"""
        unicode_content = "中文测试 🎉 特殊字符 ©®™"
        unicode_file = tmp_path / "unicode.txt"
        unicode_file.write_text(unicode_content, encoding='utf-8')

        hash_result = FileUtils.get_file_hash(unicode_file)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 32

    def test_get_file_hash_string_path(self, tmp_path):
        """Test get_file_hash with string path"""
        test_content = "String path test"
        test_file = tmp_path / "string_hash.txt"
        test_file.write_text(test_content, encoding='utf-8')

        hash_result = FileUtils.get_file_hash(str(test_file))

        assert isinstance(hash_result, str)
        assert len(hash_result) == 32

    def test_get_file_hash_nonexistent_file(self, tmp_path):
        """Test get_file_hash with non-existent file"""
        nonexistent = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            FileUtils.get_file_hash(nonexistent)


class TestFileUtilsGetFileSize:
    """Test get_file_size method"""

    def test_get_file_size_basic(self, tmp_path):
        """Test basic file size calculation"""
        content = "Hello, World!"  # 13 bytes
        test_file = tmp_path / "size_test.txt"
        test_file.write_text(content, encoding='utf-8')

        size = FileUtils.get_file_size(test_file)
        assert size == 13

    def test_get_file_size_empty_file(self, tmp_path):
        """Test size of empty file"""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding='utf-8')

        size = FileUtils.get_file_size(empty_file)
        assert size == 0

    def test_get_file_size_large_file(self, tmp_path):
        """Test size of large file"""
        content = "A" * 10000  # 10KB
        large_file = tmp_path / "large.txt"
        large_file.write_text(content, encoding='utf-8')

        size = FileUtils.get_file_size(large_file)
        assert size == 10000

    def test_get_file_size_nonexistent_file(self, tmp_path):
        """Test size of non-existent file"""
        nonexistent = tmp_path / "nonexistent.txt"

        size = FileUtils.get_file_size(nonexistent)
        assert size == 0

    def test_get_file_size_directory(self, tmp_path):
        """Test size of directory (should return 0)"""
        # This method is for files, not directories
        size = FileUtils.get_file_size(tmp_path)
        assert size == 0

    def test_get_file_size_string_path(self, tmp_path):
        """Test get_file_size with string path"""
        content = "String path test"
        test_file = tmp_path / "string_size.txt"
        test_file.write_text(content, encoding='utf-8')

        size = FileUtils.get_file_size(str(test_file))
        assert size > 0


class TestFileUtilsAliasMethods:
    """Test alias methods"""

    def test_read_json_file_alias(self, tmp_path):
        """Test read_json_file alias method"""
        test_data = {"test": "value"}
        json_file = tmp_path / "alias_read.json"

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        result1 = FileUtils.read_json(json_file)
        result2 = FileUtils.read_json_file(json_file)

        assert result1 == result2

    def test_write_json_file_alias(self, tmp_path):
        """Test write_json_file alias method"""
        test_data = {"test": "value"}
        json_file = tmp_path / "alias_write.json"

        success1 = FileUtils.write_json(test_data, json_file)
        success2 = FileUtils.write_json_file(test_data, json_file)

        assert success1 is True
        assert success2 is True

    def test_write_json_file_error_handling(self, tmp_path):
        """Test write_json_file error handling"""
        test_data = {"test": "value"}
        json_file = tmp_path / "error.json"

        with patch('utils.file_utils.FileUtils.write_json', side_effect=Exception("Write error")):
            success = FileUtils.write_json_file(test_data, json_file)
            assert success is False


class TestFileUtilsCleanupOldFiles:
    """Test cleanup_old_files method"""

    def test_cleanup_old_files_basic(self, tmp_path):
        """Test basic file cleanup"""
        # Create old file
        old_file = tmp_path / "old.log"
        old_file.write_text("old content")

        # Create new file
        new_file = tmp_path / "new.log"
        new_file.write_text("new content")

        # Set old file modification time to 40 days ago
        old_time = datetime.now() - timedelta(days=40)
        old_timestamp = old_time.timestamp()
        os.utime(old_file, (old_timestamp, old_timestamp))

        # Set new file modification time to now
        new_time = datetime.now()
        new_timestamp = new_time.timestamp()
        os.utime(new_file, (new_timestamp, new_timestamp))

        # Cleanup files older than 30 days
        removed_count = FileUtils.cleanup_old_files(tmp_path, days=30)

        assert removed_count == 1
        assert not old_file.exists()
        assert new_file.exists()

    def test_cleanup_old_files_no_old_files(self, tmp_path):
        """Test cleanup when no old files exist"""
        # Create recent file
        recent_file = tmp_path / "recent.log"
        recent_file.write_text("recent content")

        # Set file modification time to 10 days ago
        recent_time = datetime.now() - timedelta(days=10)
        recent_timestamp = recent_time.timestamp()
        os.utime(recent_file, (recent_timestamp, recent_timestamp))

        # Cleanup files older than 30 days
        removed_count = FileUtils.cleanup_old_files(tmp_path, days=30)

        assert removed_count == 0
        assert recent_file.exists()

    def test_cleanup_old_files_all_old(self, tmp_path):
        """Test cleanup when all files are old"""
        # Create multiple old files
        old_files = []
        for i in range(5):
            old_file = tmp_path / f"old_{i}.log"
            old_file.write_text(f"content {i}")
            old_files.append(old_file)

            # Set modification time to 40 days ago
            old_time = datetime.now() - timedelta(days=40)
            old_timestamp = old_time.timestamp()
            os.utime(old_file, (old_timestamp, old_timestamp))

        # Cleanup files older than 30 days
        removed_count = FileUtils.cleanup_old_files(tmp_path, days=30)

        assert removed_count == 5
        for old_file in old_files:
            assert not old_file.exists()

    def test_cleanup_old_files_mixed_age(self, tmp_path):
        """Test cleanup with mixed age files"""
        # Create files with different ages
        files_and_ages = [
            ("very_old.log", 50),    # Should be removed
            ("old.log", 35),        # Should be removed
            ("recent.log", 20),     # Should remain
            ("new.log", 5)          # Should remain
        ]

        for filename, days_ago in files_and_ages:
            file_path = tmp_path / filename
            file_path.write_text(f"content {filename}")

            # Set modification time
            file_time = datetime.now() - timedelta(days=days_ago)
            file_timestamp = file_time.timestamp()
            os.utime(file_path, (file_timestamp, file_timestamp))

        # Cleanup files older than 30 days
        removed_count = FileUtils.cleanup_old_files(tmp_path, days=30)

        assert removed_count == 2
        assert not (tmp_path / "very_old.log").exists()
        assert not (tmp_path / "old.log").exists()
        assert (tmp_path / "recent.log").exists()
        assert (tmp_path / "new.log").exists()

    def test_cleanup_old_files_nonexistent_directory(self):
        """Test cleanup with non-existent directory"""
        removed_count = FileUtils.cleanup_old_files("/nonexistent/directory", days=30)
        assert removed_count == 0

    def test_cleanup_old_files_empty_directory(self, tmp_path):
        """Test cleanup with empty directory"""
        removed_count = FileUtils.cleanup_old_files(tmp_path, days=30)
        assert removed_count == 0

    def test_cleanup_old_files_directories_only(self, tmp_path):
        """Test cleanup ignores directories"""
        # Create directory
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Set directory modification time to old
        old_time = datetime.now() - timedelta(days=40)
        old_timestamp = old_time.timestamp()
        os.utime(subdir, (old_timestamp, old_timestamp))

        # Cleanup should not remove directories
        removed_count = FileUtils.cleanup_old_files(tmp_path, days=30)

        assert removed_count == 0
        assert subdir.exists()

    def test_cleanup_old_files_default_days(self, tmp_path):
        """Test cleanup with default days (30)"""
        # Create old file
        old_file = tmp_path / "old.log"
        old_file.write_text("old content")

        # Set modification time to 40 days ago
        old_time = datetime.now() - timedelta(days=40)
        old_timestamp = old_time.timestamp()
        os.utime(old_file, (old_timestamp, old_timestamp))

        # Cleanup with default days
        removed_count = FileUtils.cleanup_old_files(tmp_path)

        assert removed_count == 1
        assert not old_file.exists()

    @patch('os.utime', side_effect=OSError("Permission denied"))
    def test_cleanup_old_files_permission_error(self, mock_utime, tmp_path):
        """Test cleanup handles permission errors gracefully"""
        # Create file
        test_file = tmp_path / "test.log"
        test_file.write_text("content")

        # Mock utime to raise error
        removed_count = FileUtils.cleanup_old_files(tmp_path, days=30)

        # Should handle error gracefully
        assert removed_count == 0

    def test_cleanup_old_files_string_path(self, tmp_path):
        """Test cleanup with string path"""
        # Create old file
        old_file = tmp_path / "string_cleanup.log"
        old_file.write_text("old content")

        # Set modification time to old
        old_time = datetime.now() - timedelta(days=40)
        old_timestamp = old_time.timestamp()
        os.utime(old_file, (old_timestamp, old_timestamp))

        # Cleanup with string path
        removed_count = FileUtils.cleanup_old_files(str(tmp_path), days=30)

        assert removed_count == 1
        assert not old_file.exists()


class TestFileUtilsIntegration:
    """Integration tests combining multiple methods"""

    def test_json_workflow(self, tmp_path):
        """Test complete JSON workflow: write -> hash -> size -> read"""
        test_data = {"workflow": "test", "items": [1, 2, 3]}
        json_file = tmp_path / "workflow.json"

        # Write JSON
        FileUtils.write_json(test_data, json_file)
        assert json_file.exists()

        # Get hash
        file_hash = FileUtils.get_file_hash(json_file)
        assert len(file_hash) == 32

        # Get size
        file_size = FileUtils.get_file_size(json_file)
        assert file_size > 0

        # Read back
        read_data = FileUtils.read_json(json_file)
        assert read_data == test_data

    def test_directory_management_workflow(self, tmp_path):
        """Test directory management workflow"""
        # Create nested directory structure
        data_dir = tmp_path / "data" / "processed" / "2023"

        # Ensure directory exists
        created_dir = FileUtils.ensure_dir(data_dir)
        assert created_dir.exists()

        # Write multiple JSON files
        for i in range(3):
            data = {"id": i, "value": f"item_{i}"}
            file_path = data_dir / f"item_{i}.json"
            FileUtils.write_json(data, file_path)

        # Verify files exist
        json_files = list(data_dir.glob("*.json"))
        assert len(json_files) == 3

        # Get file info for all files
        file_info = []
        for json_file in json_files:
            info = {
                "path": json_file,
                "hash": FileUtils.get_file_hash(json_file),
                "size": FileUtils.get_file_size(json_file),
                "data": FileUtils.read_json(json_file)
            }
            file_info.append(info)

        # Verify all files have unique hashes
        hashes = [info["hash"] for info in file_info]
        assert len(hashes) == len(set(hashes))

    def test_file_lifecycle_with_cleanup(self, tmp_path):
        """Test file lifecycle with cleanup"""
        data_dir = tmp_path / "temp_data"
        FileUtils.ensure_dir(data_dir)

        # Create files with different timestamps
        files_info = []
        for i in range(10):
            file_path = data_dir / f"temp_{i}.json"
            data = {"id": i, "created": datetime.now().isoformat()}
            FileUtils.write_json(data, file_path)

            # Set different modification times
            days_ago = 40 - (i * 5)  # Files from 40 to 5 days ago
            file_time = datetime.now() - timedelta(days=days_ago)
            file_timestamp = file_time.timestamp()
            os.utime(file_path, (file_timestamp, file_timestamp))

            files_info.append({
                "path": file_path,
                "days_ago": days_ago
            })

        # Verify all files exist
        for file_info in files_info:
            assert file_info["path"].exists()

        # Cleanup files older than 30 days
        removed_count = FileUtils.cleanup_old_files(data_dir, days=30)

        # Should remove files older than 30 days (approximately 4 files)
        assert removed_count >= 1

        # Verify remaining files
        remaining_files = list(data_dir.glob("*.json"))
        assert len(remaining_files) > 0

    def test_error_handling_workflow(self, tmp_path):
        """Test error handling in file operations"""
        # Test with non-existent operations
        try:
            # This should fail gracefully
            data = FileUtils.read_json_file(tmp_path / "nonexistent.json")
            assert data is None
        except Exception:
            pytest.fail("read_json_file should handle FileNotFoundError gracefully")

        # Test write to protected location (mock)
        with patch('utils.file_utils.open', side_effect=PermissionError("Permission denied")):
            success = FileUtils.write_json_file({"test": "data"}, tmp_path / "protected.json")
            assert success is False

    def test_unicode_workflow(self, tmp_path):
        """Test workflow with Unicode content"""
        unicode_data = {
            "中文": "测试数据",
            "emoji": ["🎉", "✨", "🚀"],
            "special": "©®™",
            "mixed": "English 中文 mix 🎉"
        }

        json_file = tmp_path / "unicode_test.json"

        # Write Unicode data
        FileUtils.write_json(unicode_data, json_file)

        # Verify file properties
        assert json_file.exists()
        hash_value = FileUtils.get_file_hash(json_file)
        file_size = FileUtils.get_file_size(json_file)

        assert len(hash_value) == 32
        assert file_size > 0

        # Read back and verify
        read_data = FileUtils.read_json(json_file)
        assert read_data == unicode_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])