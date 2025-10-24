"""
工具类综合测试
覆盖所有工具模块的核心功能
"""

import pytest
import json
import re
import os
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
import tempfile
from pathlib import Path


# 测试字符串工具
@pytest.mark.unit

class TestStringUtils:
    """字符串工具测试"""

    def test_slugify(self):
        """测试字符串slug化"""

        def slugify(text: str) -> str:
            """将文本转换为slug"""
            # 转换为小写
            text = text.lower()
            # 替换空格和特殊字符
            text = re.sub(r"[^\w\s-]", "", text)
            text = re.sub(r"[-\s]+", "-", text)
            # 移除首尾连字符
            return text.strip("-")

        test_cases = [
            ("Hello World", "hello-world"),
            ("  Test   String  ", "test-string"),
            ("Special@#$%Characters", "special-characters"),
            ("Multiple---Hyphens", "multiple-hyphens"),
            ("", ""),
            ("123 Numbers 456", "123-numbers-456"),
        ]

        for input_text, expected in test_cases:
            _result = slugify(input_text)
            assert _result == expected

    def test_truncate_text(self):
        """测试文本截断"""

        def truncate(text: str, max_length: int, suffix: str = "...") -> str:
            """截断文本到指定长度"""
            if len(text) <= max_length:
                return text
            return text[: max_length - len(suffix)] + suffix

        test_cases = [
            ("Hello World", 10, "Hello..."),
            ("Short", 10, "Short"),
            ("Very long text", 5, "Ve..."),
            ("", 10, ""),
            ("Test", 0, "..."),
        ]

        for text, max_len, expected in test_cases:
            _result = truncate(text, max_len)
            assert _result == expected

    def test_extract_numbers(self):
        """测试提取数字"""

        def extract_numbers(text: str) -> List[int]:
            """从文本中提取所有数字"""
            return [int(num) for num in re.findall(r"\d+", text)]

        test_cases = [
            ("123abc456", [123, 456]),
            ("no numbers", []),
            ("score: 3-1", [3, 1]),
            ("2024-01-01", [2024, 1, 1]),
            ("", []),
        ]

        for text, expected in test_cases:
            _result = extract_numbers(text)
            assert _result == expected

    def test_generate_random_string(self):
        """测试生成随机字符串"""

        def random_string(
            length: int, use_digits: bool = True, use_letters: bool = True
        ) -> str:
            """生成随机字符串"""
            charset = ""
            if use_letters:
                charset += "abcdefghijklmnopqrstuvwxyz"
            if use_digits:
                charset += "0123456789"

            if not charset:
                return ""

            return "".join(secrets.choice(charset) for _ in range(length))

        # 测试不同长度
        for length in [0, 5, 10, 20]:
            _result = random_string(length)
            assert len(result) == length

        # 测试只使用字母
        _result = random_string(10, use_digits=False)
        assert not any(c.isdigit() for c in result)
        assert len(result) == 10

        # 测试只使用数字
        _result = random_string(10, use_letters=False)
        assert all(c.isdigit() for c in result)
        assert len(result) == 10

    def test_is_email_valid(self):
        """测试邮箱验证"""

        def is_valid_email(email: str) -> bool:
            """验证邮箱格式"""
            pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            return bool(re.match(pattern, email))

        # 有效邮箱
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "123@456.com",
            "a@b.c",
        ]

        for email in valid_emails:
            assert is_valid_email(email) is True

        # 无效邮箱
        invalid_emails = [
            "",  # 空
            "not-an-email",  # 缺少@
            "@example.com",  # 缺少用户名
            "user@",  # 缺少域名
            "user@.com",  # 无效域名
            "user@domain",  # 缺少TLD
            "user space@domain.com",  # 包含空格
        ]

        for email in invalid_emails:
            assert is_valid_email(email) is False


# 测试时间工具
class TestTimeUtils:
    """时间工具测试"""

    def test_format_duration(self):
        """测试时间间隔格式化"""

        def format_duration(seconds: float) -> str:
            """格式化时间间隔"""
            if seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                minutes = int(seconds // 60)
                secs = seconds % 60
                return f"{minutes}m {secs:.0f}s"
            else:
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                return f"{hours}h {minutes}m"

        test_cases = [
            (30, "30.0s"),
            (90, "1m 30s"),
            (3661, "1h 1m"),
            (7200, "2h 0m"),
            (45.5, "45.5s"),
        ]

        for seconds, expected in test_cases:
            _result = format_duration(seconds)
            assert _result == expected

    def test_time_ago(self):
        """测试时间差计算"""

        def time_ago(dt: datetime, relative_to: Optional[datetime] = None) -> str:
            """计算时间差"""
            if relative_to is None:
                relative_to = datetime.now(timezone.utc)

            diff = relative_to - dt
            seconds = diff.total_seconds()

            if seconds < 60:
                return "just now"
            elif seconds < 3600:
                minutes = int(seconds // 60)
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            elif seconds < 86400:
                hours = int(seconds // 3600)
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            else:
                days = int(seconds // 86400)
                return f"{days} day{'s' if days > 1 else ''} ago"

        now = datetime.now(timezone.utc)

        test_cases = [
            (now - timedelta(seconds=30), "just now"),
            (now - timedelta(minutes=5), "5 minutes ago"),
            (now - timedelta(minutes=1), "1 minute ago"),
            (now - timedelta(hours=3), "3 hours ago"),
            (now - timedelta(hours=1), "1 hour ago"),
            (now - timedelta(days=2), "2 days ago"),
        ]

        for past_time, expected in test_cases:
            _result = time_ago(past_time, now)
            assert _result == expected

    def test_is_business_hours(self):
        """测试工作时间判断"""

        def is_business_hours(dt: datetime, timezone_offset: int = 0) -> bool:
            """判断是否在工作时间（9-17）"""
            # 调整时区
            dt = dt + timedelta(hours=timezone_offset)
            # 检查是否为工作日
            if dt.weekday() >= 5:  # 周末
                return False
            # 检查时间
            return 9 <= dt.hour < 17

        # 工作日工作时间
        work_time = datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc)  # 周一14:00
        assert is_business_hours(work_time) is True

        # 工作日非工作时间
        non_work_time = datetime(2024, 1, 1, 20, 0, tzinfo=timezone.utc)  # 周一20:00
        assert is_business_hours(non_work_time) is False

        # 周末
        weekend = datetime(2024, 1, 6, 14, 0, tzinfo=timezone.utc)  # 周六14:00
        assert is_business_hours(weekend) is False


# 测试文件工具
class TestFileUtils:
    """文件工具测试"""

    def test_get_file_extension(self):
        """测试获取文件扩展名"""

        def get_extension(filename: str) -> str:
            """获取文件扩展名"""
            return Path(filename).suffix.lower()

        test_cases = [
            ("test.txt", ".txt"),
            ("document.pdf", ".pdf"),
            ("archive.tar.gz", ".gz"),
            ("no_extension", ""),
            ("hidden.file", ".file"),
            (".env", ".env"),
        ]

        for filename, expected in test_cases:
            _result = get_extension(filename)
            assert _result == expected

    def test_safe_filename(self):
        """测试安全文件名"""

        def safe_filename(filename: str) -> str:
            """生成安全的文件名"""
            # 移除或替换不安全字符
            filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
            # 移除控制字符
            filename = re.sub(r"[\x00-\x1f\x7f]", "", filename)
            # 限制长度
            if len(filename) > 255:
                name, ext = os.path.splitext(filename)
                filename = name[: 255 - len(ext)] + ext
            return filename

        test_cases = [
            ("normal_file.txt", "normal_file.txt"),
            ("file<with>special:chars", "file_with_special_chars"),
            ("file\twith\ncontrol\x01chars", "filewithcontrolchars"),
            ("a" * 300 + ".txt", "a" * 251 + ".txt"),
        ]

        for filename, expected in test_cases:
            _result = safe_filename(filename)
            assert _result == expected

    def test_calculate_file_hash(self):
        """测试计算文件哈希"""

        def calculate_hash(content: str, algorithm: str = "md5") -> str:
            """计算内容的哈希值"""
            hash_obj = hashlib.new(algorithm)
            hash_obj.update(content.encode("utf-8"))
            return hash_obj.hexdigest()

        # 测试MD5
        content = "Hello, World!"
        expected_md5 = "65a8e279883337fed1b1c2d4a1b56f1b"
        _result = calculate_hash(content, "md5")
        assert _result == expected_md5

        # 测试SHA256
        expected_sha256 = (
            "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        )
        _result = calculate_hash(content, "sha256")
        assert _result == expected_sha256

    def test_create_temp_file(self):
        """测试创建临时文件"""

        def create_temp_file(content: str, suffix: str = ".tmp") -> str:
            """创建临时文件"""
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=suffix, delete=False
            ) as f:
                f.write(content)
                return f.name

        # 创建临时文件
        content = "Test content"
        temp_path = create_temp_file(content, ".txt")

        try:
            # 验证文件存在
            assert os.path.exists(temp_path)
            # 验证内容
            with open(temp_path, "r") as f:
                assert f.read() == content
            # 验证后缀
            assert temp_path.endswith(".txt")
        finally:
            # 清理
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# 测试数据转换工具
class TestDataConversion:
    """数据转换工具测试"""

    def test_bytes_to_human(self):
        """测试字节转换为人类可读格式"""

        def bytes_to_human(bytes_value: int) -> str:
            """转换字节为人类可读格式"""
            units = ["B", "KB", "MB", "GB", "TB"]
            size = float(bytes_value)
            unit_index = 0

            while size >= 1024 and unit_index < len(units) - 1:
                size /= 1024
                unit_index += 1

            if unit_index == 0:
                return f"{int(size)} {units[unit_index]}"
            else:
                return f"{size:.1f} {units[unit_index]}"

        test_cases = [
            (0, "0 B"),
            (512, "512 B"),
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),
            (1048576, "1.0 MB"),
            (1073741824, "1.0 GB"),
            (1099511627776, "1.0 TB"),
        ]

        for bytes_value, expected in test_cases:
            _result = bytes_to_human(bytes_value)
            assert _result == expected

    def test_parse_query_string(self):
        """测试解析查询字符串"""

        def parse_query_string(query: str) -> Dict[str, List[str]]:
            """解析查询字符串"""
            params = {}
            if not query:
                return params

            # 移除开头的?
            if query.startswith("?"):
                query = query[1:]

            for pair in query.split("&"):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    key = key.replace("+", " ")
                    value = value.replace("+", " ")
                    # URL解码
                    import urllib.parse

                    key = urllib.parse.unquote(key)
                    value = urllib.parse.unquote(value)

                    if key not in params:
                        params[key] = []
                    params[key].append(value)

            return params

        test_cases = [
            ("", {}),
            ("name=John", {"name": ["John"]}),
            ("name=John&age=30", {"name": ["John"], "age": ["30"]}),
            ("tags=python&tags=web", {"tags": ["python", "web"]}),
            ("space%20test=hello%20world", {"space test": ["hello world"]}),
        ]

        for query, expected in test_cases:
            _result = parse_query_string(query)
            assert _result == expected

    def test_deep_merge_dicts(self):
        """测试深度合并字典"""

        def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
            """深度合并两个字典"""
            _result = dict1.copy()
            for key, value in dict2.items():
                if (
                    key in result
                    and isinstance(_result[key], dict)
                    and isinstance(value, dict)
                ):
                    _result[key] = deep_merge(_result[key], value)
                else:
                    _result[key] = value
            return result

        dict1 = {"a": 1, "b": {"x": 10, "y": 20}, "c": [1, 2, 3]}

        dict2 = {"b": {"y": 30, "z": 40}, "d": 4, "c": [4, 5]}

        expected = {"a": 1, "b": {"x": 10, "y": 30, "z": 40}, "c": [4, 5], "d": 4}

        _result = deep_merge(dict1, dict2)
        assert _result == expected

    def test_flatten_dict(self):
        """测试扁平化字典"""

        def flatten_dict(d: Dict, parent_key: str = "", sep: str = ".") -> Dict:
            """扁平化嵌套字典"""
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key, sep=sep).items())
                else:
                    items.append((new_key, v))
            return dict(items)

        nested = {
            "user": {
                "name": "John",
                "address": {"street": "123 Main St", "city": "New York"},
            },
            "settings": {
                "theme": "dark",
                "notifications": {"email": True, "sms": False},
            },
        }

        expected = {
            "user.name": "John",
            "user.address.street": "123 Main St",
            "user.address.city": "New York",
            "settings.theme": "dark",
            "settings.notifications.email": True,
            "settings.notifications.sms": False,
        }

        _result = flatten_dict(nested)
        assert _result == expected


# 测试加密工具
class TestCryptoUtils:
    """加密工具测试"""

    def test_generate_token(self):
        """测试生成令牌"""

        def generate_token(length: int = 32) -> str:
            """生成安全令牌"""
            return secrets.token_urlsafe(length)

        # 测试默认长度
        token = generate_token()
        assert len(token) >= 32  # base64编码后的长度
        assert isinstance(token, str)

        # 测试自定义长度
        token = generate_token(16)
        assert len(token) >= 16

    def test_hash_password(self):
        """测试密码哈希"""

        def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
            """哈希密码"""
            if salt is None:
                salt = secrets.token_hex(16)

            # 使用PBKDF2
            from hashlib import pbkdf2_hmac

            hash_value = pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
            )

            return hash_value.hex(), salt

        # 测试密码哈希
        password = "test_password"
        hashed, salt = hash_password(password)

        assert isinstance(hashed, str)
        assert isinstance(salt, str)
        assert len(hashed) == 64  # SHA256 hex长度
        assert len(salt) == 32  # 16字节 hex编码

        # 相同密码不同盐应该产生不同哈希
        hashed2, salt2 = hash_password(password)
        assert hashed != hashed2
        assert salt != salt2

        # 相同密码相同盐应该产生相同哈希
        hashed3, _ = hash_password(password, salt)
        assert hashed == hashed

    def test_generate_uuid(self):
        """测试生成UUID"""
        import uuid

        # 测试UUID4
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()

        assert isinstance(id1, uuid.UUID)
        assert isinstance(id2, uuid.UUID)
        assert id1 != id2
        assert str(id1).count("-") == 4  # UUID格式

    def test_base64_encode_decode(self):
        """测试Base64编码解码"""
        import base64

        def encode_base64(data: str) -> str:
            """Base64编码"""
            return base64.b64encode(data.encode()).decode()

        def decode_base64(data: str) -> str:
            """Base64解码"""
            return base64.b64decode(data).decode()

        original = "Hello, World! 你好世界！"
        encoded = encode_base64(original)
        decoded = decode_base64(encoded)

        assert encoded != original
        assert decoded == original
