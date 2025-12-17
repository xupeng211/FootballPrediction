# 🤝 贡献指南

感谢您对 Football Prediction v2.0 项目的关注！我们欢迎所有形式的贡献，包括但不限于代码提交、问题报告、文档改进和功能建议。

## 📋 目录

- [🏗️ 开发环境设置](#-开发环境设置)
- [🌳 分支管理策略](#-分支管理策略)
- [🔄 Pull Request 流程](#-pull-request-流程)
- [📝 代码规范](#-代码规范)
- [🧪 测试要求](#-测试要求)
- [📚 文档贡献](#-文档贡献)
- [🐛 问题报告](#-问题报告)
- [💡 功能建议](#-功能建议)

## 🏗️ 开发环境设置

### 前置要求

- **Python 3.11+**
- **Docker 20.0+** 和 **Docker Compose 2.0+**
- **Git**

### 快速设置

```bash
# 1. Fork 项目到你的 GitHub 账户
# 然后克隆你的 fork
git clone https://github.com/YOUR_USERNAME/FootballPrediction.git
cd FootballPrediction

# 2. 添加上游仓库
git remote add upstream https://github.com/xupeng211/FootballPrediction.git

# 3. 安装开发依赖
make install

# 4. 设置 pre-commit 钩子
pre-commit install

# 5. 启动开发环境
docker-compose -f docker-compose.dev.yml up -d

# 6. 验证环境
make test
```

### 开发工具配置

推荐使用以下 IDE 和工具：

- **VS Code** + Python 插件 + Docker 插件
- **PyCharm Professional** (内置 Docker 支持)
- **Git CLI** 或 **GitHub Desktop**

## 🌳 分支管理策略

我们采用 **Git Flow** 工作流程：

### 主要分支

| 分支 | 用途 | 保护状态 |
|------|------|----------|
| `main` | 生产就绪代码 | ✅ 严格保护 |
| `develop` | 开发集成分支 | ✅ 严格保护 |

### 功能分支

```bash
# 功能开发分支
git checkout develop
git checkout -b feature/amazing-feature

# 修复分支
git checkout develop
git checkout -b fix/critical-bug

# 发布分支
git checkout develop
git checkout -b release/v2.1.0

# 热修复分支
git checkout main
git checkout -b hotfix/urgent-fix
```

### 分支命名规范

- `feature/功能描述` - 新功能开发
- `fix/问题描述` - Bug 修复
- `docs/文档更新` - 文档改进
- `refactor/重构描述` - 代码重构
- `perf/性能优化` - 性能改进
- `test/测试相关` - 测试相关
- `ci/CI相关` - CI/CD 改进

## 🔄 Pull Request 流程

### 1. 创建 PR

```bash
# 确保你的分支是最新的
git checkout feature/your-feature
git fetch upstream
git rebase upstream/develop

# 运行所有检查
make ci

# 推送到你的 fork
git push origin feature/your-feature

# 在 GitHub 上创建 Pull Request
```

### 2. PR 标题格式

```
类型(范围): 简短描述

详细描述（可选）

相关问题: #123
```

**类型前缀：**
- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `style:` 代码格式（不影响功能）
- `refactor:` 重构
- `perf:` 性能优化
- `test:` 测试相关
- `ci:` CI/CD 相关
- `build:` 构建相关
- `chore:` 其他改动

**示例：**
```
feat(api): 添加批量预测端点

实现 /api/v1/predictions/batch 端点，支持同时预测多场比赛。
包含输入验证、错误处理和性能优化。

相关问题: #45
```

### 3. PR 描述模板

使用我们的 [PR 模板](./.github/PULL_REQUEST_TEMPLATE.md) 来确保信息完整。

### 4. 代码审查

所有 PR 都需要至少一位维护者的审查。审查重点：

- ✅ 代码质量和规范
- ✅ 测试覆盖率
- ✅ 性能影响
- ✅ 安全考虑
- ✅ 文档更新

### 5. 合并要求

PR 合并前必须满足：

- [ ] 所有 CI 检查通过
- [ ] 代码覆盖率 ≥ 80%
- [ ] 至少一个审查者批准
- [ ] 无合并冲突
- [ ] 文档已更新（如需要）

## 📝 代码规范

### Python 代码风格

我们使用以下工具确保代码质量：

```bash
# 代码格式化
make format  # Black + isort

# 代码检查
make lint    # Flake8

# 类型检查
make typecheck  # MyPy

# 安全扫描
make security   # Bandit

# 运行所有检查
make ci
```

### 编码规范

- 遵循 **PEP 8** 和 **PEP 257**
- 使用 **类型注解** (Type Hints)
- 编写 **docstring**（Google 风格）
- 变量和函数使用 **snake_case**
- 类名使用 **PascalCase**
- 常量使用 **UPPER_SNAKE_CASE**

### 代码示例

```python
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class PredictionService:
    """足球预测服务类.

    提供基于机器学习的足球比赛预测功能。

    Attributes:
        model_name: 使用的模型名称
        cache_ttl: 缓存过期时间（秒）
    """

    def __init__(self, model_name: str, cache_ttl: int = 3600) -> None:
        """初始化预测服务.

        Args:
            model_name: 机器学习模型名称
            cache_ttl: 缓存过期时间，默认1小时
        """
        self.model_name = model_name
        self.cache_ttl = cache_ttl

    def predict_match(
        self,
        home_team: str,
        away_team: str,
        match_date: Optional[str] = None
    ) -> Dict[str, float]:
        """预测比赛结果.

        Args:
            home_team: 主队名称
            away_team: 客队名称
            match_date: 比赛日期（可选）

        Returns:
            预测结果字典，包含主胜、平局、客胜概率

        Raises:
            ValueError: 当队名为空时
            ModelLoadError: 当模型加载失败时
        """
        if not home_team or not away_team:
            raise ValueError("队名不能为空")

        logger.info(f"预测比赛: {home_team} vs {away_team}")

        # 实现预测逻辑...
        return {"home_win": 0.6, "draw": 0.3, "away_win": 0.1}
```

## 🧪 测试要求

### 测试结构

```
tests/
├── unit/           # 单元测试
├── integration/    # 集成测试
├── e2e/           # 端到端测试
└── performance/   # 性能测试
```

### 测试编写规范

```python
import pytest
from unittest.mock import Mock, patch
from src.services.inference_service_v2 import InferenceServiceV2

class TestInferenceService:
    """推理服务测试类."""

    @pytest.fixture
    def service(self):
        """创建推理服务实例."""
        return InferenceServiceV2(model_name="test_model")

    def test_predict_match_success(self, service):
        """测试成功预测比赛."""
        result = service.predict_match("Team A", "Team B")

        assert isinstance(result, dict)
        assert "home_win" in result
        assert "draw" in result
        assert "away_win" in result
        assert sum(result.values()) == pytest.approx(1.0)

    def test_predict_match_invalid_input(self, service):
        """测试无效输入."""
        with pytest.raises(ValueError, match="队名不能为空"):
            service.predict_match("", "Team B")

    @patch("src.services.inference_service_v2.ModelLoader")
    def test_predict_with_mock_model(self, mock_loader, service):
        """测试使用模拟模型的预测."""
        mock_model = Mock()
        mock_model.predict.return_value = [0.5, 0.3, 0.2]
        mock_loader.return_value.load_model.return_value = mock_model

        result = service.predict_match("Team A", "Team B")
        assert result["home_win"] == 0.5
```

### 测试覆盖率

- **目标覆盖率**: 80%+
- **新增代码**: 要求 100% 覆盖率
- **关键业务逻辑**: 要求 100% 覆盖率

```bash
# 运行测试并生成覆盖率报告
make coverage

# 查看覆盖率详情
open htmlcov/index.html
```

## 📚 文档贡献

### 文档类型

- **API 文档**: 使用 FastAPI 自动生成的 Swagger 文档
- **代码文档**: 详细的 docstring 和类型注解
- **用户指南**: README.md 和相关文档
- **开发文档**: 架构设计、部署指南等

### 文档编写规范

- 使用 **Markdown** 格式
- 添加适当的 **Emoji** 增强可读性
- 包含 **代码示例** 和 **使用说明**
- 保持文档与代码同步更新

## 🐛 问题报告

### 报告 Bug

使用 [GitHub Issues](https://github.com/xupeng211/FootballPrediction/issues) 报告 Bug，请包含：

1. **问题描述**: 清晰描述遇到的问题
2. **复现步骤**: 详细的重现步骤
3. **期望行为**: 描述期望的正确行为
4. **实际行为**: 描述实际发生的情况
5. **环境信息**: 操作系统、Python 版本、依赖版本
6. **错误日志**: 完整的错误堆栈信息
7. **相关代码**: 最小可复现代码示例

### Bug 报告模板

```markdown
## Bug 描述
简要描述 Bug

## 复现步骤
1. 执行命令 `...`
2. 点击 `...`
3. 滚动到 `...`
4. 看到错误

## 期望行为
清晰简洁地描述期望发生的情况

## 实际行为
清晰简洁地描述实际发生的情况

## 环境信息
- OS: [例如 macOS 13.0]
- Python 版本: [例如 3.11.0]
- 项目版本: [例如 v2.0.0]

## 错误日志
```
粘贴完整的错误日志
```

## 附加信息
添加任何其他有助于解决问题的信息
```

## 💡 功能建议

### 提出建议

我们欢迎功能建议！请先检查 [已有 Issues](https://github.com/xupeng211/FootballPrediction/issues) 避免重复。

### 功能建议模板

```markdown
## 功能描述
清晰简洁地描述你想要的功能

## 问题背景
描述这个功能要解决的问题

## 解决方案
描述你期望的解决方案

## 替代方案
描述你考虑过的其他解决方案

## 附加信息
添加任何其他相关信息或截图
```

## 🎯 贡献类型

我们欢迎以下类型的贡献：

### 💻 代码贡献
- 新功能开发
- Bug 修复
- 性能优化
- 代码重构
- 测试改进

### 📖 文档贡献
- README 改进
- API 文档完善
- 教程和指南
- 代码注释改进

### 🎨 设计贡献
- UI/UX 改进
- Logo 和图标设计
- 文档排版优化

### 🧪 测试贡献
- 单元测试编写
- 集成测试改进
- 性能测试
- 测试环境搭建

## 🏆 贡献者认可

我们重视每一位贡献者：

- **Contributors 列表**: 在 README 中展示所有贡献者
- **Release Notes**: 在版本发布时感谢贡献者
- **社区活动**: 定期举办社区活动和代码审查

## 📞 联系方式

- **GitHub Issues**: [提交问题](https://github.com/xupeng211/FootballPrediction/issues)
- **GitHub Discussions**: [参与讨论](https://github.com/xupeng211/FootballPrediction/discussions)
- **Email**: team@footballprediction.com

## 📄 许可证

通过贡献代码，您同意您的贡献将在 [MIT 许可证](./LICENSE) 下发布。

---

再次感谢您的贡献！🎉

<div align="center">

  <p>💡 <strong>每一个贡献都让项目变得更好</strong></p>

  <p>🤖 <em>Together we build amazing things</em></p>

</div>