#!/usr/bin/env python3
"""
覆盖率数据分析工具 - 80%冲刺路线图生成器
从coverage.json中提取关键数据，识别高ROI的测试目标
"""

import json
import sys
from typing import Any
from pathlib import Path


def load_coverage_data(file_path: str = "coverage_new.json") -> dict:
    """加载覆盖率数据"""
    try:
        with open(file_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ 错误: 找不到覆盖率报告文件 '{file_path}'")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ 错误: 无法解析覆盖率报告文件 '{file_path}'")
        sys.exit(1)


def analyze_file_coverage(coverage_data: dict) -> list[tuple[str, int, int, float]]:
    """
    分析每个文件的覆盖率情况

    返回 : list[tuple[文件路径, 总行数, 未覆盖行数, 覆盖率百分比]]
    """
    files_analysis = []

    for file_path, file_data in coverage_data.get("files", {}).items():
        if not file_path.startswith("src/"):
            continue

        summary = file_data.get("summary", {})
        total_lines = summary.get("num_statements", 0)
        missing_lines = summary.get("missing_lines", 0)
        covered_lines = total_lines - missing_lines
        coverage_percent = (covered_lines / total_lines * 100) if total_lines > 0 else 0

        files_analysis.append((file_path, total_lines, missing_lines, coverage_percent))

    return files_analysis


def categorize_module(file_path: str) -> str:
    """根据路径将文件分类到不同模块"""
    if "api/" in file_path:
        return "API层"
    elif "database/" in file_path or "db" in file_path:
        return "数据层"
    elif "domain/" in file_path:
        return "领域层"
    elif "services/" in file_path:
        return "服务层"
    elif "ml/" in file_path:
        return "机器学习"
    elif "cache/" in file_path:
        return "缓存层"
    elif "collectors/" in file_path or "data/" in file_path:
        return "数据收集"
    elif "tasks/" in file_path:
        return "任务调度"
    elif "core/" in file_path:
        return "核心基础设施"
    elif "utils/" in file_path or "helpers" in file_path:
        return "工具层"
    elif "monitoring/" in file_path:
        return "监控系统"
    elif "config/" in file_path:
        return "配置层"
    else:
        return "其他模块"


def identify_quick_wins(
    files_analysis: list[tuple[str, int, int, float]],
) -> list[dict]:
    """
    识别Quick Wins目标 - 高未覆盖行数且易于测试的文件
    优先选择: API路由、数据模型、服务类等
    """
    quick_win_patterns = [
        "api/routes/",
        "services/",
        "database/models/",
        "domain/entities/",
        "cache/",
        "config/",
        "utils/",
    ]

    quick_wins = []
    for file_path, total_lines, missing_lines, coverage_percent in files_analysis:
        if missing_lines < 10:  # 跳过未覆盖行数太少的文件
            continue

        is_quick_win = any(pattern in file_path for pattern in quick_win_patterns)
        if is_quick_win:
            quick_wins.append(
                {
                    "file": file_path,
                    "module": categorize_module(file_path),
                    "total_lines": total_lines,
                    "missing_lines": missing_lines,
                    "coverage_percent": coverage_percent,
                    "roi_score": missing_lines
                    * (2.0 if "api/routes/" in file_path else 1.5),  # API路径权重更高
                }
            )

    return sorted(quick_wins, key=lambda x: x["roi_score"], reverse=True)


def identify_hard_battles(
    files_analysis: list[tuple[str, int, int, float]],
) -> list[dict]:
    """
    识别Hard Battles目标 - 代码行数多但测试难度大的文件
    主要包括: 复杂的第三方API集成、异步任务等
    """
    hard_battle_patterns = ["collectors/", "data/", "tasks/", "ml/", "monitoring/"]

    hard_battles = []
    for file_path, total_lines, missing_lines, coverage_percent in files_analysis:
        if missing_lines < 20:  # 只关注未覆盖行数较多的文件
            continue

        is_hard_battle = any(pattern in file_path for pattern in hard_battle_patterns)
        if is_hard_battle:
            difficulty_score = missing_lines
            if "collectors/" in file_path:
                difficulty_score *= 2.0  # 数据收集器难度权重最高
            elif "ml/" in file_path:
                difficulty_score *= 1.8  # ML模块次之
            elif "tasks/" in file_path:
                difficulty_score *= 1.5

            hard_battles.append(
                {
                    "file": file_path,
                    "module": categorize_module(file_path),
                    "total_lines": total_lines,
                    "missing_lines": missing_lines,
                    "coverage_percent": coverage_percent,
                    "difficulty_score": difficulty_score,
                }
            )

    return sorted(hard_battles, key=lambda x: x["difficulty_score"], reverse=True)


def generate_roadmap_report(
    coverage_data: dict, files_analysis: list[tuple[str, int, int, float]]
) -> str:
    """生成80%覆盖率冲刺路线图报告"""

    # 计算整体覆盖率
    totals = coverage_data.get("totals", {})
    current_coverage = totals.get("percent_covered", 0)

    # 获取Top 20未覆盖文件
    top_20_files = sorted(
        [f for f in files_analysis if f[2] > 5],  # 只显示未覆盖行数>5的文件
        key=lambda x: x[2],  # 按未覆盖行数排序
        reverse=True,
    )[:20]

    # 识别Quick Wins和Hard Battles
    quick_wins = identify_quick_wins(files_analysis)[:10]
    hard_battles = identify_hard_battles(files_analysis)[:10]

    # 计算潜在覆盖率提升
    # 移除未使用的变量: total_missing_lines = sum(f[2] for f in files_analysis)
    quick_wins_potential = sum(w["missing_lines"] for w in quick_wins)

    # 生成报告
    report = f"""# 🎯 80%覆盖率冲刺路线图

## 📊 当前基线状态

- **当前覆盖率**: **{current_coverage:.1f}%**
- **总代码行数**: {totals.get("num_statements", 0):,} 行
- **已覆盖行数**: {totals.get("covered_lines", 0):,} 行
- **未覆盖行数**: {totals.get("missing_lines", 0):,} 行
- **目标差距**: {max(0, 80 - current_coverage):.1f}% (需要覆盖约 {int((max(0, 80 - current_coverage) / 100) * totals.get("num_statements", 1)):,} 行)

---

## 🏆 Top 20 战场 (按未覆盖行数排序)

| 排名 | 文件路径 | 模块类型 | 总行数 | 未覆盖行数 | 当前覆盖率 |
|------|----------|----------|--------|------------|------------|
"""

    for i, (file_path, total_lines, missing_lines, coverage_percent) in enumerate(
        top_20_files, 1
    ):
        module_type = categorize_module(file_path)
        report += f"| {i:2d} | `{file_path}` | {module_type} | {total_lines:4d} | **{missing_lines:4d}** | {coverage_percent:5.1f}% |\n"

    report += f"""

---

## ⚡ Quick Wins (速胜目标) - 预计提升{quick_wins_potential:.0f}行覆盖率

这些文件相对容易测试，可以通过Mock和单元测试快速获得大量覆盖率提升：

| 优先级 | 文件路径 | 模块 | 未覆盖行数 | 难度评估 |
|--------|----------|------|------------|----------|
"""

    for i, win in enumerate(quick_wins, 1):
        difficulty = (
            "🟢 简单"
            if win["missing_lines"] < 30
            else "🟡 中等" if win["missing_lines"] < 50 else "🔠 较难"
        )
        report += f"| {i} | `{win['file']}` | {win['module']} | {win['missing_lines']} | {difficulty} |\n"

    report += f"""

### 🎯 Quick Wins 执行策略
1. **API路由测试** - 使用FastAPI TestClient，Mock数据库操作
2. **服务层测试** - Mock外部依赖，专注业务逻辑
3. **数据模型测试** - 验证模型验证和序列化逻辑
4. **配置和工具类** - 纯函数，最容易测试

预计完成后覆盖率可提升至: **{current_coverage + (quick_wins_potential / totals.get("num_statements", 1) * 100):.1f}%**

---

## 🛠️ Hard Battles (攻坚目标) - 需要更多策略和资源

这些文件测试难度较高，需要集成测试、Mock策略或特殊测试环境：

| 优先级 | 文件路径 | 模块 | 未覆盖行数 | 难度系数 |
|--------|----------|------|------------|----------|
"""

    for i, battle in enumerate(hard_battles, 1):
        difficulty_desc = (
            "🔴 极难"
            if battle["difficulty_score"] > 100
            else "🟠 困难" if battle["difficulty_score"] > 50 else "🟡 中等"
        )
        report += f"| {i} | `{battle['file']}` | {battle['module']} | {battle['missing_lines']} | {difficulty_desc} |\n"

    report += """

### 🎯 Hard Battles 攻坚策略
1. **数据收集器** - 使用VCR.py记录真实API响应，或创建完整的Mock服务
2. **机器学习模块** - 专注于工具函数和数据处理管道，模型本身可通过集成测试验证
3. **任务调度** - 使用Celery的testing mode，Mock外部系统
4. **监控系统** - Mock监控指标收集器，专注验证告警逻辑

---

## 📋 执行顺序建议

### 第一阶段: Quick Wins (预计覆盖率提升至 45-55%)
1. 测试API路由文件 (预计 +8-12%)
2. 测试服务层核心逻辑 (预计 +6-10%)
3. 测试数据模型和验证 (预计 +4-8%)
4. 测试配置和工具类 (预计 +3-5%)

### 第二阶段: 模块扩展 (预计覆盖率提升至 65-75%)
1. 测试缓存层和数据库操作 (预计 +8-12%)
2. 测试领域层业务规则 (预计 +6-10%)
3. 测试任务调度核心逻辑 (预计 +5-8%)

### 第三阶段: Hard Battles (冲击80%+)
1. 数据收集器集成测试 (预计 +5-8%)
2. 机器学习管道测试 (预计 +4-7%)
3. 监控和告警系统测试 (预计 +3-5%)

---

## 🚀 下一步行动

### 立即开始 (本周)
- [ ] 为API路由添加基础测试框架
- [ ] 为核心服务类创建Mock策略
- [ ] 设置测试数据库和Redis实例

### 短期目标 (2周内)
- [ ] 完成所有Quick Wins目标
- [ ] 建立持续集成中的覆盖率监控
- [ ] 创建测试模板和最佳实践文档

### 中期目标 (1个月内)
- [ ] 攻克Hard Battles中的关键模块
- [ ] 达到80%覆盖率目标
- [ ] 建立质量门禁机制

---

## 📈 成功指标

- **每周覆盖率增长**: 目标 5-8%
- **Quick Wins完成率**: 90%+
- **测试执行时间**: < 5分钟
- **CI/CD通过率**: 保持95%+

---

*报告生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    return report


def main():
    """主函数"""
    print("🔍 正在分析覆盖率数据...")

    # 加载覆盖率数据
    coverage_data = load_coverage_data()

    # 分析文件覆盖率
    files_analysis = analyze_file_coverage(coverage_data)

    print(f"📊 找到 {len(files_analysis)} 个Python文件")

    # 生成报告
    report = generate_roadmap_report(coverage_data, files_analysis)

    # 保存报告
    with open("COVERAGE_ROADMAP_TO_80.md", "w", encoding="utf-8") as f:
        f.write(report)

    print("✅ 路线图报告已生成: COVERAGE_ROADMAP_TO_80.md")

    # 输出关键统计
    totals = coverage_data.get("totals", {})
    current_coverage = totals.get("percent_covered", 0)
    total_missing = totals.get("missing_lines", 0)

    print("\n📈 关键指标:")
    print(f"   当前覆盖率: {current_coverage:.1f}%")
    print(f"   未覆盖行数: {total_missing:,}")
    print(f"   目标差距: {max(0, 80 - current_coverage):.1f}%")

    # 显示Top 5文件
    top_5 = sorted(
        [f for f in files_analysis if f[2] > 5], key=lambda x: x[2], reverse=True
    )[:5]
    print("\n🎯 Top 5 优先目标:")
    for i, (file_path, _, missing_lines, _) in enumerate(top_5, 1):
        print(f"   {i}. {file_path} ({missing_lines} 行未覆盖)")


if __name__ == "__main__":
    main()
