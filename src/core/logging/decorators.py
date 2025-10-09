"""
日志装饰器
Logging Decorators
"""




def log_performance(operation: str, logger: Optional[StructuredLogger] = None):
    """性能监控装饰器"""

    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                log = logger or get_logger(func.__module__, LogCategory.PERFORMANCE)
                log.performance(
                    operation=operation,
                    duration=duration,
                    success=success,
                    function=func.__name__,
                    module=func.__module__,
                )

        return wrapper

    return decorator


def log_async_performance(operation: str, logger: Optional[StructuredLogger] = None):
    """异步性能监控装饰器"""

    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                log = logger or get_logger(func.__module__, LogCategory.PERFORMANCE)
                log.performance(
                    operation=operation,
                    duration=duration,
                    success=success,
                    function=func.__name__,
                    module=func.__module__,
                )

        return wrapper

    return decorator


def log_audit(action: str, logger: Optional[StructuredLogger] = None):
    """审计日志装饰器"""

    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            log = logger or get_logger(func.__module__, LogCategory.AUDIT)
            # 尝试从kwargs或args中提取用户ID
            user_id = kwargs.get("user_id") or (


                args[0]
                if args and isinstance(args[0], dict) and "user_id" in args[0]
                else None
            )

            log.audit(
                action=action,
                user_id=user_id,
                function=func.__name__,
                module=func.__module__,
            )

            return func(*args, **kwargs)

        return wrapper

    return decorator