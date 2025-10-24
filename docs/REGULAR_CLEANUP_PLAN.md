# 🗓️ 项目定期清理计划

## 📋 清理目标
保持项目根目录整洁，避免临时文件和报告堆积，提升开发效率。

## 🔄 清理周期建议

### 📅 每日清理 (轻量级)
**时间**: 每天下班前5分钟
**命令**:
```bash
# 清理缓存 (可选，根据需要)
# rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/ .cache/

# 删除当天的临时改进报告
# rm -f improvement-report-$(date +%Y%m%d)*.md

# 整理临时脚本到正确位置
# mv *.py scripts/temp/ 2>/dev/null || true
```

### 📅 每周清理 (标准)
**时间**: 每周五下午
**脚本**: `./scripts/weekly_cleanup.sh`

```bash
#!/bin/bash
# 每周清理脚本

echo "🧹 开始每周项目清理..."

# 1. 创建本周归档目录
WEEK_DIR="archive/$(date +%Y-%W)"
mkdir -p $WEEK_DIR/{reports,coverage,temp}

# 2. 移动本周临时报告
find . -maxdepth 1 -name "*_REPORT.md" -mtime -7 -exec mv {} $WEEK_DIR/reports/ \; 2>/dev/null || true
find . -maxdepth 1 -name "*_SUMMARY.md" -mtime -7 -exec mv {} $WEEK_DIR/reports/ \; 2>/dev/null || true

# 3. 移动覆盖率数据
find . -maxdepth 1 -name "coverage*.json" -mtime -7 -exec mv {} $WEEK_DIR/coverage/ \; 2>/dev/null || true
find . -maxdepth 1 -name "coverage*.xml" -mtime -7 -exec mv {} $WEEK_DIR/coverage/ \; 2>/dev/null || true

# 4. 清理缓存
rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/ .cache/

# 5. 删除临时文件
find . -maxdepth 1 -name "*_temp*" -mtime -7 -delete 2>/dev/null || true
find . -maxdepth 1 -name "*_backup*" -mtime -7 -delete 2>/dev/null || true
find . -maxdepth 1 -name "*.log" -mtime -7 -delete 2>/dev/null || true

echo "✅ 每周清理完成！"
```

### 📅 每月清理 (深度)
**时间**: 每月最后一天
**脚本**: `./scripts/monthly_cleanup.sh`

```bash
#!/bin/bash
# 每月清理脚本

echo "🧹 开始每月深度清理..."

# 1. 执行每周清理
./scripts/weekly_cleanup.sh

# 2. 创建月度归档
MONTH_DIR="archive/$(date +%Y-%m)"
mkdir -p $MONTH_DIR/{reports,coverage,temp,old}

# 3. 移动所有剩余的临时报告
find . -maxdepth 1 -name "*REPORT*.md" -exec mv {} $MONTH_DIR/reports/ \; 2>/dev/null || true
find . -maxdepth 1 -name "*SUMMARY*.md" -exec mv {} $MONTH_DIR/reports/ \; 2>/dev/null || true
find . -maxdepth 1 -name "*ANALYSIS*.md" -exec mv {} $MONTH_DIR/reports/ \; 2>/dev/null || true

# 4. 移动中文报告
find . -maxdepth 1 -name "*报告*.md" -exec mv {} $MONTH_DIR/reports/ \; 2>/dev/null || true
find . -maxdepth 1 -name "*总结*.md" -exec mv {} $MONTH_DIR/reports/ \; 2>/dev/null || true

# 5. 清理旧的归档（保留最近3个月）
find archive/ -maxdepth 1 -type d -name "20*" -mtime +90 -exec mv {} $MONTH_DIR/old/ \; 2>/dev/null || true

# 6. 清理Docker镜像和容器（可选）
docker system prune -f

echo "✅ 每月深度清理完成！"
```

## 🛠️ 自动化设置

### 设置Cron任务
```bash
# 编辑crontab
crontab -e

# 添加以下行
# 每周五下午6点执行周清理
0 18 * * 5 cd /path/to/FootballPrediction && ./scripts/weekly_cleanup.sh

# 每月最后一天下午6点执行月清理
0 18 28-31 * * cd /path/to/FootballPrediction && [[ $(date -d tomorrow +\%d) -eq 1 ]] && ./scripts/monthly_cleanup.sh
```

### Git Hook设置
```bash
# 在 .git/hooks/pre-commit 中添加
# 清理缓存和临时文件
rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/ .cache/

# 检查是否有大文件需要归档
if [ $(find . -maxdepth 1 -name "*.md" | wc -l) -gt 30 ]; then
    echo "⚠️  警告：根目录Markdown文件过多，建议先清理"
    echo "运行: ./scripts/weekly_cleanup.sh"
fi
```

## ⚠️ 清理规则

### 🟢 安全删除（可随时重新生成）
- 缓存目录：`.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.cache/`
- 覆盖率数据：`coverage*.json`, `coverage*.xml`, `.coverage`
- 临时文件：`*_temp*`, `*_backup*`, `*.log`
- 时间戳报告：`improvement-report-*.md`

### 🟡 需要检查后删除
- Python脚本：检查是否还需要，不需要则移动到 `scripts/`
- 配置文件：检查是否为当前使用的配置
- 数据库文件：确认是否为测试数据

### 🔴 永不删除
- 核心项目文件：`src/`, `tests/`, `docs/`, `scripts/`, `config/`
- 配置文件：`pyproject.toml`, `pytest.ini`, `Makefile`, `.gitignore`
- 重要文档：`README.md`, `CONTRIBUTING.md`, `CLAUDE.md`
- 环境配置：`.env.example`, `.dockerignore`

## 📊 清理检查清单

### 清理前检查
- [ ] 确认所有重要代码已提交到Git
- [ ] 检查是否有正在运行的测试或构建
- [ ] 确认不需要保留的临时文件

### 清理后验证
- [ ] 运行 `make test` 确保功能正常
- [ ] 运行 `make lint` 检查代码质量
- [ ] 检查 `git status` 确认没有意外删除
- [ ] 验证项目可以正常启动

## 🚨 应急恢复

如果误删重要文件，可以从以下位置恢复：
1. **Git历史**: `git checkout HEAD~1 -- <filename>`
2. **归档目录**: 检查 `archive/` 目录
3. **回收站**: 某些系统可能已移到回收站
4. **重新生成**: 覆盖率报告、缓存等可以重新生成

## 📈 监控指标

建议监控以下指标来优化清理计划：
- 根目录文件数量（目标：< 50个）
- Markdown文件数量（目标：< 20个）
- 归档目录大小
- 清理执行时间

根据实际情况调整清理频率和范围。

---
*创建时间: 2025-10-24 | 最后更新: 2025-10-24*