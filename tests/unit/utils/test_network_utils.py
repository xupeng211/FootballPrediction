"""
网络工具测试
"""

import urllib.parse
from typing import Any, Dict, List, Optional

import pytest


class NetworkUtils:
    """网络工具类"""

    @staticmethod
    def build_url(
        base_url: str, path: str = "", params: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建URL"""
        url = base_url.rstrip("/")
        if path:
            url += "/" + path.lstrip("/")

        if params:
            query_string = urllib.parse.urlencode(params)
            url += "?" + query_string

        return url

    @staticmethod
    def parse_url(url: str) -> Dict[str, Any]:
        """解析URL"""
        parsed = urllib.parse.urlparse(url)
        return {
            "scheme": parsed.scheme,
            "netloc": parsed.netloc,
            "path": parsed.path,
            "params": parsed.params,
            "query": parsed.query,
            "fragment": parsed.fragment,
            "hostname": parsed.hostname,
            "port": parsed.port,
            "username": parsed.username,
            "password": parsed.password,
        }

    @staticmethod
    def get_status_code_description(status_code: int) -> str:
        """获取HTTP状态码描述"""
        status_codes = {
            100: "Continue",
            101: "Switching Protocols",
            200: "OK",
            201: "Created",
            202: "Accepted",
            204: "No Content",
            301: "Moved Permanently",
            302: "Found",
            304: "Not Modified",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            409: "Conflict",
            422: "Unprocessable Entity",
            429: "Too Many Requests",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout",
        }
        return status_codes.get(status_code, "Unknown")

    @staticmethod
    def is_success_status(status_code: int) -> bool:
        """判断是否为成功状态码"""
        return 200 <= status_code < 300

    @staticmethod
    def is_client_error(status_code: int) -> bool:
        """判断是否为客户端错误"""
        return 400 <= status_code < 500

    @staticmethod
    def is_server_error(status_code: int) -> bool:
        """判断是否为服务器错误"""
        return 500 <= status_code < 600

    @staticmethod
    def is_redirect_status(status_code: int) -> bool:
        """判断是否为重定向状态码"""
        return 300 <= status_code < 400

    @staticmethod
    def parse_content_type(content_type: str) -> Dict[str, str]:
        """解析Content-Type头"""
        parts = content_type.split(";")
        _result = {"type": parts[0].strip()}

        for part in parts[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                _result[key.strip()] = value.strip().strip('"')

        return result

    @staticmethod
    def encode_base64(data: str) -> str:
        """Base64编码"""
        import base64

        return base64.b64encode(data.encode()).decode()

    @staticmethod
    def decode_base64(encoded_data: str) -> str:
        """Base64解码"""
        import base64

        return base64.b64decode(encoded_data).decode()

    @staticmethod
    def build_query_string(params: Dict[str, Any]) -> str:
        """构建查询字符串"""
        return urllib.parse.urlencode(params)

    @staticmethod
    def parse_query_string(query_string: str) -> Dict[str, List[str]]:
        """解析查询字符串"""
        return urllib.parse.parse_qs(query_string)

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """清理文件名中的URL编码字符"""
        return urllib.parse.unquote(filename)

    @staticmethod
    def get_mime_type(file_extension: str) -> str:
        """根据文件扩展名获取MIME类型"""
        mime_types = {
            ".txt": "text/plain",
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".xml": "application/xml",
            ".pdf": "application/pdf",
            ".zip": "application/zip",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".mp4": "video/mp4",
            ".mp3": "audio/mpeg",
        }
        return mime_types.get(file_extension.lower(), "application/octet-stream")

    @staticmethod
    def format_bytes(bytes_count: int) -> str:
        """格式化字节数为可读格式"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"

    @staticmethod
    def is_valid_port(port: int) -> bool:
        """验证端口号是否有效"""
        return 0 < port <= 65535

    @staticmethod
    def is_valid_ip(ip: str) -> bool:
        """简单的IP地址验证"""
        import re

        ipv4_pattern =
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        return bool(re.match(ipv4_pattern, ip))

    @staticmethod
    def get_common_ports() -> Dict[int, str]:
        """获取常用端口号及其服务"""
        return {
            20: "FTP Data",
            21: "FTP Control",
            22: "SSH",
            23: "Telnet",
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            110: "POP3",
            143: "IMAP",
            443: "HTTPS",
            993: "IMAPS",
            995: "POP3S",
            3306: "MySQL",
            5432: "PostgreSQL",
            6379: "Redis",
            8080: "HTTP Alternate",
        }


@pytest.mark.unit
@pytest.mark.external_api
class TestNetworkUtils:
    """测试网络工具类"""

    def test_build_url_basic(self):
        """测试基本URL构建"""
        url = NetworkUtils.build_url("http://example.com")
        assert url == "http://example.com"

    def test_build_url_with_path(self):
        """测试带路径的URL构建"""
        url = NetworkUtils.build_url("http://example.com", "api/users")
        assert url == "http://example.com/api/users"

    def test_build_url_with_params(self):
        """测试带参数的URL构建"""
        params = {"page": 1, "limit": 10}
        url = NetworkUtils.build_url("http://example.com", "api/users", params)
        assert "page=1" in url
        assert "limit=10" in url

    def test_build_url_with_all(self):
        """测试完整的URL构建"""
        params = {"q": "test", "lang": "en"}
        url = NetworkUtils.build_url("https://api.example.com/", "search/", params)
        assert url == "https://api.example.com/search/?q=test&lang=en"

    def test_parse_url(self):
        """测试URL解析"""
        url = "https://user:pass@example.com:8080/path/to/file?query=value#fragment"
        parsed = NetworkUtils.parse_url(url)

        assert parsed["scheme"] == "https"
        assert parsed["netloc"] == "user:pass@example.com:8080"
        assert parsed["path"] == "/path/to/file"
        assert parsed["query"] == "query=value"
        assert parsed["fragment"] == "fragment"
        assert parsed["hostname"] == "example.com"
        assert parsed["port"] == 8080
        assert parsed["username"] == "user"
        assert parsed["password"] == "pass"

    def test_get_status_code_description(self):
        """测试HTTP状态码描述"""
        assert NetworkUtils.get_status_code_description(200) == "OK"
        assert NetworkUtils.get_status_code_description(404) == "Not Found"
        assert NetworkUtils.get_status_code_description(500) == "Internal Server Error"
        assert NetworkUtils.get_status_code_description(999) == "Unknown"

    def test_is_success_status(self):
        """测试成功状态码判断"""
        assert NetworkUtils.is_success_status(200) is True
        assert NetworkUtils.is_success_status(201) is True
        assert NetworkUtils.is_success_status(199) is False
        assert NetworkUtils.is_success_status(300) is False
        assert NetworkUtils.is_success_status(404) is False

    def test_is_client_error(self):
        """测试客户端错误判断"""
        assert NetworkUtils.is_client_error(400) is True
        assert NetworkUtils.is_client_error(404) is True
        assert NetworkUtils.is_client_error(499) is True
        assert NetworkUtils.is_client_error(399) is False
        assert NetworkUtils.is_client_error(500) is False

    def test_is_server_error(self):
        """测试服务器错误判断"""
        assert NetworkUtils.is_server_error(500) is True
        assert NetworkUtils.is_server_error(502) is True
        assert NetworkUtils.is_server_error(499) is False
        assert NetworkUtils.is_server_error(600) is False

    def test_is_redirect_status(self):
        """测试重定向状态码判断"""
        assert NetworkUtils.is_redirect_status(301) is True
        assert NetworkUtils.is_redirect_status(302) is True
        assert NetworkUtils.is_redirect_status(299) is False
        assert NetworkUtils.is_redirect_status(400) is False

    def test_parse_content_type(self):
        """测试Content-Type解析"""
        ct = "text/html; charset=utf-8; boundary=something"
        parsed = NetworkUtils.parse_content_type(ct)

        assert parsed["type"] == "text/html"
        assert parsed["charset"] == "utf-8"
        assert parsed["boundary"] == "something"

    def test_parse_content_type_simple(self):
        """测试简单Content-Type解析"""
        ct = "application/json"
        parsed = NetworkUtils.parse_content_type(ct)

        assert parsed["type"] == "application/json"
        assert len(parsed) == 1

    def test_encode_decode_base64(self):
        """测试Base64编码解码"""
        original = "Hello, World! 测试"
        encoded = NetworkUtils.encode_base64(original)
        decoded = NetworkUtils.decode_base64(encoded)

        assert encoded != original
        assert decoded == original

    def test_build_query_string(self):
        """测试构建查询字符串"""
        params = {"name": "John", "age": 30, "city": "Beijing"}
        query = NetworkUtils.build_query_string(params)

        assert "name=John" in query
        assert "age=30" in query
        assert "city=Beijing" in query

    def test_parse_query_string(self):
        """测试解析查询字符串"""
        query = "name=John&age=30&hobby=reading&hobby=coding"
        parsed = NetworkUtils.parse_query_string(query)

        assert parsed["name"] == ["John"]
        assert parsed["age"] == ["30"]
        assert parsed["hobby"] == ["reading", "coding"]

    def test_sanitize_filename(self):
        """测试清理文件名"""
        filename = "file%20name%20with%20spaces.txt"
        sanitized = NetworkUtils.sanitize_filename(filename)
        assert sanitized == "file name with spaces.txt"

    def test_get_mime_type(self):
        """测试获取MIME类型"""
        assert NetworkUtils.get_mime_type(".txt") == "text/plain"
        assert NetworkUtils.get_mime_type(".json") == "application/json"
        assert NetworkUtils.get_mime_type(".png") == "image/png"
        assert NetworkUtils.get_mime_type(".unknown") == "application/octet-stream"

    def test_format_bytes(self):
        """测试格式化字节数"""
        assert NetworkUtils.format_bytes(512) == "512.0 B"
        assert NetworkUtils.format_bytes(1536) == "1.5 KB"
        assert NetworkUtils.format_bytes(1048576) == "1.0 MB"
        assert NetworkUtils.format_bytes(1073741824) == "1.0 GB"

    def test_is_valid_port(self):
        """测试验证端口号"""
        assert NetworkUtils.is_valid_port(80) is True
        assert NetworkUtils.is_valid_port(443) is True
        assert NetworkUtils.is_valid_port(65535) is True
        assert NetworkUtils.is_valid_port(0) is False
        assert NetworkUtils.is_valid_port(-1) is False
        assert NetworkUtils.is_valid_port(65536) is False

    def test_is_valid_ip(self):
        """测试验证IP地址"""
        assert NetworkUtils.is_valid_ip("192.168.1.1") is True
        assert NetworkUtils.is_valid_ip("0.0.0.0") is True
        assert NetworkUtils.is_valid_ip("255.255.255.255") is True
        assert NetworkUtils.is_valid_ip("256.256.256.256") is False
        assert NetworkUtils.is_valid_ip("192.168.1") is False
        assert NetworkUtils.is_valid_ip("not.an.ip") is False

    def test_get_common_ports(self):
        """测试获取常用端口"""
        ports = NetworkUtils.get_common_ports()

        assert 80 in ports
        assert 443 in ports
        assert 3306 in ports
        assert ports[80] == "HTTP"
        assert ports[443] == "HTTPS"
        assert ports[3306] == "MySQL"

    def test_build_url_with_leading_trailing_slashes(self):
        """测试URL构建时的斜杠处理"""
        url = NetworkUtils.build_url("http://example.com/", "/api/users/")
        assert url == "http://example.com/api/users"

    def test_build_query_string_with_special_chars(self):
        """测试构建包含特殊字符的查询字符串"""
        params = {"q": "test search", "lang": "zh-CN"}
        query = NetworkUtils.build_query_string(params)

        # URL编码后的结果
        assert "test+search" in query or "test%20search" in query
        assert "lang=zh-CN" in query
