# ⚽ FootballPrediction CLI 使用指南

## 📖 版本说明

- **🆕 v2.0 版本** (推荐): [CLI_使用指南_v2.md](./CLI_使用指南_v2.md) - 新架构，功能更强
- **📚 v1.x 版本** (历史): 本文档 - 传统版本，保持兼容

---

## 🚀 v2.0 CLI 工具 (推荐)

### 🎯 核心工具

- **`predict_match_v2.py`** - 基于新架构的主要预测工具
- **`docker-manager.sh`** - Docker 管理和部署工具

### 🎮 快速开始

```bash
# 推荐方式：使用 Docker 一键部署
./scripts/docker-manager.sh dev

# 本地开发：安装依赖后运行
make install && make dev
```

### 📊 主要功能

```bash
# 🎯 基础预测
python scripts/predict_match_v2.py --home "Manchester United" --away "Arsenal"

# 📊 批量预测
python scripts/predict_match_v2.py --batch matches.json

# 🤖 模型管理
python scripts/predict_match_v2.py --list-models
python scripts/predict_match_v2.py --home "Team A" --away "Team B" --model xgboost_v2

# 🐳 Docker 管理
./scripts/docker-manager.sh build
./scripts/docker-manager.sh up
./scripts/docker-manager.sh health
```

**详细文档**: 👉 查看 [CLI_使用指南_v2.md](./CLI_使用指南_v2.md)

---

## 📚 v1.x CLI 工具 (历史版本)

> ⚠️ **重要**: 此为历史版本，建议升级到 v2.0 以获得更好的功能和性能。

### 🎯 历史工具

- **`predict_match_legacy.py`** (原 `predict_match.py`) - v1.x 预测工具

### 🚀 v1.x 基本用法

```bash
# 使用历史版本
python scripts/predict_match_legacy.py --home "Arsenal" --away "Chelsea"

# 简化语法
python scripts/predict_match_legacy.py -H "Man United" -A "Liverpool"

# 指定日期
python scripts/predict_match_legacy.py -H "PSG" -A "Lyon" -d "2024-01-15"

# 详细输出
python scripts/predict_match_legacy.py -H "Bayern" -A "Dortmund" --verbose
```

### 📊 v1.x 输出示例

```bash
🏟️  比赛: Manchester United vs Arsenal
📅  日期: 2024-01-15

📊 预测概率:
主胜      :  58.69% |███████████████████████████░░░|
平局      :  22.15% |█████████████░░░░░░░░░░░░░░░|
客胜      :  19.16% |█████████░░░░░░░░░░░░░░░░░░|

💡 投注建议: 💰 推荐: HOME_WIN (置信度 58.69%)
📈 模型版本: xgboost_v1
```

---

## 🔄 迁移指南

### 📋 从 v1.x 升级到 v2.0

#### 1. 工具迁移
```bash
# v1.x (旧)
python scripts/predict_match.py --home "Team A" --away "Team B"

# v2.0 (新)
python scripts/predict_match_v2.py --home "Team A" --away "Team B"
```

#### 2. 功能升级对比

| 功能 | v1.x | v2.0 | 说明 |
|------|-------|-------|------|
| **预测引擎** | 单模型 | 多模型支持 | 支持模型选择 |
| **批量预测** | 不支持 | ✅ 支持 | 批量处理多场比赛 |
| **API 集成** | 不支持 | ✅ 支持 | REST API 接口 |
| **缓存系统** | 无 | ✅ LRU缓存 | 提升预测速度 |
| **模型解释** | 无 | ✅ SHAP分析 | 特征重要性 |
| **部署方式** | 手动 | ✅ Docker | 容器化部署 |
| **性能监控** | 无 | ✅ 健康检查 | 实时监控 |

#### 3. 命令行参数对比

| 参数 | v1.x | v2.0 | 说明 |
|------|-------|-------|------|
| `--home` | ✅ | ✅ | 主队名称 |
| `--away` | ✅ | ✅ | 客队名称 |
| `--date` | ✅ | ✅ | 比赛日期 |
| `--verbose` | ✅ | ✅ | 详细日志 |
| `--model` | ❌ | ✅ | 模型选择 (v2.0新增) |
| `--batch` | ❌ | ✅ | 批量预测 (v2.0新增) |
| `--format` | ❌ | ✅ | 输出格式 (v2.0新增) |
| `--save` | ❌ | ✅ | 保存结果 (v2.0新增) |
| `--list-models` | ❌ | ✅ | 模型列表 (v2.0新增) |

#### 4. 输出格式升级

**v1.x 输出**:
```
🎯 预测概率:
主胜      : 58.69%
平局      : 22.15%
客胜      : 19.16%
```

**v2.0 输出** (JSON/CSV/Table):
```json
{
  "match_id": 123456,
  "prediction": "HOME_WIN",
  "probabilities": [0.5869, 0.2215, 0.1916],
  "confidence": 0.5869,
  "model_version": "xgboost_v2",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 🔄 数据格式迁移

#### 批量预测文件格式

**v1.x**: 不支持批量预测

**v2.0 JSON 格式**:
```json
{
  "matches": [
    {
      "home_team": "Manchester United",
      "away_team": "Arsenal",
      "match_date": "2024-01-15"
    }
  ]
}
```

**v2.0 CSV 格式**:
```csv
home_team,away_team,match_date
Manchester United,Arsenal,2024-01-15
Chelsea,Liverpool,2024-01-15
```

---

## 🔧 高级功能对比

### 🤖 API 集成

**v1.x**: 独立 CLI 工具

**v2.0**: REST API + CLI 双模式
```bash
# CLI 模式
python scripts/predict_match_v2.py --home "Team A" --away "Team B"

# API 模式
curl -X POST http://localhost:8000/api/v1/predictions \
  -H "Content-Type: application/json" \
  -d '{"home_team": "Team A", "away_team": "Team B"}'
```

### 🐳 部署方式

**v1.x**: 本地 Python 环境

**v2.0**: 完整容器化
```bash
# v1.x 手动部署
pip install -r requirements.txt
python scripts/predict_match.py --home "A" --away "B"

# v2.0 一键部署
./scripts/docker-manager.sh build
./scripts/docker-manager.sh up
```

---

## 🛠️ 故障排除

### 🔍 常见迁移问题

#### 1. 找不到 v2.0 脚本
```bash
# 错误: FileNotFoundError
# 解决方案: 检查文件是否存在
ls -la scripts/predict_match_v2.py

# 如果不存在，确保使用正确的 v2.0 版本
```

#### 2. 参数不兼容
```bash
# v1.x 参数 (某些在 v2.0 中已废弃)
python scripts/predict_match_legacy.py --legacy-param

# v2.0 新参数
python scripts/predict_match_v2.py --new-param value
```

#### 3. 输出格式变化
```bash
# v1.x 固定格式输出
python scripts/predict_match_legacy.py

# v2.0 可定制格式
python scripts/predict_match_v2.py --format json
python scripts/predict_match_v2.py --format csv
python scripts/predict_match_v2.py --format table
```

### 🚀 性能差异

**v1.x**:
- 响应时间: ~300ms
- 内存使用: 较高
- 无缓存机制

**v2.0**:
- 响应时间: ~100ms (3x 提升)
- 内存使用: 优化减少 40%
- LRU缓存命中率: >80%

---

## 📚 更多资源

### 📖 相关文档

- **🆕 v2.0 CLI 指南**: [CLI_使用指南_v2.md](./CLI_使用指南_v2.md) - 推荐使用
- **📚 README 主文档**: [README.md](./README.md)
- **🎯 v2.0 发布说明**: [RELEASE_NOTES.md](./RELEASE_NOTES.md)
- **🔧 开发指南**: [CLAUDE.md](./CLAUDE.md)

### 🔗 快速链接

```bash
# 查看 v2.0 功能
python scripts/predict_match_v2.py --help
./scripts/docker-manager.sh --help

# 访问 v2.0 API 文档
curl http://localhost:8000/docs
```

---

**🎯 选择建议**:
- 🆕 **新项目**: 直接使用 v2.0 工具
- 📚 **现有项目**: 逐步迁移到 v2.0，享受新功能
- 🔧 **学习用途**: 对比两个版本，了解技术演进

---

**🎊 FootballPrediction CLI 工具 - 从 v1.x 到 v2.0，持续进化！**