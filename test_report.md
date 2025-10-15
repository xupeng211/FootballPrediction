# 综合测试报告

**测试时间**: 2025-10-14 20:38:42

## 测试摘要

| 指标 | 值 |
|------|----|
| 总测试数 | 6 |
| 通过数 | 0 |
| 失败数 | 6 |
| 成功率 | 0.0% |

## 详细结果

### unit_tests

- **状态**: ❌ 失败
- **描述**: 单元测试 - utils模块
- **耗时**: 1.95秒

**错误信息**:
```
/home/user/projects/FootballPrediction/.venv/lib/python3.11/site-packages/pytest_asyncio/plugin.py:208: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Va
...
```

### lint_check

- **状态**: ❌ 失败
- **描述**: 代码质量检查 - ruff
- **耗时**: 0.06秒

### type_check

- **状态**: ❌ 失败
- **描述**: 类型检查 - MyPy
- **耗时**: 0.40秒

### coverage

- **状态**: ❌ 失败
- **描述**: 测试覆盖率
- **耗时**: 2.12秒

**错误信息**:
```
/home/user/projects/FootballPrediction/.venv/lib/python3.11/site-packages/pytest_asyncio/plugin.py:208: PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.
The event loop scope for asynchronous fixtures will default to the fixture caching scope. Future versions of pytest-asyncio will default the loop scope for asynchronous fixtures to function scope. Set the default fixture loop scope explicitly in order to avoid unexpected behavior in the future. Va
...
```

### cache_test

- **状态**: ❌ 失败
- **描述**: 缓存功能测试
- **耗时**: 0.01秒

**错误信息**:
```
Traceback (most recent call last):
  File "/home/user/projects/FootballPrediction/src/utils/cached_operations.py", line 9, in <module>
    from typing import Dict, List, Optional
  File "/home/user/.pyenv/versions/3.11.9/lib/python3.11/typing.py", line 24, in <module>
    from collections import defaultdict
ImportError: cannot import name 'defaultdict' from 'collections' (/home/user/projects/FootballPrediction/src/utils/collections/__init__.py)

```

### redis

- **状态**: ❌ 失败
- **描述**: Redis不可用: No module named 'src'
- **耗时**: 0.00秒

