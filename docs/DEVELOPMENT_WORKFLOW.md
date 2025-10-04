# 开发工作流程

## 概述

本文档描述了FootballPrediction项目的标准开发工作流程和最佳实践。

## 开发环境设置

### 初始设置

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/FootballPrediction.git
cd FootballPrediction

# 2. 创建虚拟环境
make venv

# 3. 安装依赖
make install

# 4. 安装pre-commit hooks
pre-commit install

# 5. 配置环境变量
cp .env.example .env
# 编辑.env文件，填入实际配置

# 6. 验证环境
make env-check
```

### 推荐的IDE配置

#### VSCode

创建`.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/unit"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

#### PyCharm

1. 设置Python解释器：`.venv/bin/python`
2. 启用Pytest作为测试运行器
3. 配置Black作为格式化工具
4. 启用MyPy类型检查

## Git工作流

### 分支策略

```
main (生产)
  ↑
develop (开发)
  ↑
feature/xxx (功能分支)
```

### 创建功能分支

```bash
# 从develop创建新分支
git checkout develop
git pull origin develop
git checkout -b feature/add-new-prediction-model

# 开发你的功能
# ...

# 提交更改
git add .
git commit -m "feat: 添加新的预测模型"

# 推送到远程
git push origin feature/add-new-prediction-model
```

### 提交消息规范

遵循[Conventional Commits](https://www.conventionalcommits.org/)规范：

```bash
# 格式
<type>(<scope>): <subject>

<body>

<footer>

# 类型(type)
feat:     新功能
fix:      修复bug
docs:     文档更新
style:    代码格式（不影响代码运行）
refactor: 重构
test:     测试相关
chore:    构建过程或辅助工具

# 示例
feat(api): 添加预测端点
fix(database): 修复连接池泄漏
docs(readme): 更新安装说明
refactor(utils): 简化字符串处理逻辑
test(api): 增加健康检查测试
```

### Code Review检查清单

提交PR前确保：

- [ ] 所有测试通过 (`make test`)
- [ ] 代码覆盖率达标 (`make coverage`)
- [ ] Lint检查通过 (`make lint`)
- [ ] Pre-commit hooks通过
- [ ] 更新了相关文档
- [ ] 添加了测试用例
- [ ] 提交消息符合规范

## 开发流程

### 1. 编写代码

```python
# src/api/new_endpoint.py
from fastapi import APIRouter

router = APIRouter(tags=["new-feature"])

@router.get("/new-endpoint")
async def new_endpoint():
    """新端点描述"""
    return {"status": "ok"}
```

### 2. 编写测试

```python
# tests/unit/api/test_new_endpoint.py
import pytest

def test_new_endpoint(api_client):
    """测试新端点"""
    response = api_client.get("/api/new-endpoint")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

### 3. 运行测试

```bash
# 运行新测试
pytest tests/unit/api/test_new_endpoint.py -v

# 运行所有测试
make test

# 检查覆盖率
make coverage
```

### 4. 代码质量检查

```bash
# 格式化代码
ruff format src/ tests/

# Lint检查
ruff check src/ tests/

# 类型检查
mypy src/

# 或使用make命令
make lint
```

### 5. 提交代码

```bash
# 添加文件
git add .

# 提交（会自动运行pre-commit hooks）
git commit -m "feat(api): 添加新端点"

# 如果hooks失败，修复问题后重新提交
```

## 测试驱动开发(TDD)

### TDD流程

1. **红色阶段**：先写测试，测试失败
```python
def test_new_feature():
    result = new_feature()
    assert result == expected
```

2. **绿色阶段**：实现功能，让测试通过
```python
def new_feature():
    return expected
```

3. **重构阶段**：优化代码，保持测试通过
```python
def new_feature():
    # 优化后的实现
    return calculate_result()
```

### 示例：TDD开发新功能

```python
# 1. 写测试 (红色)
def test_calculate_win_probability():
    """测试胜率计算"""
    prob = calculate_win_probability(
        home_team="Man Utd",
        away_team="Liverpool"
    )
    assert 0 <= prob <= 1
    assert isinstance(prob, float)

# 2. 实现功能 (绿色)
def calculate_win_probability(home_team, away_team):
    """计算胜率"""
    # 简单实现
    return 0.5

# 3. 重构 (保持绿色)
def calculate_win_probability(home_team, away_team):
    """计算胜率 - 优化版"""
    home_stats = get_team_stats(home_team)
    away_stats = get_team_stats(away_team)
    return calculate_probability(home_stats, away_stats)
```

## 持续集成

### GitHub Actions工作流

代码推送后自动触发：

1. **Lint检查**
   - Ruff linting
   - MyPy类型检查

2. **测试**
   - 单元测试
   - 集成测试
   - 覆盖率检查

3. **构建**
   - Docker镜像构建
   - 镜像推送到registry

### 本地CI模拟

```bash
# 运行完整CI流程
make ci

# 或使用脚本
./ci-verify.sh

# 这会依次运行：
# - lint检查
# - 类型检查
# - 测试
# - 覆盖率检查
```

## 调试技巧

### 使用IPython调试

```python
# 在代码中插入断点
import IPython; IPython.embed()

# 运行时会在此处暂停
# 可以交互式检查变量
```

### 使用pdb

```python
import pdb

def problematic_function():
    # 设置断点
    pdb.set_trace()

    # 调试命令
    # n: 下一行
    # s: 步入函数
    # c: 继续执行
    # p var: 打印变量
    # q: 退出
```

### 使用pytest调试

```bash
# 失败时进入pdb
pytest --pdb

# 显示print输出
pytest -s

# 详细输出
pytest -vv

# 只运行失败的测试
pytest --lf
```

### 日志调试

```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def debug_function():
    logger.debug("进入函数")
    logger.info(f"处理数据: {data}")
    logger.warning("注意: 性能可能较慢")
    logger.error("发生错误", exc_info=True)
```

## 性能优化

### 性能分析

```bash
# 使用cProfile
python -m cProfile -s cumulative src/main.py > profile.txt

# 使用make命令
make profile-app

# 分析内存使用
make profile-memory
```

### 优化建议

1. **数据库查询优化**
```python
# ❌ N+1查询问题
for match in matches:
    team = db.get_team(match.team_id)

# ✅ 批量查询
team_ids = [m.team_id for m in matches]
teams = db.get_teams(team_ids)
```

2. **缓存使用**
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def expensive_calculation(param):
    # 耗时计算
    return result
```

3. **异步优化**
```python
# ❌ 串行执行
result1 = await api_call_1()
result2 = await api_call_2()

# ✅ 并行执行
result1, result2 = await asyncio.gather(
    api_call_1(),
    api_call_2()
)
```

## 依赖管理

### 添加新依赖

```bash
# 1. 添加到requirements.txt
echo "new-package==1.0.0" >> requirements/base.txt

# 2. 安装
pip install new-package

# 3. 锁定依赖
make lock-deps

# 4. 提交更改
git add requirements/
git commit -m "chore: 添加new-package依赖"
```

### 更新依赖

```bash
# 检查过时的包
pip list --outdated

# 更新特定包
pip install --upgrade package-name

# 更新并锁定
make lock-deps

# 验证没有破坏性变更
make test
```

## 数据库迁移

### 创建迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "添加新表"

# 查看SQL
alembic upgrade head --sql

# 应用迁移
alembic upgrade head
```

### 回滚迁移

```bash
# 回滚一个版本
alembic downgrade -1

# 回滚到特定版本
alembic downgrade <revision_id>
```

## 故障排查

### 常见问题

#### 导入错误

```bash
# 确保PYTHONPATH正确
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"

# 或在pytest中
pytest --import-mode=importlib
```

#### 数据库连接失败

```bash
# 检查数据库状态
docker-compose ps

# 查看日志
docker-compose logs db

# 重启服务
docker-compose restart db
```

#### 测试失败

```bash
# 查看详细错误
pytest -vv --tb=long

# 只运行失败的测试
pytest --lf

# 查看慢速测试
pytest --durations=10
```

## 代码审查指南

### 审查者检查清单

- [ ] 代码逻辑正确
- [ ] 有适当的测试覆盖
- [ ] 遵循项目编码规范
- [ ] 没有明显的性能问题
- [ ] 错误处理完善
- [ ] 日志记录适当
- [ ] 文档和注释清晰
- [ ] 没有安全漏洞

### 提交者准备清单

- [ ] 自己先review一遍代码
- [ ] 确保CI通过
- [ ] 更新相关文档
- [ ] 添加测试用例
- [ ] 清理调试代码
- [ ] 检查commit历史是否清晰

## 发布流程

### 版本号规范

使用[语义化版本](https://semver.org/)：`MAJOR.MINOR.PATCH`

- MAJOR: 不兼容的API变更
- MINOR: 向后兼容的功能新增
- PATCH: 向后兼容的bug修复

### 发布步骤

```bash
# 1. 更新版本号
# 编辑 pyproject.toml 或 __version__.py

# 2. 更新CHANGELOG
# 添加新版本的变更记录

# 3. 创建tag
git tag -a v1.2.3 -m "Release version 1.2.3"
git push origin v1.2.3

# 4. 触发CI/CD
# GitHub Actions会自动构建和部署
```

## 资源链接

- [项目README](../README.md)
- [贡献指南](../CONTRIBUTING.md)
- [API文档](./API_DOCUMENTATION.md)
- [测试指南](./TESTING_GUIDE.md)
- [代码示例](./CODE_EXAMPLES.md)

## 获取帮助

- **Slack**: #football-prediction
- **邮件**: dev-team@example.com
- **Issues**: GitHub Issues
- **Wiki**: 项目Wiki

---

**记住**: 好的代码是写给人读的，恰好能被机器执行。
