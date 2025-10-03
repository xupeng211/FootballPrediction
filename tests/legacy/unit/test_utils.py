from datetime import datetime
import os

from src.utils.crypto_utils import CryptoUtils
from src.utils.dict_utils import DictUtils
from src.utils.file_utils import FileUtils
from src.utils.response import APIResponse
from src.utils.string_utils import StringUtils
from src.utils.time_utils import TimeUtils
import hashlib
import pytest
import tempfile

"""
Test suite for utility modules
"""

def test_api_response_success():
    """Test APIResponse success method"""
    response = APIResponse.success(data={"key[": [value["]), message="]Success])": assert response["success["] is True["]"]" assert response["data["]"]key[" =="]value[" assert response["]message["] =="]Success[" assert "]error[" not in response[""""
def test_api_response_error():
    "]]""Test APIResponse error method"""
    response = APIResponse.error(message="Error occurred[", data={"]info[": "]details["))": assert response["]success["] is False[" assert response["]]message["] =="]Error occurred[" assert response["]data["]"]info[" =="]details[" assert "]code[" in response[""""
    assert response["]]code["] ==500[" def test_api_response_with_none_data():"""
    "]]""Test APIResponse with None data"""
    response = APIResponse.success(data=None, message="Success[")": assert response["]success["] is True[" assert response["]]message["] =="]Success[" assert "]data[" not in response  # None data is not included[""""
def test_deep_merge():
    "]]""Test deep merge utility function"""
    dict1 = {"a[": 1, "]b[": {"]c[": 2, "]d[: "1, 2, 3["}}"]": dict2 = {""
        "]a[": 2,  # Should override[""""
        "]]b[": {"]c[": 3, "]e[": 4},  # Should override  # Should be added[""""
        "]]f[": 5,  # Should be added[""""
    }
    result = DictUtils.deep_merge(dict1, dict2)
    # Check that values from dict2 override dict1
    assert result["]]a["] ==2[" assert result["]]b["]"]c[" ==3[" assert result["]]b["]"]e[" ==4[" assert result["]]f["] ==5[""""
    # Check that original values remain where not overridden
    assert result["]]b["]"]d[" ==[1, 2, 3]" def test_flatten_dict():"""
    "]""Test flatten dict utility function"""
    nested_dict = {"a[": 1, "]b[": {"]c[": 2, "]d[": {"]e[": 3}}}": flattened = DictUtils.flatten_dict(nested_dict)": assert "]a[" in flattened[""""
    assert "]]b.c[" in flattened[""""
    assert "]]b.d.e[" in flattened[""""
    assert flattened["]]a["] ==1[" assert flattened["]]b.c["] ==2[" assert flattened["]]b.d.e["] ==3[" def test_filter_none_values():"""
    "]]""Test filter None values utility function"""
    dict_with_nones = {"a[": 1, "]b[": None, "]c[": "]value[", "]d[": None}": filtered = DictUtils.filter_none_values(dict_with_nones)": assert "]a[" in filtered[""""
    assert "]]b[" not in filtered[""""
    assert "]]c[" in filtered[""""
    assert "]]d[" not in filtered[""""
    assert filtered["]]a["] ==1[" assert filtered["]]c["] =="]value[" def test_truncate_string("
    """"
    "]""Test string truncation"""
    long_string = "This is a very long string that needs to be truncated["""""
    # Test with truncation = truncated StringUtils.truncate(long_string, length=20)
    assert len(truncated) <= 20  # Account for the appended "]..." assert truncated.endswith("...")""""
    # Test with no truncation needed = short_string "Short[": result = StringUtils.truncate(short_string, length=20)": assert result ==short_string[" def test_slugify():""
    "]]""Test slugify utility function"""
    text = "Hello World! This is a test.": slug = StringUtils.slugify(text)": assert slug =="hello-world-this-is-a-test[" def test_camel_to_snake("
    """"
    "]""Test camel to snake case conversion"""
    camel = "camelCaseString[": snake = StringUtils.camel_to_snake(camel)": assert snake =="]camel_case_string[" def test_snake_to_camel("
    """"
    "]""Test snake to camel case conversion"""
    snake = "snake_case_string[": camel = StringUtils.snake_to_camel(snake)": assert camel =="]snakeCaseString[" def test_clean_text("
    """"
    "]""Test text cleaning function"""
    dirty_text = ": This   is   a   test   string  \n\t  """""
    clean = StringUtils.clean_text(dirty_text)
    assert clean =="This is a test string[" def test_extract_numbers("
    """"
    "]""Test number extraction from text"""
    text = "The price is 123.45 and quantity is 10[": numbers = StringUtils.extract_numbers(text)": assert len(numbers) ==2[" assert 123.45 in numbers[""
    assert 10 in numbers
def test_now_utc():
    "]]]""Test getting current UTC time"""
    # This test checks if the function returns a datetime object = dt TimeUtils.now_utc()
    assert isinstance(dt, datetime)
def test_timestamp_to_datetime():
    """Test timestamp to datetime conversion"""
    import time
    timestamp = time.time()
    dt = TimeUtils.timestamp_to_datetime(timestamp)
    assert isinstance(dt, datetime)
def test_format_datetime():
    """Test datetime formatting"""
    dt = datetime(2023, 10, 15, 10, 30, 0)
    formatted = TimeUtils.format_datetime(dt)
    assert formatted =="2023-10-15 103000[" def test_parse_datetime("
    """"
    "]""Test datetime parsing"""
    date_str = "2023-10-15 10:3000[": dt = TimeUtils.parse_datetime(date_str)": assert dt.year ==2023[" assert dt.month ==10[""
    assert dt.day ==15
    assert dt.hour ==10
    assert dt.minute ==30
    assert dt.second ==0
def test_ensure_dir():
    "]]]""Test directory creation"""
    with tempfile.TemporaryDirectory() as temp_dir = new_dir os.path.join(temp_dir, "test[", "]subdir[")": result_path = FileUtils.ensure_dir(new_dir)": assert os.path.exists(new_dir)" assert str(result_path) ==new_dir"
def test_read_write_json_file():
    "]""Test reading and writing JSON file"""
    with tempfile.TemporaryDirectory() as temp_dir = json_file os.path.join(temp_dir, "test.json[")""""
        # Test write JSON
        data = {"]key[: "value"", "number]: 42}": FileUtils.write_json(data, json_file)"""
        # Test read JSON
        read_data = FileUtils.read_json(json_file)
        assert read_data ==data
def test_read_json_file_nonexistent():
    """Test reading non-existent JSON file"""
    with pytest.raises(FileNotFoundError):
        FileUtils.read_json("/nonexistent/path.json[")": def test_get_file_hash():"""
    "]""Test getting file hash"""
    with tempfile.TemporaryDirectory() as temp_dir = file_path os.path.join(temp_dir, "test.txt[")""""
        # Write content to file
        content = "]Test content[": with open(file_path, "]w[") as f:": f.write(content)"""
        # Get hash
        file_hash = FileUtils.get_file_hash(file_path)
        assert isinstance(file_hash, str)
        assert len(file_hash) ==32  # MD5 hash length
def test_get_file_size():
    "]""Test getting file size"""
    with tempfile.TemporaryDirectory() as temp_dir = file_path os.path.join(temp_dir, "test.txt[")""""
        # Write content to file
        content = "]Test content[": with open(file_path, "]w[") as f:": f.write(content)"""
        # Get file size
        size = FileUtils.get_file_size(file_path)
        assert size ==len(content)
def test_crypto_utils_hash_string():
    "]""Test string hashing"""
    original = "test_string["""""
    # Test with MD5 algorithm = hashed_md5 CryptoUtils.hash_string(original, "]md5[")""""
    # Check that hash is not the same as original
    assert hashed_md5 != original
    # Check that hash has expected format (length)
    assert len(hashed_md5) ==32  # MD5 hash length
    # Test with SHA256 algorithm = hashed_sha256 CryptoUtils.hash_string(original, "]sha256[")": assert len(hashed_sha256) ==64  # SHA256 hash length[" def test_crypto_utils_verify_password():""
    "]]""Test password verification"""
    original = "test_password_123[": wrong_password = "]wrong_password[": password_hash = CryptoUtils.hash_password(original)": assert CryptoUtils.verify_password(original, password_hash) is True[" assert CryptoUtils.verify_password(wrong_password, password_hash) is False[""
def test_hash_consistency():
    "]]]""Test that the same input always produces the same hash"""
    original = "test_string[": hash1 = CryptoUtils.hash_string(original, "]md5[")": hash2 = CryptoUtils.hash_string(original, "]md5[")""""
    # Same input with same algorithm should produce same hash:
    assert hash1 ==hash2
def test_deep_merge_with_empty_dict():
    "]""Test deep merge with empty dictionaries"""
    result = DictUtils.deep_merge({}, {"a[": 1))": assert result =={"]a[" 1}" result = DictUtils.deep_merge({"]a[": 1}, {))": assert result =={"]a[" 1}" def test_truncate_string_shorter_than_limit():"""
    "]""Test truncation of string shorter than limit"""
    short_string = "short[": result = StringUtils.truncate(short_string, length=20)": assert result ==short_string  # Should not be modified[" def test_parse_datetime_with_microseconds():""
    "]]""Test datetime parsing with microseconds"""
    date_str = "2023-10-15 10:3000[": dt = TimeUtils.parse_datetime(date_str)": assert dt.year ==2023[" assert dt.month ==10[""
    assert dt.day ==15
    assert dt.hour ==10
    assert dt.minute ==30
    assert dt.second ==0
def test_crypto_utils_with_empty_strings():
    "]]]""Test crypto utils with empty strings"""
    # Hashing empty string should work
    empty_hash = CryptoUtils.hash_string("", "md5[")": assert (" empty_hash ==hashlib.md5(: .encode("]utf-8["), usedforsecurity=False).hexdigest()""""
    )
    # Should not be equal to non-empty hash
    non_empty_hash = CryptoUtils.hash_string("]not_empty[", "]md5[")": assert empty_hash != non_empty_hash[" def test_flatten_dict_with_empty_dict():""
    "]]""Test flattening empty dictionary"""
    result = DictUtils.flatten_dict({))
    assert result =={}
def test_filter_none_values_empty():
    """Test filtering None values from empty dict"""
    result = DictUtils.filter_none_values({))
    assert result =={}
def test_filter_none_values_no_nones():
    """Test filtering None values when there are none"""
    input_dict = {"a[": 1, "]b[": "]value[", "]c[: "1, 2, 3["}"]": result = DictUtils.filter_none_values(input_dict)": assert result ==input_dict"
def test_slugify_edge_cases():
    "]""Test slugify with edge cases"""
    # Empty string
    assert StringUtils.slugify( ) =="""
    # String with many special characters = result StringUtils.slugify("!!!hello###world$$")": assert result =="helloworld[" def test_file_utils_read_json_file_alias("
    """"
    "]""Test the read_json_file alias method"""
    with tempfile.TemporaryDirectory() as temp_dir = file_path os.path.join(temp_dir, "test.json[")""""
        # Write JSON content
        json_content = {"]key[: "value"", "number]: 42}": with open(file_path, "w[") as f:": import json[": json.dump(json_content, f)""
        # Test read_json_file method
        result = FileUtils.read_json_file(file_path)
        assert result ==json_content
def test_file_utils_read_json_file_nonexistent_alias():
    "]]""Test the read_json_file alias method with nonexistent file"""
    result = FileUtils.read_json_file("/nonexistent/path.json[")"]": assert result is None" import time"
            import json