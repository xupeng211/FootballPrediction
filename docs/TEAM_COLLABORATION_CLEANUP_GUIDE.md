# 👥 团队协作清理指南

## 📋 目标
建立团队协作机制，确保项目始终保持整洁，提高开发效率。

## 🎯 团队职责分工

### 🧹 清洁负责人 (每周轮换)
- **职责**: 执行周清理，监控项目清洁度
- **时间**: 每周五下午
- **任务**:
  - 运行 `./scripts/weekly_cleanup.sh`
  - 检查清洁度报告 (`python3 scripts/project_cleanliness_monitor.py`)
  - 报告清理状态给团队

### 🔍 代码审查者 (每个PR)
- **职责**: 在代码审查中检查文件规范
- **检查点**:
  - 是否有临时文件被提交
  - 是否有临时报告文件堆积
  - 是否违反文件组织规范

### 📅 项目管理员 (每月)
- **职责**: 执行月度深度清理
- **时间**: 每月最后一天
- **任务**:
  - 运行 `./scripts/monthly_cleanup.sh`
  - 审查归档策略
  - 优化清理流程

## 📏 文件规范

### ✅ 允许在根目录的文件类型
```
✅ 配置文件: pyproject.toml, pytest.ini, Makefile
✅ 文档文件: README.md, CONTRIBUTING.md, CLAUDE.md
✅ 环境文件: .env.example, .gitignore, .dockerignore
✅ 构建文件: Dockerfile, docker-compose.yml
✅ 许可证: LICENSE, LICENSE.md
```

### ❌ 不允许在根目录的文件类型
```
❌ 临时报告: *_REPORT.md, *_SUMMARY.md
❌ 覆盖率数据: coverage*.json, coverage*.xml
❌ 缓存目录: .pytest_cache/, .mypy_cache/, __pycache__/
❌ 日志文件: *.log, *_temp*
❌ 备份文件: *_backup*, *.bak
❌ 临时脚本: add_*.py, fix_*.py (应放在 scripts/temp/)
```

### 📁 推荐的目录结构
```
FootballPrediction/
├── 📄 核心配置文件
├── src/                    # 源代码 ✅
├── tests/                  # 测试代码 ✅
├── docs/                   # 项目文档 ✅
├── scripts/               # 脚本文件 ✅
│   └── temp/             # 临时脚本 ✅
├── config/                # 配置文件 ✅
├── requirements/          # 依赖管理 ✅
├── archive/               # 历史归档 ✅
│   ├── reports/          # 报告归档 ✅
│   └── coverage/         # 覆盖率归档 ✅
└── monitoring-data/       # 监控数据 ✅
```

## 🔄 协作工作流程

### 🚨 每日检查 (开发者)
```bash
# 提交代码前检查
git status                    # 检查是否有意外文件
python3 scripts/project_cleanliness_monitor.py  # 查看清洁度
```

### 📅 每周清理 (清洁负责人)
```bash
# 每周五执行
./scripts/weekly_cleanup.sh

# 检查结果
python3 scripts/project_cleanliness_monitor.py

# 向团队报告
echo "本周清理完成，清洁度分数: X分"
```

### 📊 每月报告 (项目管理员)
```bash
# 每月最后一天执行
./scripts/monthly_cleanup.sh

# 生成月度报告
echo "月度清理报告:
- 归档文件: X个
- 清洁度提升: X分
- 团队协作状况: 优秀"
```

## 🤖 Git Hooks 自动化

### 安装Pre-commit Hooks
```bash
# 在 .git/hooks/pre-commit 中添加
#!/bin/bash
echo "🧹 检查提交文件..."

# 检查是否有临时文件
if git diff --cached --name-only | grep -E "(_REPORT\.md|_SUMMARY\.md|coverage\*\.|\.log$)"; then
    echo "⚠️  检测到临时文件在暂存区！"
    echo "请移动到合适位置或删除这些文件:"
    git diff --cached --name-only | grep -E "(_REPORT\.md|_SUMMARY\.md|coverage\*\.|\.log$)"
    exit 1
fi

# 检查清洁度
python3 scripts/project_cleanliness_monitor.py > /dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  项目清洁度较低，建议先清理"
fi

echo "✅ 文件检查通过"
```

### 安装Pre-push Hooks
```bash
# 在 .git/hooks/pre-push 中添加
#!/bin/bash
echo "🧹 推送前清理检查..."

# 快速清理缓存
rm -rf .pytest_cache/ .mypy_cache/ __pycache__/ 2>/dev/null || true

# 检查清洁度分数
SCORE=$(python3 scripts/project_cleanliness_monitor.py | grep "清洁度分数" | grep -o '[0-9]*')

if [ "$SCORE" -lt 70 ]; then
    echo "⚠️  项目清洁度分数过低 ($SCORE)，建议先运行清理"
    echo "运行: ./scripts/weekly_cleanup.sh"
    read -p "是否继续推送? (y/N): " confirm
    if [ "$confirm" != "y" ]; then
        exit 1
    fi
fi

echo "✅ 推送前检查通过"
```

## 📋 检查清单

### 🔍 开发者提交前
- [ ] 没有提交临时文件
- [ ] 没有提交覆盖率数据文件
- [ ] 没有提交日志文件
- [ ] 检查过项目清洁度
- [ ] 运行过 `make test` 验证功能

### 📅 清洁负责人周清理
- [ ] 运行周清理脚本
- [ ] 检查清洁度分数
- [ ] 归档临时报告
- [ ] 向团队报告状态
- [ ] 记录清理日志

### 📊 项目管理员月清理
- [ ] 运行月度深度清理
- [ ] 审查归档策略
- [ ] 生成月度报告
- [ ] 更新清理指南
- [ ] 评估团队协作效果

## ⚡ 快速修复命令

### 🚨 紧急清理
```bash
# 快速清理当前混乱
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
rm -rf .pytest_cache/ .mypy_cache/ .cache/

# 移动临时文件
mkdir -p scripts/temp/
mv add_*.py fix_*.py scripts/temp/ 2>/dev/null || true
```

### 📊 诊断问题
```bash
# 查看文件分布
find . -maxdepth 1 -type f | wc -l                    # 根目录文件数
find . -maxdepth 1 -name "*.md" | wc -l               # Markdown文件数
du -sh archive/                                       # 归档大小

# 生成完整报告
python3 scripts/project_cleanliness_monitor.py
```

### 🔧 设置自动化
```bash
# 重新设置自动化任务
./scripts/setup_auto_cleanup.sh

# 手动触发清理
./scripts/weekly_cleanup.sh
./scripts/monthly_cleanup.sh
```

## 🎯 成功指标

### 量化指标
- **清洁度分数**: 目标 ≥ 80分
- **根目录文件数**: 目标 ≤ 50个
- **Markdown文件数**: 目标 ≤ 20个
- **归档大小**: 目标 ≤ 100MB

### 质量指标
- **团队遵守率**: 100% 成员遵守文件规范
- **自动化效果**: 90%+ 清理任务自动执行
- **响应速度**: 问题发现后24小时内解决

## 🚨 故障排除

### 常见问题
1. **cron任务不执行**
   ```bash
   # 检查cron服务
   sudo systemctl status cron

   # 查看cron日志
   tail -f /var/log/syslog | grep CRON
   ```

2. **脚本权限问题**
   ```bash
   # 修复脚本权限
   chmod +x scripts/*.sh
   chmod +x scripts/*.py
   ```

3. **Python环境问题**
   ```bash
   # 确保使用正确的Python
   which python3
   /home/user/projects/FootballPrediction/.venv/bin/python3 scripts/weekly_cleanup.sh
   ```

### 获取帮助
- 📖 查看 [REGULAR_CLEANUP_PLAN.md](./REGULAR_CLEANUP_PLAN.md)
- 🔧 运行 `python3 scripts/project_cleanliness_monitor.py`
- 👥 联系清洁负责人或项目管理员

## 📈 持续改进

### 月度回顾
- 清洁度分数趋势分析
- 团队协作效果评估
- 清理流程优化建议
- 自动化程度提升

### 季度优化
- 更新清洁标准
- 改进自动化脚本
- 扩展监控功能
- 团队培训更新

---

**记住**: 整洁的项目 = 高效的团队！ 🎯

*创建时间: 2025-10-24 | 维护者: 全体团队成员*
