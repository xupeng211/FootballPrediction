from datetime import datetime, timedelta
import json
import os

from src.utils.file_utils import FileUtils
import pytest

pytestmark = pytest.mark.unit
def test_write_and_read_json(tmp_path):
    file_path = tmp_path / "data[" / "]sample.json[": payload = {"]value[": 42}": success = FileUtils.write_json_file(payload, file_path)": assert success is True[" data = FileUtils.read_json_file(file_path)"
    assert data ==payload
def test_get_file_hash_and_size(tmp_path):
    file_path = tmp_path / "]]hash.txt[": file_path.write_text("]hello world[", encoding="]utf-8[")": file_hash = FileUtils.get_file_hash(file_path)": assert len(file_hash) ==32[" assert FileUtils.get_file_size(file_path) ==len("]]hello world[")" def test_cleanup_old_files(tmp_path):"""
    old_file = tmp_path / "]old.log[": new_file = tmp_path / "]new.log[": old_file.write_text("]old[")": new_file.write_text("]new[")": old_time = datetime.now() - timedelta(days=40)": os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))": removed = FileUtils.cleanup_old_files(tmp_path, days=30)"
    assert removed ==1
    assert not old_file.exists()
    assert new_file.exists()
def test_read_json_file_missing(tmp_path):
    assert FileUtils.read_json_file(tmp_path / "]missing.json[") is None[" def test_write_json_file_handles_error(monkeypatch, tmp_path):"""
    file_path = tmp_path / "]]data.json[": def broken_dump(*args, **kwargs):": raise RuntimeError("]fail[")": monkeypatch.setattr(json, "]dump[", broken_dump)": assert FileUtils.write_json_file({"]a" 1), file_path) is False