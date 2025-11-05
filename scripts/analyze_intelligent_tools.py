#!/usr/bin/env python3
"""
智能工具体系分析和优化器
Intelligent Tool System Analysis and Optimizer

分析现有的600+个脚本，提供功能优化建议
"""

import os
import re
import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
import subprocess

class IntelligentToolAnalyzer:
    """智能工具分析器"""

    def __init__(self):
        self.base_dir = Path(".")
        self.scripts_dir = Path("scripts")
        self.analysis_results = {
            "total_scripts": 0,
            "python_scripts": 0,
            "shell_scripts": 0,
            "tool_categories": {},
            "functionality_analysis": {},
            "optimization_suggestions": [],
            "integration_opportunities": [],
            "quality_metrics": {}
        }

    def scan_all_scripts(self) -> Dict:
        """扫描所有脚本文件"""
        print("🔍 扫描智能工具体系...")

        # 扫描Python脚本
        python_scripts = list(self.base_dir.rglob("*.py"))
        # 扫描Shell脚本
        shell_scripts = list(self.base_dir.rglob("*.sh"))

        # 过滤掉非scripts目录的文件
        python_scripts = [p for p in python_scripts if "scripts" in str(p)]
        shell_scripts = [p for p in shell_scripts if "scripts" in str(p)]

        self.analysis_results["python_scripts"] = len(python_scripts)
        self.analysis_results["shell_scripts"] = len(shell_scripts)
        self.analysis_results["total_scripts"] = len(python_scripts) + len(shell_scripts)

        print(f"📊 发现脚本统计:")
        print(f"   Python脚本: {len(python_scripts)}个")
        print(f"   Shell脚本: {len(shell_scripts)}个")
        print(f"   总计: {self.analysis_results['total_scripts']}个")

        return {
            "python_scripts": python_scripts,
            "shell_scripts": shell_scripts
        }

    def analyze_script_functionality(self, script_path: Path) -> Dict:
        """分析单个脚本的功能"""
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()

            analysis = {
                "path": str(script_path),
                "size_lines": len(content.splitlines()),
                "functions": [],
                "imports": [],
                "features": [],
                "quality_score": 0,
                "category": self.categorize_script(script_path, content),
                "complexity": "medium"
            }

            # 分析Python脚本
            if script_path.suffix == ".py":
                analysis.update(self.analyze_python_script(content))
            # 分析Shell脚本
            elif script_path.suffix == ".sh":
                analysis.update(self.analyze_shell_script(content))

            # 计算质量分数
            analysis["quality_score"] = self.calculate_quality_score(analysis)

            return analysis

        except Exception as e:
            return {
                "path": str(script_path),
                "error": str(e),
                "category": "error"
            }

    def analyze_python_script(self, content: str) -> Dict:
        """分析Python脚本"""
        analysis = {
            "functions": [],
            "imports": [],
            "features": [],
            "has_main": False,
            "has_docstring": False,
            "has_error_handling": False,
            "uses_async": False
        }

        try:
            tree = ast.parse(content)

            # 检查文档字符串
            if ast.get_docstring(tree):
                analysis["has_docstring"] = True

            # 分析导入
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        analysis["imports"].append(node.module)

            # 分析函数和类
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis["functions"].append(node.name)

                    # 检查异步函数
                    if isinstance(node, ast.AsyncFunctionDef):
                        analysis["uses_async"] = True

                elif isinstance(node, ast.ClassDef):
                    analysis["functions"].append(f"class:{node.name}")

            # 检查main函数
            analysis["has_main"] = any("main" in func for func in analysis["functions"])

            # 检查错误处理
            error_handling_keywords = ["try:", "except", "raise", "finally:"]
            analysis["has_error_handling"] = any(keyword in content for keyword in error_handling_keywords)

            # 检测功能特征
            if "pytest" in content:
                analysis["features"].append("testing")
            if "requests" in content or "http" in content:
                analysis["features"].append("networking")
            if "sqlite" in content or "database" in content:
                analysis["features"].append("database")
            if "logging" in content:
                analysis["features"].append("logging")
            if "argparse" in content or "click" in content:
                analysis["features"].append("cli")
            if "schedule" in content or "cron" in content:
                analysis["features"].append("automation")
            if "coverage" in content:
                analysis["features"].append("coverage_analysis")
            if "github" in content or "git" in content:
                analysis["features"].append("git_integration")

        except SyntaxError:
            analysis["syntax_error"] = True

        return analysis

    def analyze_shell_script(self, content: str) -> Dict:
        """分析Shell脚本"""
        analysis = {
            "functions": [],
            "imports": [],
            "features": [],
            "has_shebang": False,
            "has_error_handling": False,
            "uses_variables": False
        }

        # 检查shebang
        if content.startswith("#!"):
            analysis["has_shebang"] = True

        # 提取函数名
        function_matches = re.findall(r'^\s*function\s+(\w+)|^(\w+)\s*\(\s*\)',
    content,
    re.MULTILINE)
        for match in function_matches:
            func_name = match[0] or match[1]
            if func_name:
                analysis["functions"].append(func_name)

        # 检测功能特征
        if "docker" in content:
            analysis["features"].append("docker")
        if "git" in content:
            analysis["features"].append("git")
        if "pytest" in content or "python" in content:
            analysis["features"].append("testing")
        if "npm" in content or "yarn" in content:
            analysis["features"].append("package_manager")
        if "systemctl" in content or "service" in content:
            analysis["features"].append("service_management")

        # 检查错误处理
        analysis["has_error_handling"] = "set -e" in content or "||" in content

        # 检查变量使用
        analysis["uses_variables"] = "$" in content

        return analysis

    def categorize_script(self, script_path: Path, content: str) -> str:
        """对脚本进行分类"""
        path_str = str(script_path).lower()
        content_lower = content.lower()

        # 测试相关
        if any(keyword in path_str or keyword in content_lower
               for keyword in ["test", "pytest", "coverage"]):
            return "testing"

        # 部署相关
        if any(keyword in path_str or keyword in content_lower
               for keyword in ["deploy", "deployment", "ci", "cd"]):
            return "deployment"

        # 质量保证
        if any(keyword in path_str or keyword in content_lower
               for keyword in ["quality", "lint", "fix", "review", "analyze"]):
            return "quality"

        # 监控相关
        if any(keyword in path_str or keyword in content_lower
               for keyword in ["monitor", "metrics", "performance", "health"]):
            return "monitoring"

        # 工具集成
        if any(keyword in path_str or keyword in content_lower
               for keyword in ["integration", "sync", "automation", "tool"]):
            return "integration"

        # GitHub相关
        if any(keyword in path_str or keyword in content_lower
               for keyword in ["github", "git", "issue"]):
            return "github"

        # 机器学习/数据
        if any(keyword in path_str or keyword in content_lower
               for keyword in ["ml", "model", "prediction", "data"]):
            return "ml_data"

        # 默认分类
        return "utility"

    def calculate_quality_score(self, analysis: Dict) -> int:
        """计算脚本质量分数"""
        score = 0

        # 基础分数
        if analysis.get("has_docstring", False):
            score += 20
        if analysis.get("has_main", False):
            score += 15
        if analysis.get("has_error_handling", False):
            score += 15
        if analysis.get("has_shebang", False):
            score += 10

        # 功能复杂度
        functions = analysis.get("functions", [])
        if len(functions) > 0:
            score += min(20, len(functions) * 2)

        # 特征丰富度
        features = analysis.get("features", [])
        score += min(20, len(features) * 3)

        return min(100, score)

    def generate_optimization_suggestions(self,
    script_analyses: List[Dict]) -> List[Dict]:
        """生成优化建议"""
        suggestions = []

        # 统计分析
        categories = {}
        quality_scores = []

        for analysis in script_analyses:
            if "error" not in analysis:
                category = analysis.get("category", "unknown")
                categories[category] = categories.get(category, 0) + 1
                quality_scores.append(analysis.get("quality_score", 0))

        # 生成建议
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            if avg_quality < 70:
                suggestions.append({
                    "type": "quality_improvement",
                    "priority": "high",
                    "description": f"整体脚本质量分数较低({avg_quality:.1f}/100)，建议添加文档字符串、错误处理和主函数",
    
    
                    "affected_scripts": "multiple"
                })

        # 检查重复功能
        feature_counts = {}
        for analysis in script_analyses:
            if "features" in analysis:
                for feature in analysis["features"]:
                    feature_counts[feature] = feature_counts.get(feature, 0) + 1

        # 识别可以整合的重复功能
        for feature, count in feature_counts.items():
            if count > 3:
                suggestions.append({
                    "type": "consolidation",
                    "priority": "medium",
                    "description": f"发现{count}个脚本都有'{feature}'功能，考虑创建统一的工具库",
                    "feature": feature,
                    "count": count
                })

        # 检查缺失的功能
        essential_features = ["logging", "error_handling", "configuration", "documentation"]
        for feature in essential_features:
            if feature not in feature_counts:
                suggestions.append({
                    "type": "missing_feature",
                    "priority": "medium",
                    "description": f"缺少{feature}相关的工具，建议添加相应的脚本",
                    "feature": feature
                })

        return suggestions

    def generate_integration_opportunities(self,
    script_analyses: List[Dict]) -> List[Dict]:
        """生成集成机会"""
        opportunities = []

        # 分析脚本间的依赖关系
        import_map = {}
        for analysis in script_analyses:
            if "imports" in analysis:
                for imp in analysis["imports"]:
                    if "scripts" in imp:
                        import_map[imp] = import_map.get(imp, 0) + 1

        # 识别可以创建工具链的脚本组
        testing_scripts = []
        deployment_scripts = []
        quality_scripts = []

        for analysis in script_analyses:
            category = analysis.get("category", "")
            if category == "testing":
                testing_scripts.append(analysis["path"])
            elif category == "deployment":
                deployment_scripts.append(analysis["path"])
            elif category == "quality":
                quality_scripts.append(analysis["path"])

        # 生成集成建议
        if len(testing_scripts) > 2:
            opportunities.append({
                "type": "tool_chain",
                "category": "testing",
                "description": f"可以创建测试工具链，整合{len(testing_scripts)}个测试相关脚本",
                "scripts": testing_scripts[:5]  # 只显示前5个
            })

        if len(deployment_scripts) > 2:
            opportunities.append({
                "type": "tool_chain",
                "category": "deployment",
                "description": f"可以创建部署工具链，整合{len(deployment_scripts)}个部署相关脚本",
                "scripts": deployment_scripts[:5]
            })

        if len(quality_scripts) > 2:
            opportunities.append({
                "type": "tool_chain",
                "category": "quality",
                "description": f"可以创建质量保证工具链，整合{len(quality_scripts)}个质量相关脚本",
                "scripts": quality_scripts[:5]
            })

        return opportunities

    def create_optimization_plan(self) -> Dict:
        """创建优化计划"""
        print("🔧 创建智能工具优化计划...")

        # 扫描脚本
        scripts = self.scan_all_scripts()

        # 分析所有脚本
        all_analyses = []

        # 分析Python脚本
        print("📝 分析Python脚本...")
        for script_path in scripts["python_scripts"]:
            analysis = self.analyze_script_functionality(script_path)
            all_analyses.append(analysis)

        # 分析Shell脚本
        print("🐚 分析Shell脚本...")
        for script_path in scripts["shell_scripts"]:
            analysis = self.analyze_script_functionality(script_path)
            all_analyses.append(analysis)

        # 生成优化建议
        print("💡 生成优化建议...")
        optimization_suggestions = self.generate_optimization_suggestions(all_analyses)

        # 生成集成机会
        print("🔗 识别集成机会...")
        integration_opportunities = self.generate_integration_opportunities(all_analyses)

        # 统计分类
        categories = {}
        for analysis in all_analyses:
            if "error" not in analysis:
                category = analysis.get("category", "unknown")
                categories[category] = categories.get(category, 0) + 1

        # 计算质量指标
        quality_scores = [a.get("quality_score",
    0) for a in all_analyses if "error" not in a]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        # 更新分析结果
        self.analysis_results.update({
            "tool_categories": categories,
            "functionality_analysis": {a["path"]: a for a in all_analyses if "error" not in a},
            "optimization_suggestions": optimization_suggestions,
            "integration_opportunities": integration_opportunities,
            "quality_metrics": {
                "average_quality_score": avg_quality,
                "high_quality_scripts": len([s for s in quality_scores if s >= 80]),
                "medium_quality_scripts": len([s for s in quality_scores if 60 <= s < 80]),
    
    
                "low_quality_scripts": len([s for s in quality_scores if s < 60])
            }
        })

        return self.analysis_results

    def generate_report(self) -> str:
        """生成分析报告"""
        report = f"""
# 智能工具体系分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**分析脚本总数**: {self.analysis_results['total_scripts']}

## 📊 脚本统计

- **Python脚本**: {self.analysis_results['python_scripts']}个
- **Shell脚本**: {self.analysis_results['shell_scripts']}个
- **总计**: {self.analysis_results['total_scripts']}个

## 🗂️ 工具分类分布

"""

        for category, count in self.analysis_results["tool_categories"].items():
            report += f"- **{category}**: {count}个\n"

        report += f"""
## 📈 质量指标

- **平均质量分数**: {self.analysis_results['quality_metrics']['average_quality_score']:.1f}/100
- **高质量脚本**: {self.analysis_results['quality_metrics']['high_quality_scripts']}个
- **中等质量脚本**: {self.analysis_results['quality_metrics']['medium_quality_scripts']}个
- **低质量脚本**: {self.analysis_results['quality_metrics']['low_quality_scripts']}个

## 💡 优化建议

"""

        for i,
    suggestion in enumerate(self.analysis_results["optimization_suggestions"][:10],
    1):
            report += f"### {i}. {suggestion['description']}\n"
            report += f"- **优先级**: {suggestion['priority']}\n"
            report += f"- **类型**: {suggestion['type']}\n\n"

        report += "## 🔗 集成机会\n\n"

        for i,
    opportunity in enumerate(self.analysis_results["integration_opportunities"][:5],
    1):
            report += f"### {i}. {opportunity['description']}\n"
            report += f"- **类别**: {opportunity['category']}\n"
            report += f"- **类型**: {opportunity['type']}\n\n"

        return report

def main():
    """主函数"""
    print("🚀 启动智能工具体系分析...")

    analyzer = IntelligentToolAnalyzer()

    # 创建优化计划
    optimization_plan = analyzer.create_optimization_plan()

    # 生成报告
    report = analyzer.generate_report()

    # 保存报告
    with open("intelligent_tools_analysis_report.md", "w", encoding="utf-8") as f:
        f.write(report)

    # 保存详细数据
    with open("intelligent_tools_analysis_data.json", "w", encoding="utf-8") as f:
        json.dump(optimization_plan, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n📊 分析完成!")
    print(f"   总脚本数: {optimization_plan['total_scripts']}")
    print(f"   平均质量分数: {optimization_plan['quality_metrics']['average_quality_score']:.1f}/100")
    print(f"   优化建议: {len(optimization_plan['optimization_suggestions'])}个")
    print(f"   集成机会: {len(optimization_plan['integration_opportunities'])}个")
    print(f"\n📄 报告已保存:")
    print(f"   - intelligent_tools_analysis_report.md")
    print(f"   - intelligent_tools_analysis_data.json")

    return optimization_plan

if __name__ == "__main__":
    main()