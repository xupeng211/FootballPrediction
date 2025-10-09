"""
"""



    """


    """



    """






    """

        """

        """


        """







        """


        """处理成功调用 / Handle successful call"""

        """处理失败调用 / Handle failed call"""


        """

        """


        """

        """

        """

        """

        """

        """

        """

        """

        """

        """


        from src.utils.retry import CircuitBreaker
            from src.utils.retry import CircuitBreaker
import asyncio
import time

熔断器实现
Circuit Breaker Implementation
class CircuitState(Enum):
    熔断器状态枚举 / Circuit Breaker State Enumeration
    定义熔断器的三种状态。
    Defines the three states of a circuit breaker.
    States:
        CLOSED: 熔断器关闭，允许请求通过 / Circuit breaker closed, allowing requests
        OPEN: 熔断器打开，阻止请求 / Circuit breaker open, blocking requests
        HALF_OPEN: 熔断器半开，试探性允许请求 / Circuit breaker half-open, tentatively allowing requests
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
class CircuitBreaker:
    熔断器实现 / Circuit Breaker Implementation
    实现熔断器模式，防止级联故障。
    Implements the circuit breaker pattern to prevent cascading failures.
    Attributes:
        failure_threshold (int): 失败阈值 / Failure threshold
        recovery_timeout (float): 恢复超时（秒） / Recovery timeout (seconds)
        retry_timeout (float): 重试超时（秒） / Retry timeout (seconds)
        failure_count (int): 失败计数 / Failure count
        last_failure_time (Optional[float]): 最后失败时间 / Last failure time
        state (CircuitState): 当前状态 / Current state
        lock (asyncio.Lock): 异步锁 / Async lock
    Example:
        ```python
        # 创建熔断器
        circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            retry_timeout=30.0
        )
        # 使用熔断器调用函数
        try:
            result = await circuit_breaker.call(external_service_call, arg1, arg2)
        except Exception as e:
            print(f"服务调用被熔断: {e}")
        ```
    Note:
        熔断器在OPEN状态下会阻止所有请求，防止对已知故障的服务继续调用。
        The circuit breaker blocks all requests in OPEN state to prevent continued calls to known faulty services.
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        retry_timeout: float = 30.0,
    ):
        初始化熔断器 / Initialize circuit breaker
        Args:
            failure_threshold (int): 失败阈值，超过此值熔断器打开 /
                                   Failure threshold, circuit breaker opens after this many failures
                Defaults to 5
            recovery_timeout (float): 恢复超时（秒），熔断器打开后等待此时间尝试恢复 /
                                    Recovery timeout (seconds), time to wait before attempting recovery after opening
                Defaults to 60.0
            retry_timeout (float): 重试超时（秒），半开状态下等待此时间再次尝试 /
                                 Retry timeout (seconds), time to wait in half-open state before retrying
                Defaults to 30.0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.retry_timeout = retry_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.lock = asyncio.Lock()
    async def call(self, func: Callable, *args, **kwargs) -> any:
        使用熔断器调用函数 / Call function with circuit breaker
        Args:
            func (Callable): 要调用的函数 / Function to call
            *args: 函数参数 / Function arguments
            **kwargs: 函数关键字参数 / Function keyword arguments
        Returns:
            Any: 函数调用结果 / Function call result
        Raises:
            Exception: 当熔断器打开时抛出异常 / Raised when circuit breaker is open
            Exception: 当函数调用失败时抛出异常 / Raised when function call fails
        Example:
            ```python
            circuit_breaker = CircuitBreaker()
            async def external_api_call():
                # 外部API调用
                pass
            try:
                result = await circuit_breaker.call(external_api_call)
                print(f"调用成功: {result}")
            except Exception as e:
                print(f"调用失败或被熔断: {e}")
            ```
        async with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise Exception("熔断器已打开 / Circuit breaker is OPEN")
            try:
                result = await func(*args, **kwargs)
                await self._on_success()
                return result
            except Exception:
                await self._on_failure()
                raise
    async def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    async def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    def _should_attempt_reset(self) -> bool:
        检查是否应该尝试重置熔断器 / Check if circuit should attempt to reset
        Returns:
            bool: 如果应该尝试重置则返回True / True if should attempt reset
        if self.last_failure_time is None:
            return False
        time_since_failure = time.time() - self.last_failure_time
        timeout = (
            self.retry_timeout
            if self.state == CircuitState.HALF_OPEN
            else self.recovery_timeout
        )
        return time_since_failure >= timeout
    def get_state(self) -> CircuitState:
        获取当前熔断器状态 / Get current circuit breaker state
        Returns:
            CircuitState: 当前状态 / Current state
        return self.state
    def get_failure_count(self) -> int:
        获取当前失败计数 / Get current failure count
        Returns:
            int: 失败次数 / Number of failures
        return self.failure_count
    def reset(self):
        手动重置熔断器状态 / Manually reset circuit breaker state
        将熔断器重置为关闭状态，清零失败计数。
        Resets the circuit breaker to closed state and clears failure count.
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    async def force_open(self):
        强制打开熔断器 / Force open the circuit breaker
        手动将熔断器设置为打开状态。
        Manually sets the circuit breaker to open state.
        async with self.lock:
            self.state = CircuitState.OPEN
            self.last_failure_time = time.time()
    async def force_close(self):
        强制关闭熔断器 / Force close the circuit breaker
        手动将熔断器设置为关闭状态并重置计数。
        Manually sets the circuit breaker to closed state and resets count.
        async with self.lock:
            self.reset()