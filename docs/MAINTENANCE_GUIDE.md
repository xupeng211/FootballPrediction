# 🔧 目录维护指南

## 🎯 概述

本指南为FootballPrediction项目的目录结构维护提供详细的操作流程和最佳实践，确保项目目录结构的长期整洁和规范。

## 📋 日常维护任务

### 🗂️ 每日维护
- **检查新增文件**: 确保新文件放在正确的目录中
- **清理临时文件**: 删除不再需要的临时文件和缓存
- **验证命名规范**: 确保新文件和目录符合命名规范

### 📅 每周维护
- **整理文档**: 将散落的文档移动到正确位置
- **检查重复目录**: 识别并清理重复或空目录
- **更新文档**: 确保目录结构文档与实际结构一致

### 📊 每月维护
- **深度清理**: 清理过期的报告和日志文件
- **结构优化**: 根据项目发展调整目录结构
- **归档历史**: 将历史数据移动到archive目录

## 🔍 维护检查清单

### ✅ 文件放置检查
```bash
# 1. 检查是否有文件放在错误位置
find /home/user/projects/FootballPrediction -maxdepth 1 -name "*.py" -not -path "*/scripts/*"

# 2. 检查是否有配置文件散落在根目录
find /home/user/projects/FootballPrediction -maxdepth 1 -name "*.ini" -o -name "*.toml" -o -name "*.yml"

# 3. 检查是否有文档文件需要整理
find /home/user/projects/FootballPrediction -maxdepth 1 -name "*.md" | grep -v "CLAUDE.md\|原始需求.md"
```

### 🧹 清理操作
```bash
# 1. 清理临时文件
find /home/user/projects/FootballPrediction -name "*.tmp" -delete
find /home/user/projects/FootballPrediction -name "__pycache__" -type d -exec rm -rf {} +
find /home/user/projects/FootballPrediction -name "*.pyc" -delete

# 2. 清理空目录
find /home/user/projects/FootballPrediction -type d -empty -delete

# 3. 清理旧的覆盖率报告
find /home/user/projects/FootballPrediction -name "coverage*.json" -mtime +30 -delete
```

### 📊 统计分析
```bash
# 1. 统计根目录文件数量
echo "根目录文件数: $(ls -1 /home/user/projects/FootballPrediction | wc -l)"

# 2. 统计各类型文件数量
echo "Python文件数: $(find /home/user/projects/FootballPrediction -name "*.py" | wc -l)"
echo "Markdown文件数: $(find /home/user/projects/FootballPrediction -name "*.md" | wc -l)"
echo "配置文件数: $(find /home/user/projects/FootballPrediction -name "*.ini" -o -name "*.toml" -o -name "*.yml" | wc -l)"

# 3. 分析目录大小
du -sh /home/user/projects/FootballPrediction/* | sort -hr | head -10
```

## 🛠️ 自动化维护工具

### 🤖 维护脚本
```python
#!/usr/bin/env python3
"""
目录维护自动化脚本
scripts/maintenance/directory_maintenance.py
"""

import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

class DirectoryMaintenance:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.temp_extensions = ['.tmp', '.bak', '.log']
        self.cache_dirs = ['__pycache__', '.pytest_cache', '.ruff_cache']

    def clean_temp_files(self):
        """清理临时文件"""
        cleaned_count = 0
        for ext in self.temp_extensions:
            for file_path in self.project_root.rglob(f"*{ext}"):
                if file_path.is_file():
                    file_path.unlink()
                    cleaned_count += 1
        print(f"✅ 清理了 {cleaned_count} 个临时文件")

    def clean_cache_dirs(self):
        """清理缓存目录"""
        cleaned_count = 0
        for cache_dir in self.cache_dirs:
            for dir_path in self.project_root.rglob(cache_dir):
                if dir_path.is_dir():
                    shutil.rmtree(dir_path)
                    cleaned_count += 1
        print(f"✅ 清理了 {cleaned_count} 个缓存目录")

    def check_misplaced_files(self):
        """检查错误放置的文件"""
        misplaced_files = []

        # 检查根目录下的Python文件
        for file_path in self.project_root.glob("*.py"):
            misplaced_files.append(file_path)

        # 检查根目录下的配置文件
        config_patterns = ["*.ini", "*.toml", "*.yml", "*.yaml"]
        for pattern in config_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.name not in ["alembic.ini"]:  # 保留符号链接
                    misplaced_files.append(file_path)

        return misplaced_files

    def archive_old_reports(self, days_old: int = 30):
        """归档旧报告"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        archived_count = 0

        # 归档旧的JSON报告
        for report_path in self.project_root.rglob("*.json"):
            if (report_path.name.startswith(("quality_report_", "coverage_")) and
                datetime.fromtimestamp(report_path.stat().st_mtime) < cutoff_date):
                archive_path = self.project_root / "docs" / "reports" / "legacy" / report_path.name
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(report_path), str(archive_path))
                archived_count += 1

        print(f"✅ 归档了 {archived_count} 个旧报告")

    def generate_maintenance_report(self):
        """生成维护报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "root_file_count": len(list(self.project_root.iterdir())),
            "python_files": len(list(self.project_root.rglob("*.py"))),
            "markdown_files": len(list(self.project_root.rglob("*.md"))),
            "config_files": len(list(self.project_root.rglob("*.ini")) +
                              list(self.project_root.rglob("*.toml")) +
                              list(self.project_root.rglob("*.yml"))),
        }

        # 计算目录大小
        total_size = sum(f.stat().st_size for f in self.project_root.rglob('*') if f.is_file())
        report["total_size_mb"] = round(total_size / (1024 * 1024), 2)

        return report

    def run_maintenance(self):
        """运行完整维护流程"""
        print("🔧 开始目录维护...")

        # 1. 清理临时文件
        self.clean_temp_files()

        # 2. 清理缓存目录
        self.clean_cache_dirs()

        # 3. 检查错误放置的文件
        misplaced = self.check_misplaced_files()
        if misplaced:
            print(f"⚠️  发现 {len(misplaced)} 个可能错误放置的文件:")
            for file_path in misplaced:
                print(f"   - {file_path}")

        # 4. 归档旧报告
        self.archive_old_reports()

        # 5. 生成维护报告
        report = self.generate_maintenance_report()
        print(f"📊 维护完成! 当前状态:")
        print(f"   - 根目录文件数: {report['root_file_count']}")
        print(f"   - Python文件数: {report['python_files']}")
        print(f"   - Markdown文件数: {report['markdown_files']}")
        print(f"   - 总大小: {report['total_size_mb']} MB")

        return report

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    maintenance = DirectoryMaintenance(project_root)
    maintenance.run_maintenance()
```

### ⚡ 快速维护命令
```bash
# 运行自动维护脚本
python3 scripts/maintenance/directory_maintenance.py

# 快速清理命令
make clean-temp          # 清理临时文件
make clean-cache         # 清理缓存文件
make check-structure     # 检查目录结构
make archive-reports     # 归档旧报告
```

## 🎯 具体场景处理

### 🔄 新功能开发时
1. **创建新模块**:
   ```bash
   # 在src下创建新的功能模块
   mkdir -p src/domain/new_feature
   touch src/domain/new_feature/__init__.py
   touch src/domain/new_feature/entities.py
   touch src/domain/new_feature/services.py
   ```

2. **创建测试文件**:
   ```bash
   # 在tests下创建对应的测试
   touch tests/unit/domain/new_feature/test_entities.py
   touch tests/unit/domain/new_feature/test_services.py
   ```

3. **创建配置文件**:
   ```bash
   # 如果需要新配置，放在config目录
   touch config/new_feature_config.py
   ```

### 🐛 问题修复时
1. **创建修复脚本**:
   ```bash
   # 修复脚本放在scripts/quality或scripts/maintenance
   touch scripts/quality/fix_specific_issue.py
   ```

2. **添加测试用例**:
   ```bash
   # 为修复的问题添加回归测试
   touch tests/unit/api/test_regression_fix.py
   ```

3. **更新文档**:
   ```bash
   # 如果涉及架构变更，更新相关文档
   # vim docs/DIRECTORY_STRUCTURE.md
   ```

### 📦 部署准备时
1. **整理配置文件**:
   ```bash
   # 确保所有部署配置在config目录
   # 检查docker-compose文件位置
   ```

2. **清理开发文件**:
   ```bash
   # 移除测试数据和临时文件
   # 归档开发过程中的报告
   ```

3. **更新文档**:
   ```bash
   # 确保部署文档是最新的
   # 更新CHANGELOG和RELEASE_NOTES
   ```

## 🚨 常见问题和解决方案

### ❓ 问题1: 根目录文件过多
**症状**: 根目录文件数超过500个
**解决方案**:
```bash
# 1. 识别散落的文件类型
find /home/user/projects/FootballPrediction -maxdepth 1 -type f | head -20

# 2. 批量移动到正确位置
mv *.md docs/reports/legacy/
mv *.json docs/reports/legacy/
mv *.py scripts/unused/
```

### ❓ 问题2: 重复目录
**症状**: 发现功能重复的目录
**解决方案**:
```bash
# 1. 识别重复目录
find /home/user/projects/FootballPrediction -maxdepth 1 -type d | sort

# 2. 比较目录内容
diff -r dir1 dir2

# 3. 合并内容并删除重复
mv dir1/* dir2/
rmdir dir1
```

### ❓ 问题3: 命名不一致
**症状**: 目录命名规范不统一
**解决方案**:
```bash
# 1. 查找使用下划线命名的目录
find /home/user/projects/FootballPrediction -maxdepth 1 -type d -name "*_*"

# 2. 批量重命名
for dir in */; do
    new_name=$(echo "$dir" | tr '_' '-' | sed 's/\/$//')
    if [ "$dir" != "$new_name/" ]; then
        mv "$dir" "$new_name"
    fi
done
```

### ❓ 问题4: 历史文件堆积
**症状**: 大量过期的报告和日志文件
**解决方案**:
```bash
# 1. 归档30天前的JSON报告
find /home/user/projects/FootballPrediction -name "*.json" -mtime +30 -exec mv {} docs/reports/legacy/ \;

# 2. 清理旧的日志文件
find /home/user/projects/FootballPrediction -name "*.log" -mtime +7 -delete

# 3. 压缩大文件
find /home/user/projects/FootballPrediction -name "*.log" -size +10M -exec gzip {} \;
```

## 📊 监控和报告

### 📈 目录健康指标
- **根目录文件数**: 目标 < 400个
- **重复目录数**: 目标 = 0个
- **空目录数**: 目标 < 5个
- **命名不规范**: 目标 = 0个
- **文档覆盖率**: 目标 > 80%

### 📋 定期报告模板
```markdown
# 目录维护报告 - {date}

## 📊 当前状态
- 根目录文件数: {count}
- Python文件数: {python_count}
- Markdown文件数: {md_count}
- 总存储大小: {size}MB

## ✅ 完成的维护
- 清理临时文件: {temp_count}个
- 清理缓存目录: {cache_count}个
- 归档旧报告: {archive_count}个
- 修复命名问题: {naming_count}个

## ⚠️ 发现的问题
{issues_list}

## 🎯 下一步行动
{next_actions}
```

## 🔄 持续改进

### 📚 培训和文档
- 为新团队成员提供目录结构培训
- 定期更新维护文档
- 建立最佳实践分享机制

### 🤖 自动化工具
- 开发更多自动化维护脚本
- 集成到CI/CD流水线
- 设置定期维护任务

### 📊 反馈机制
- 收集团队反馈
- 定期评估维护效果
- 持续优化维护流程

---

**文档版本**: v1.0
**最后更新**: 2025-11-03
**维护者**: Claude AI Assistant
**相关文档**: [DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md) | [NAMING_CONVENTIONS.md](NAMING_CONVENTIONS.md)

## 🛠️ 快速命令参考

```bash
# 检查目录结构健康
python3 scripts/maintenance/directory_maintenance.py

# 快速清理
make clean-temp && make clean-cache

# 检查命名规范
python3 scripts/utils/naming_convention_checker.py

# 生成维护报告
python3 scripts/maintenance/generate_maintenance_report.py
```