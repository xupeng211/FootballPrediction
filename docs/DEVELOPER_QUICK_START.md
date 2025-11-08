# 开发者快速上手指南

## 🚀 5分钟快速启动

### 环境准备

```bash
# 1️⃣ 克隆项目
git clone <repository-url>
cd FootballPrediction

# 2️⃣ 环境设置
make install && make env-check

# 3️⃣ 智能修复（解决80%环境问题）
python3 scripts/smart_quality_fixer.py

# 4️⃣ 验证环境
make test.unit
```

### 🎯 核心开发流程

```bash
# 开发前检查
make ci-check

# 开发过程中
make fix-code          # 代码修复
make test.unit        # 运行测试
make coverage         # 检查覆盖率

# 提交前
make prepush          # 完整验证
```

## 🏗️ 项目架构概览

### 核心技术栈
- **后端**: FastAPI + SQLAlchemy 2.0 + Redis + PostgreSQL
- **架构**: DDD + CQRS + 依赖注入 + 事件驱动
- **测试**: pytest + asyncio + 47种标准化标记
- **工具**: Ruff + MyPy + Black + 自动化脚本

### 项目结构

```
src/
├── api/             # FastAPI路由和API层
├── core/            # 核心模块（DI、事件、配置）
├── domain/          # 领域驱动设计
│   ├── entities/    # 业务实体
│   ├── services/    # 领域服务
│   └── strategies/  # 业务策略
├── services/        # 应用服务层
├── database/        # 数据访问层
├── cache/           # Redis缓存
├── ml/              # 机器学习模块
├── utils/           # 工具函数
└── monitoring/      # 性能监控
```

## 🛠️ 开发工具链

### 必备工具

```bash
# 代码质量工具
ruff check src/ tests/ --fix          # 代码检查和修复
ruff format src/ tests/               # 代码格式化
mypy src/                             # 类型检查
bandit -r src/                        # 安全检查

# 测试工具
pytest tests/unit/utils/ -v          # 单元测试
pytest -m "unit and critical" -v     # 关键功能测试
make coverage                         # 覆盖率报告

# 智能修复工具
python3 scripts/smart_quality_fixer.py  # 一键修复
make solve-test-crisis                 # 测试危机修复
```

### IDE配置

#### VSCode配置 (.vscode/settings.json)

```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "python.testing.unittestEnabled": false,
    "files.exclude": {
        "**/__pycache__": true,
        "**/htmlcov": true,
        "**/.pytest_cache": true
    }
}
```

#### PyCharm配置

```bash
# 设置Python解释器
File → Settings → Project → Python Interpreter → Add → Existing Environment
选择: ./.venv/bin/python

# 启用pytest
File → Settings → Tools → Python Integrated Tools → Testing → pytest

# 配置代码检查
File → Settings → Tools → External Tools → Add Ruff
```

## 🧪 测试驱动开发

### Smart Tests (推荐)

```bash
# 核心稳定测试组合，执行时间<2分钟，通过率>90%
pytest tests/unit/utils tests/unit/cache tests/unit/core -v --maxfail=20
```

### 按功能域测试

```bash
# API测试
pytest -m "api and critical" -v

# 业务逻辑测试
pytest -m "domain or services" -v

# 数据库测试
pytest -m "database" -v

# 缓存测试
pytest -m "cache" -v
```

### 单个文件测试

```bash
# 正确方式（不加覆盖率阈值）
pytest tests/unit/utils/test_date_utils.py::test_format_date_iso -v

# 查看覆盖率详情
pytest tests/unit/utils/ --cov=src.utils --cov-report=term-missing -v
```

## 📝 代码质量最佳实践

### 1. 提交前检查

```bash
make prepush
```

包含：
- 代码格式化 (Black + isort)
- 代码质量检查 (Ruff)
- 类型检查 (MyPy)
- 安全检查 (bandit)
- 单元测试验证
- 覆盖率检查

### 2. 智能修复优先

```bash
# 优先使用智能修复工具
python3 scripts/smart_quality_fixer.py

# 手动修复作为补充
make fix-code
```

### 3. 渐进式改进

```bash
# 查看当前状态
make check-quality
make coverage

# 问题修复
make syntax-fix          # 语法错误
make security-fix        # 安全问题
make quality-improve     # 质量提升
```

## 🔧 常见开发任务

### 添加新API端点

1. **定义路由** (`src/api/routes/`)
```python
from fastapi import APIRouter, Depends
from src.core.di import get_service

router = APIRouter(prefix="/api/v1/example", tags=["example"])

@router.post("/")
async def create_example(
    data: ExampleCreate,
    service = Depends(get_service)
):
    return await service.create_example(data)
```

2. **添加服务层** (`src/services/`)
```python
class ExampleService:
    async def create_example(self, data: ExampleCreate) -> Example:
        # 业务逻辑
        pass
```

3. **编写测试** (`tests/unit/api/`)
```python
@pytest.mark.api
def test_create_example_success(client):
    response = client.post("/api/v1/example/", json={
        "name": "test"
    })
    assert response.status_code == 201
```

### 添加新领域服务

1. **定义实体** (`src/domain/entities/`)
```python
from sqlalchemy import Column, Integer, String
from src.database.base import BaseModel

class Example(BaseModel):
    __tablename__ = "examples"

    name = Column(String(100), nullable=False)
```

2. **实现领域服务** (`src/domain/services/`)
```python
class ExampleDomainService:
    def validate_example_data(self, data: dict) -> bool:
        # 领域规则验证
        return True
```

### 添加缓存逻辑

```python
from src.cache.decorators import cache_result

@cache_result(ttl=300)
async def expensive_operation(param: str) -> dict:
    # 耗时操作
    return {"result": "computed"}
```

## 🐛 调试技巧

### 测试调试

```bash
# 详细输出
pytest tests/unit/core/test_di.py -v -s

# 停在第一个失败
pytest -x

# 进入调试器
pytest tests/unit/core/test_di.py::test_container_resolve --pdb

# 只运行失败的测试
pytest --lf
```

### 代码调试

```python
# 使用项目日志
from src.core.logger import get_logger
logger = get_logger(__name__)

def debug_function():
    logger.info("开始执行函数")
    result = some_operation()
    logger.debug(f"操作结果: {result}")
    return result
```

### 性能分析

```bash
# 查看最慢的测试
pytest --durations=10

# 代码性能分析
python -m cProfile -o profile.stats src/main.py
python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative')
p.print_stats(10)
"
```

## 📊 监控和分析

### 代码质量监控

```bash
# 质量趋势分析
make quality-guardian
make test-coverage-monitor

# 综合报告
make report-quality
```

### 性能监控

```python
from src.monitoring.metrics import track_performance

@track_performance
async def monitored_function():
    # 被监控的函数
    pass
```

## 🚀 部署准备

### 本地开发环境

```bash
# 启动开发服务器
make dev

# 启动完整服务栈
make up    # app + db + redis + nginx
```

### 环境配置

```bash
# 创建环境文件
make create-env

# 验证环境
make env-check

# 环境变量示例 (.env)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
DEBUG=true
```

### Docker开发

```bash
# 构建开发镜像
docker-compose build

# 运行开发环境
docker-compose up

# 容器中运行测试
docker-compose exec app make test.unit
```

## 🔗 关键文档链接

### 核心文档
- [系统架构指南](./architecture/CORE_ARCHITECTURE_GUIDE.md)
- [测试综合指南](./TESTING_COMPREHENSIVE_GUIDE.md)
- [API文档](./API_REFERENCE.md)
- [部署指南](./DEPLOYMENT_COMPREHENSIVE_GUIDE.md)

### 开发指南
- [代码规范](./CODING_STANDARDS.md)
- [Git工作流](./GIT_WORKFLOW.md)
- [代码审查](./CODE_REVIEW_STANDARDS.md)

### 运维指南
- [生产环境就绪](./PRODUCTION_READINESS_ASSESSMENT.md)
- [监控指南](./ops/monitoring.md)
- [故障处理](./ops/runbooks/README.md)

## 🆘 获取帮助

### 常见问题解决

```bash
# 环境问题
make clean && make install && make test.unit

# 测试失败
make solve-test-crisis
python3 scripts/smart_quality_fixer.py

# 代码质量问题
make fix-code
make ci-auto-fix

# 性能问题
make performance-check
```

### 联系方式

- **文档问题**: 提交GitHub Issue
- **技术问题**: 查看相关文档或搜索codebase
- **Bug报告**: 使用GitHub Issues模板

## 📈 开发效率提升

### 快捷命令

```bash
# 创建别名（添加到 .bashrc 或 .zshrc）
alias ft='pytest tests/unit/utils/ -v'  # 快速测试
alias qc='make check-quality'          # 质量检查
alias fx='make fix-code'               # 快速修复
alias tc='make test.coverage'          # 测试覆盖率
```

### 开发模板

```python
# 新API端点模板
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v1/resource", tags=["resource"])

@router.post("/")
async def create_resource(data: ResourceCreate):
    # TODO: 实现创建逻辑
    pass

@router.get("/{resource_id}")
async def get_resource(resource_id: int):
    # TODO: 实现获取逻辑
    pass
```

```python
# 新测试模板
import pytest

class TestResource:
    @pytest.mark.unit
    def test_create_resource_success(self):
        # Arrange
        # TODO: 准备测试数据

        # Act
        # TODO: 执行操作

        # Assert
        # TODO: 验证结果
        assert True
```

---

## 🎉 开发者资源

### 学习资源
- [FastAPI官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0文档](https://docs.sqlalchemy.org/)
- [pytest文档](https://docs.pytest.org/)

### 工具文档
- [Ruff文档](https://docs.astral.sh/ruff/)
- [Black文档](https://black.readthedocs.io/)
- [MyPy文档](https://mypy.readthedocs.io/)

---

*文档版本: v1.0 | 最后更新: 2025-11-08 | 维护者: Claude Code*