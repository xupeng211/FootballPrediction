# 测试驱动开发（TDD）指南

## 概述

测试驱动开发是一种软件开发方法论，要求在编写生产代码之前先编写测试。本文档介绍如何在FootballPrediction项目中实施TDD。

## TDD循环

### Red-Green-Refactor 循环

1. **Red** - 编写一个失败的测试
   - 确保测试真正失败（而不是因为语法错误）
   - 确保错误消息清晰明确

2. **Green** - 编写最少的代码让测试通过
   - 只写刚好能通过测试的代码
   - 不要过度设计

3. **Refactor** - 重构代码保持测试通过
   - 改进代码质量
   - 保持测试一直通过

## TDD示例

### 示例1：创建新的工具函数

#### Step 1 - Red：编写失败的测试

```python
# tests/unit/utils/test_calculator.py
import pytest
from src.utils.calculator import Calculator

class TestCalculator:
    def test_add_two_numbers(self):
        """测试两个数字相加"""
        calculator = Calculator()
        result = calculator.add(2, 3)
        assert result == 5

    def test_add_negative_numbers(self):
        """测试负数相加"""
        calculator = Calculator()
        result = calculator.add(-5, -3)
        assert result == -8
```

运行测试：`pytest tests/unit/utils/test_calculator.py -v`
预期结果：失败（因为Calculator类还不存在）

#### Step 2 - Green：实现最少的代码

```python
# src/utils/calculator.py
class Calculator:
    def add(self, a, b):
        return a + b
```

运行测试：`pytest tests/unit/utils/test_calculator.py -v`
预期结果：通过

#### Step 3 - Refactor：改进代码（如果需要）

```python
# src/utils/calculator.py
from typing import Union

class Calculator:
    """简单的计算器工具类"""

    def add(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """
        两个数字相加

        Args:
            a: 第一个数字
            b: 第二个数字

        Returns:
            相加的结果
        """
        return a + b

    def subtract(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """两个数字相减"""
        return a - b
```

### 示例2：创建API端点

#### Step 1 - Red：编写失败的测试

```python
# tests/unit/api/test_health.py
import pytest
from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)

def test_health_check():
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

#### Step 2 - Green：实现端点

```python
# src/api/health.py
from fastapi import APIRouter

router = APIRouter(prefix="/health")

@router.get("")
async def health_check():
    return {"status": "healthy"}

# 在 main.py中注册路由
app.include_router(health_router, tags=["health"])
```

#### Step 3 - Refactor：改进实现

```python
# src/api/health.py
from fastapi import APIRouter
from datetime import datetime
from src.core.config import get_settings

router = APIRouter(prefix="/health")

@router.get("")
async def health_check():
    """健康检查端点"""
    settings = get_settings()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.get("version", "unknown"),
        "environment": settings.get("environment", "unknown")
    }
```

## TDD最佳实践

### 1. 测试命名
- 使用描述性的测试名称
- 遵循 `test_<功能>_<场景>_<期望>` 格式
- 测试名称应该像文档一样易读

### 2. 小步前进
- 一次只实现一个功能
- 每个测试关注一个场景
- 保持测试简单专注

### 3. 测试隔离
- 每个测试独立运行
- 不依赖其他测试的状态
- 使用fixtures提供测试数据

### 4. 先写断言
- 在编写实现代码前，先定义期望结果
- 断言应该清晰明确
- 使用有意义的错误消息

## 在项目中实施TDD

### 1. 选择合适的测试级别

#### 单元测试（70%）
- 工具函数
- 业务逻辑
- 数据模型

#### 集成测试（20%）
- 数据库交互
- API交互
- 服务间通信

#### 端到端测试（10%）
- 用户流程
- 关键业务场景

### 2. 建立TDD工作流

#### 开发新功能时：
1. **需求分析**
   ```
   用户故事：用户可以查看比赛列表
   验收标准：
   - 显示即将开始的比赛
   - 可以按日期筛选
   - 显示比赛状态
   ```

2. **编写测试**
   ```python
   def test_get_upcoming_matches():
       """测试获取即将开始的比赛"""
       # 创建测试数据
       # 调用API
       # 验证结果
   ```

3. **实现功能**
   ```python
   async def get_upcoming_matches(date_filter=None):
       # 查询数据库
       # 过滤数据
       # 返回结果
   ```

4. **重构优化**
   - 添加错误处理
   - 优化查询性能
   - 改进代码结构

### 3. 代码审查清单

#### 提交前的检查：
- [ ] 所有测试通过
- [ ] 代码覆盖率达标
- [ ] 代码符合规范
- [ ] 文档已更新

#### 代码审查重点：
- 测试是否充分
- 实现是否简单
- 是否有重复代码
- 错误处理是否完善

## TDD工具和技巧

### 1. 测试工具
- **pytest**: 主要测试框架
- **pytest-mock**: Mock和stub
- **pytest-cov**: 覆盖率
- **factory-boy**: 测试数据工厂
- **faker**: 生成假数据

### 2. IDE支持
- **PyCharm**: 内置TDD支持
- **VS Code**: Python扩展支持

### 3. 快捷键
- 运行测试：`Ctrl+Shift+F10`
- 调试测试：`Shift+F9`
- 跳转到测试：`Ctrl+Click`

## 常见陷阱和解决方案

### 1. 过度设计
**问题**：编写过多代码
**解决**：保持YAGNI原则（You Aren't Gonna Need It）

### 2. 测试脆弱
**问题**：测试经常因为无关改动而失败
**解决**：
- 使用稳定的测试数据
- 避免依赖实现细节
- 使用接口而非具体类

### 3. 测试覆盖不足
**问题**：只测试正常路径
**解决**：
- 测试边界条件
- 测试错误情况
- 测试边缘值

### 4. Mock过度使用
**问题**：Mock太多导致测试虚假
**解决**：
- 只Mock外部依赖
- 优先使用真实实现
- 集成测试验证Mock

## TDD和敏捷开发

### 1. 用户故事和TDD
```
作为一个用户，我想要查看比赛积分榜，
以便了解各队排名。

TDD步骤：
1. 编写测试验证积分榜显示
2. 实现积分榜查询
3. 实现积分排序逻辑
4. 添加分页功能
5. 实现筛选功能
```

### 2. 迭代开发
- 每个迭代都有可工作的软件
- 测试确保质量
- 重构保持代码健康

## 总结

TDD不仅仅是测试技术，更是一种设计方法论。通过TDD，我们可以：
- 提高代码质量
- 减少缺陷
- 增强信心
- 改进设计

记住：TDD需要练习和耐心，但长期收益巨大！