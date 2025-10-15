from typing import Any, Dict, List, Optional, Union

"""
装饰器模式API端点
Decorator Pattern API Endpoints

展示装饰器模式的使用和效果。
Demonstrates the usage and effects of the decorator pattern.
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
import asyncio
from requests.exceptions import HTTPError

from ..decorators import DecoratorService
from ..decorators.base import DecoratorContext

router = APIRouter(prefix="/decorators", tags=["装饰器模式"])


# 创建全局装饰器服务实例
global_decorator_service = DecoratorService()


# ==================== 示例函数 ====================


async def example_function_1(x: int, y: int) -> int:
    """示例函数1：简单加法"""
    await asyncio.sleep(0.01)  # 模拟异步操作
    return x + y


async def example_function_2(text: str) -> str:
    """示例函数2：文本处理"""
    await asyncio.sleep(0.02)
    return f"Processed: {text}"


async def failing_function(retry_count: int = 0) -> str:
    """示例函数3：会失败的函数（用于测试重试）"""
    await asyncio.sleep(0.01)
    if retry_count < 2:
        raise ValueError(f"Attempt {retry_count + 1} failed")
    return "Success after retries"


async def slow_function(delay: float = 0.1) -> str:
    """示例函数4：慢速函数（用于测试超时）"""
    await asyncio.sleep(delay)
    return "Completed slowly"


# ==================== 装饰器统计端点 ====================


@router.get("/stats", summary="获取装饰器统计信息")
async def get_decorator_stats(
    function_name: Optional[str] = Query(None, description="函数名称"),
) -> Dict[str, Any]:
    """获取装饰器执行统计信息"""
    if function_name:
        stats = global_decorator_service.get_function_stats(function_name)
        if not stats:
            raise HTTPException(
                status_code=404, detail=f"函数 {function_name} 未找到或未装饰"
            )
        return stats
    else:
        return global_decorator_service.get_all_stats()


@router.post("/stats/clear", summary="清空统计信息")
async def clear_decorator_stats() -> Dict[str, str]:
    """清空所有装饰器的统计信息"""
    global_decorator_service.clear_stats()
    return {"message": "统计信息已清空"}


# ==================== 装饰器演示端点 ====================


@router.get("/demo/logging", summary="日志装饰器演示")
async def demo_logging_decorator(
    input_value: int = Query(..., description="输入值"),
) -> Dict[str, Any]:
    """演示日志装饰器的效果"""
    # 应用日志装饰器
    decorated = global_decorator_service.apply_decorators(
        example_function_1, decorator_names=["default_logging"]
    )

    result = await decorated(input_value, input_value * 2)

    # 获取统计信息
    stats = decorated.get_decorator_stats()

    return {
        "input": input_value,
        "result": result,
        "decorator_stats": stats,
        "message": "查看应用日志以查看装饰器效果",
    }


@router.get("/demo/retry", summary="重试装饰器演示")
async def demo_retry_decorator() -> Dict[str, Any]:
    """演示重试装饰器的效果"""
    # 应用重试装饰器
    decorated = global_decorator_service.apply_decorators(
        failing_function, decorator_names=["default_retry"]
    )

    start_time = datetime.utcnow()
    result = await decorated(retry_count=0)
    end_time = datetime.utcnow()

    # 获取统计信息
    stats = decorated.get_decorator_stats()

    return {
        "result": result,
        "execution_time_seconds": (end_time - start_time).total_seconds(),
        "decorator_stats": stats,
        "message": "函数失败后自动重试",
    }


@router.get("/demo/cache", summary="缓存装饰器演示")
async def demo_cache_decorator(
    input_value: int = Query(..., description="输入值"),
    use_cache: bool = Query(True, description="是否使用缓存"),
) -> Dict[str, Any]:
    """演示缓存装饰器的效果"""
    if use_cache:
        # 应用缓存装饰器
        decorated = global_decorator_service.apply_decorators(
            example_function_1, decorator_names=["default_cache"]
        )
    else:
        # 不使用缓存
        decorated = example_function_1

    # 第一次调用
    start_time = datetime.utcnow()
    result1 = await decorated(input_value, input_value * 2)
    first_call_time = (datetime.utcnow() - start_time).total_seconds()

    # 第二次调用（应该从缓存获取）
    start_time = datetime.utcnow()
    _result2 = await decorated(input_value, input_value * 2)
    second_call_time = (datetime.utcnow() - start_time).total_seconds()

    return {
        "input": input_value,
        "first_call": {
            "result": result1,
            "time_seconds": first_call_time,
        },
        "second_call": {
            "result": result2,
            "time_seconds": second_call_time,
            "from_cache": use_cache and second_call_time < first_call_time / 2,
        },
        "cache_enabled": use_cache,
        "speedup": first_call_time / second_call_time if second_call_time > 0 else 0,
    }


@router.get("/demo/timeout", summary="超时装饰器演示")
async def demo_timeout_decorator(
    delay: float = Query(0.05, ge=0, le=0.2, description="函数延迟时间"),
    timeout_seconds: float = Query(0.1, ge=0.01, le=0.5, description="超时时间"),
) -> Dict[str, Any]:
    """演示超时装饰器的效果"""
    # 创建自定义超时配置
    from ..decorators.factory import DecoratorConfig

    timeout_config = DecoratorConfig(
        name="custom_timeout",
        decorator_type="timeout",
        parameters={"timeout_seconds": timeout_seconds},
    )
    global_decorator_service.register_global_decorator(timeout_config)

    # 应用超时装饰器
    decorated = global_decorator_service.apply_decorators(
        slow_function, decorator_names=["custom_timeout"]
    )

    start_time = datetime.utcnow()

    try:
        result = await decorated(delay)
        success = True
        error_message = None
    except (ValueError, KeyError, AttributeError, HTTPError) as e:
        result = None
        success = False
        error_message = str(e)

    end_time = datetime.utcnow()
    actual_time = (end_time - start_time).total_seconds()

    return {
        "delay_seconds": delay,
        "timeout_seconds": timeout_seconds,
        "actual_time_seconds": actual_time,
        "success": success,
        "result": result,
        "error_message": error_message,
        "timed_out": not success and actual_time >= timeout_seconds,
    }


@router.get("/demo/metrics", summary="指标装饰器演示")
async def demo_metrics_decorator(
    iterations: int = Query(10, ge=1, le=100, description="执行次数"),
) -> Dict[str, Any]:
    """演示指标装饰器的效果"""
    # 应用指标装饰器
    decorated = global_decorator_service.apply_decorators(
        example_function_2, decorator_names=["default_metrics"]
    )

    # 执行多次
    results = []
    for i in range(iterations):
        result = await decorated(f"iteration_{i}")
        results.append(result)

    # 获取统计信息
    stats = decorated.get_decorator_stats()

    return {
        "iterations": iterations,
        "results_count": len(results),
        "sample_results": results[:3],  # 只显示前3个结果
        "decorator_stats": stats,
        "message": "指标装饰器收集了每次执行的统计数据",
    }


@router.get("/demo/combo", summary="组合装饰器演示")
async def demo_combo_decorators(
    input_value: int = Query(..., description="输入值"),
) -> Dict[str, Any]:
    """演示多个装饰器组合使用的效果"""
    # 应用多个装饰器
    decorated = global_decorator_service.apply_decorators(
        example_function_1,
        decorator_names=[
            "default_logging",
            "default_metrics",
            "default_timeout",
            "default_cache",
        ],
    )

    # 第一次调用
    start_time = datetime.utcnow()
    result1 = await decorated(input_value, input_value * 2)
    first_time = (datetime.utcnow() - start_time).total_seconds()

    # 第二次调用（应该从缓存获取）
    start_time = datetime.utcnow()
    _result2 = await decorated(input_value, input_value * 2)
    second_time = (datetime.utcnow() - start_time).total_seconds()

    # 获取所有装饰器的统计信息
    all_stats = decorated.get_decorator_stats()

    return {
        "input": input_value,
        "results": [result1, result2],
        "execution_times": {
            "first_call": first_time,
            "second_call": second_time,
            "speedup": first_time / second_time if second_time > 0 else 0,
        },
        "decorator_count": len(all_stats["decorators"]),
        "decorator_stats": all_stats,
        "message": "同时应用了日志、指标、超时和缓存装饰器",
    }


# ==================== 装饰器配置管理 ====================


@router.get("/configs", summary="获取装饰器配置")
async def get_decorator_configs() -> Dict[str, Any]:
    """获取所有装饰器配置"""
    factory = global_decorator_service.factory

    configs = {}
    for name in factory.list_configs():
        config = factory.get_config(name)
        if config:
            configs[name] = {
                "type": config.decorator_type,
                "enabled": config.enabled,
                "priority": config.priority,
                "parameters": config.parameters,
            }

    chains = {}
    for name in factory.list_chain_configs():
        chain = factory.get_chain_config(name)
        if chain:
            chains[name] = {
                "target_functions": chain.target_functions,
                "global": chain.is_global,
                "decorator_count": len(chain.decorators),
            }

    return {
        "decorators": configs,
        "chains": chains,
        "global_decorators": len(global_decorator_service._global_decorators),
        "function_decorators": len(global_decorator_service._function_decorators),
    }


@router.post("/reload", summary="重新加载装饰器配置")
async def reload_decorator_configs() -> Dict[str, str]:
    """重新加载装饰器配置"""
    global_decorator_service.reload_configuration()
    return {"message": "装饰器配置已重新加载"}


# ==================== 装饰器上下文演示 ====================


@router.get("/demo/context", summary="装饰器上下文演示")
async def demo_decorator_context(
    step_count: int = Query(3, ge=1, le=10, description="执行步骤数"),
) -> Dict[str, Any]:
    """演示装饰器上下文的传递"""
    # 创建上下文
    context = DecoratorContext()
    context.set("user_id", "demo_user")
    context.set("request_id", "req_12345")

    # 创建装饰器函数，它会使用上下文
    async def context_aware_function(
        x: int, decorator_context: Optional[DecoratorContext] = None
    ) -> Dict[str, Any]:
        if decorator_context:
            decorator_context.add_execution_step("context_aware_function")
            decorator_context.set("processing_step", x)

        await asyncio.sleep(0.01)
        return {
            "value": x * 2,
            "user_id": decorator_context.get("user_id") if decorator_context else None,
            "request_id": decorator_context.get("request_id")
            if decorator_context
            else None,
        }

    # 应用装饰器
    decorated = global_decorator_service.apply_decorators(
        context_aware_function, decorator_names=["default_logging"]
    )

    # 执行多次，传递同一个上下文
    results = []
    for i in range(step_count):
        result = await decorated(i + 1, decorator_context=context)
        results.append(result)

    return {
        "context_info": context.to_dict(),
        "step_count": step_count,
        "results": results,
        "execution_path": context.execution_path,
        "total_time": context.get_execution_time(),
    }
