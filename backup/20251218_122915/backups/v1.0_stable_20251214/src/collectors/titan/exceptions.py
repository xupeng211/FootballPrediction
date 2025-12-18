"""
Titan007 采集器异常定义

定义所有与 Titan007 数据采集中可能遇到的异常情况。
"""


class TitanError(Exception):
    """
    Titan007 采集器基类异常

    所有 Titan007 相关异常的基类。
    """

    def __init__(self, message: str, endpoint: str = None, params: dict = None):
        """
        初始化异常

        Args:
            message: 错误消息
            endpoint: 请求的API端点
            params: 请求参数
        """
        self.endpoint = endpoint
        self.params = params
        super().__init__(self._format_message(message))

    def _format_message(self, message: str) -> str:
        """格式化错误消息"""
        context = []
        if self.endpoint:
            context.append(f"endpoint='{self.endpoint}'")
        if self.params:
            context.append(f"params={self.params}")

        if context:
            return f"{message} ({', '.join(context)})"
        return message


class TitanNetworkError(TitanError):
    """
    网络请求异常

    当 HTTP 请求失败时抛出（超时、连接错误、5xx错误等）。
    """

    def __init__(
        self,
        message: str,
        status_code: int = None,
        endpoint: str = None,
        params: dict = None,
    ):
        """
        初始化网络错误

        Args:
            message: 错误消息
            status_code: HTTP状态码 (如果有)
            endpoint: 请求的API端点
            params: 请求参数
        """
        self.status_code = status_code
        super().__init__(message, endpoint, params)


class TitanParsingError(TitanError):
    """
    数据解析异常

    当响应内容无法正确解析时抛出（JSON解析失败、JSONP格式、BOM头等）。
    """

    def __init__(
        self,
        message: str,
        raw_content: str = None,
        endpoint: str = None,
        params: dict = None,
    ):
        """
        初始化解析错误

        Args:
            message: 错误消息
            raw_content: 原始响应内容 (用于调试)
            endpoint: 请求的API端点
            params: 请求参数
        """
        self.raw_content = raw_content
        super().__init__(message, endpoint, params)


class TitanScrapingError(TitanError):
    """
    反爬拦截异常

    当请求被目标网站的反爬机制拦截时抛出（403 Forbidden、验证码等）。
    """

    def __init__(
        self,
        message: str,
        status_code: int = 403,
        endpoint: str = None,
        params: dict = None,
    ):
        """
        初始化反爬错误

        Args:
            message: 错误消息
            status_code: HTTP状态码 (通常是403)
            endpoint: 请求的API端点
            params: 请求参数
        """
        self.status_code = status_code
        super().__init__(message, endpoint, params)


class TitanRateLimitError(TitanError):
    """
    限流异常

    当请求触发目标网站的限流策略时抛出（429 Too Many Requests）。
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = None,
        endpoint: str = None,
        params: dict = None,
    ):
        """
        初始化限流错误

        Args:
            message: 错误消息
            retry_after: 建议重试等待时间（秒）
            endpoint: 请求的API端点
            params: 请求参数
        """
        self.retry_after = retry_after
        super().__init__(message, endpoint, params)


class TitanAuthenticationError(TitanError):
    """
    认证异常

    当请求缺少或持有无效认证信息时抛出（401 Unauthorized）。
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        endpoint: str = None,
        params: dict = None,
    ):
        """
        初始化认证错误

        Args:
            message: 错误消息
            endpoint: 请求的API端点
            params: 请求参数
        """
        super().__init__(message, endpoint, params)
