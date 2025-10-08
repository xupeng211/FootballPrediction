# 🤝 贡献指南

感谢您对 FootballPrediction 项目的关注！我们欢迎所有形式的贡献，包括但不限于：

- 🐛 Bug 报告
- 💡 功能建议
- 📝 文档改进
- 🔧 代码提交
- 🧪 测试用例
- 🎨 UI/UX 改进

## 开始之前

在开始贡献之前，请：

1. **阅读项目文档**
   - [项目 README](README.md)
   - [架构文档](docs/ARCHITECTURE.md)
   - [部署指南](docs/DEPLOYMENT.md)

2. **搜索现有 Issue**
   - 查看是否已有相关的 [Issue](https://github.com/xupeng211/FootballPrediction/issues)
   - 避免重复提交

3. **了解项目规范**
   - 代码风格（使用 Ruff）
   - 提交信息格式（遵循 Conventional Commits）
   - 分支管理（Git Flow）

## 开发环境搭建

### 1. Fork 并克隆项目

```bash
# Fork 项目到您的 GitHub 账户
# 然后克隆您的 fork

git clone https://github.com/YOUR_USERNAME/FootballPrediction.git
cd FootballPrediction

# 添加上游仓库
git remote add upstream https://github.com/xupeng211/FootballPrediction.git
```

### 2. 设置开发环境

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
make install

# 安装 pre-commit hooks
pre-commit install
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置必要的环境变量
# 注意：可以使用测试值进行开发
```

## 开发流程

### 1. 创建功能分支

```bash
# 确保主分支是最新的
git checkout main
git pull upstream main

# 创建功能分支
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/issue-number-description
```

### 2. 进行开发

- 遵循项目的代码规范
- 编写清晰的注释和文档字符串
- 为新功能添加测试
- 确保所有测试通过

```bash
# 运行测试
make test

# 运行 linting
make lint

# 检查类型
make type-check
```

### 3. 提交代码

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

类型说明：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

示例：
```
feat(api): add batch prediction endpoint

Add support for predicting multiple matches in a single request.
This improves performance when processing large numbers of matches.

Closes #123
```

### 4. 推送并创建 PR

```bash
# 推送到您的 fork
git push origin feature/your-feature-name

# 创建 Pull Request
# 访问 GitHub 页面创建 PR
```

## Pull Request 指南

### PR 标题格式

使用清晰的标题，包含相关的 Issue 编号：

```
[PR] Add feature description (#123)
```

### PR 描述模板

```markdown
## 📝 描述
简要描述这个 PR 的目的和所做的更改。

## 🔗 相关 Issue
Closes #(issue number)

## 📋 更改类型
- [ ] Bug 修复
- [ ] 新功能
- [ ] 重构
- [ ] 文档更新
- [ ] 性能优化
- [ ] 其他：____

## ✅ 检查清单
- [ ] 代码遵循项目的代码规范
- [ ] 添加了必要的测试
- [ ] 所有测试通过
- [ ] 更新了相关文档
- [ ] 没有合并冲突
- [ ] 通过了 CI 检查

## 📸 截图（如适用）
如果您的更改涉及 UI 更改，请添加截图。

## 🧪 测试步骤
描述如何测试您的更改：
1. 步骤一
2. 步骤二
3. 预期结果

## 💬 其他信息
任何审查者需要知道的信息。
```

## 代码规范

### Python 代码风格

项目使用 **Ruff** 进行代码格式化和 linting：

```bash
# 自动修复
ruff check --fix .

# 格式化
ruff format .
```

主要规范：
- 最大行长度：88 字符
- 使用双引号
- 使用类型注解
- 遵循 PEP 8

### 命名规范

- **变量/函数**：snake_case
- **类**：PascalCase
- **常量**：UPPER_SNAKE_CASE
- **私有成员**：前缀下划线 `_`

### 文档字符串

使用 Google 风格的文档字符串：

```python
def calculate_prediction_confidence(predictions: List[Prediction]) -> float:
    """计算预测的置信度。

    Args:
        predictions: 预测结果列表

    Returns:
        置信度分数，范围 0-1

    Raises:
        ValueError: 当预测列表为空时
    """
    pass
```

## 测试指南

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/unit/test_predictions.py

# 运行带覆盖率的测试
pytest --cov=src --cov-report=html

# 运行特定标记的测试
pytest -m "not slow"  # 跳过慢速测试
```

### 编写测试

- 使用 pytest 框架
- 使用 fixture 管理测试数据
- Mock 外部依赖
- 测试边界条件和错误情况

```python
import pytest
from unittest.mock import Mock, patch

class TestPredictionService:
    def test_predict_match_success(self):
        """测试成功预测比赛"""
        # Given
        service = PredictionService()
        match_id = "test_match_123"

        # When
        result = service.predict_match(match_id)

        # Then
        assert result is not None
        assert result.prediction in ["home_win", "draw", "away_win"]
        assert 0 <= result.confidence <= 1
```

## 📚 文档规范

为保持文档质量，请遵循以下规范：

1. **必须通过 Docs Guard 检查**
   - 本地执行：
     ```bash
     make docs.check
     ```

2. **文档目录结构**
   - 只允许以下顶层目录：
     `architecture/`, `how-to/`, `reference/`, `testing/`, `data/`, `ml/`, `ops/`, `release/`, `staging/`, `legacy/`, `_reports/`, `_meta/`
   - 其他目录会被自动拒绝。

3. **孤儿文档处理**
   - 所有新文档必须添加到 `INDEX.md` 或在现有文档中有引用。

4. **坏链防护**
   - 外部链接可用 `http(s)`。
   - 内部相对链接必须指向实际存在文件。

5. **归档策略**
   - 过时或历史文档请放入 `legacy/`。

## 报告 Bug

使用以下模板报告 Bug：

```
**Bug 描述**
简要描述遇到的问题。

**复现步骤**
1. 执行命令 '...'
2. 点击 '....'
3. 滚动到 '....'
4. 看到错误

**预期行为**
描述您期望发生的情况。

**实际行为**
描述实际发生的情况。

**环境信息**
- OS: [e.g. Ubuntu 20.04]
- Python 版本: [e.g. 3.11.9]
- 项目版本: [e.g. v1.2.0]

**附加信息**
添加任何其他有助于解决问题的信息。
```

## 提出功能建议

使用以下模板提出新功能：

```
**功能描述**
简要描述您希望添加的功能。

**问题背景**
描述这个功能要解决的问题。

**解决方案**
描述您设想的实现方案。

**替代方案**
描述您考虑过的其他方案。

**附加信息**
添加任何其他相关信息或截图。
```

## 发布流程

项目使用语义化版本控制（SemVer）：

- **主版本号**：不兼容的 API 修改
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

发布步骤：
1. 更新版本号
2. 更新 CHANGELOG.md
3. 创建 Git 标签
4. 构建和发布

## 获得帮助

如果您需要帮助：

1. 查看 [文档](docs/)
2. 搜索 [Issues](https://github.com/xupeng211/FootballPrediction/issues)
3. 创建新的 Issue
4. 在讨论区提问

## 行为准则

请尊重所有项目参与者，保持友善和专业。我们不容忍：

- 骚扰或歧视行为
- 人身攻击
- 恶意破坏
- 侵犯隐私

违规者将被警告，严重者将被禁止参与项目。

## 贡献者认可

所有贡献者都会在 README.md 中被认可。感谢您的贡献！

## 许可证

通过贡献代码，您同意您的贡献将在 [MIT License](LICENSE) 下发布。

---

再次感谢您的贡献！🎉
