#!/usr/bin/env python3
"""
安全健康度跟踪器
跟踪项目的安全健康度评分和趋势
"""

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

class SecurityHealthTracker:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.history_file = self.project_root / "docs" / "_reports" / "security" / "health_history.json"
        self.report_file = self.project_root / "docs" / "_reports" / "security" / "health_report.md"
        self.trend_file = self.project_root / "docs" / "_reports" / "security" / "trend_analysis.json"

        # 确保目录存在
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        # 评分权重
        self.weights = {
            'critical_vulnerabilities': 30,
            'high_vulnerabilities': 20,
            'medium_vulnerabilities': 10,
            'low_vulnerabilities': 5,
            'code_issues': 15,
            'security_debt': 10,
            'compliance_score': 10
        }

    def log(self, message: str, level: str = "INFO"):
        colors = {
            "INFO": "\033[0m",
            "WARN": "\033[0;33m",
            "ERROR": "\033[0;31m",
            "SUCCESS": "\033[0;32m",
            "HIGHLIGHT": "\033[1;34m"
        }
        color = colors.get(level, "\033[0m")
        print(f"{color}{message}\033[0m")

    def load_history(self) -> List[Dict]:
        """加载历史数据"""
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return []

    def save_history(self, history: List[Dict]):
        """保存历史数据"""
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2, default=str)

    def run_dependency_audit(self) -> Dict:
        """运行依赖审计"""
        self.log("运行依赖审计...", "INFO")

        result = subprocess.run(
            ["pip-audit", "-r", "requirements.txt", "--format", "json"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                vulnerabilities = {
                    'critical': 0,
                    'high': 0,
                    'medium': 0,
                    'low': 0
                }

                for dep in data.get('dependencies', []):
                    for vuln in dep.get('vulns', []):
                        # 简单分类逻辑
                        if any(s in vuln.get('id', '').upper() for s in ['CRITICAL']):
                            vulnerabilities['critical'] += 1
                        elif any(s in vuln.get('id', '').upper() for s in ['HIGH']):
                            vulnerabilities['high'] += 1
                        elif any(s in vuln.get('id', '').upper() for s in ['MEDIUM']):
                            vulnerabilities['medium'] += 1
                        else:
                            vulnerabilities['low'] += 1

                return vulnerabilities
            except json.JSONDecodeError:
                self.log("解析依赖审计结果失败", "ERROR")

        # 如果失败，返回默认值
        return {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}

    def run_code_scan(self) -> Dict:
        """运行代码安全扫描"""
        self.log("运行代码安全扫描...", "INFO")

        result = subprocess.run(
            ["bandit", "-r", "src/", "-f", "json"],
            capture_output=True,
            text=True
        )

        if result.returncode in [0, 1]:  # bandit返回1表示发现问题但非错误
            try:
                data = json.loads(result.stdout)
                issues = {
                    'high': 0,
                    'medium': 0,
                    'low': 0
                }

                for result in data.get('results', []):
                    severity = result.get('issue_severity', 'LOW').lower()
                    if severity in issues:
                        issues[severity] += 1

                return issues
            except json.JSONDecodeError:
                self.log("解析代码扫描结果失败", "ERROR")

        return {'high': 0, 'medium': 0, 'low': 0}

    def check_security_best_practices(self) -> Dict:
        """检查安全最佳实践"""
        self.log("检查安全最佳实践...", "INFO")

        score = 100
        issues = []

        # 检查 .env 文件权限
        env_files = list(self.project_root.glob(".env*"))
        for env_file in env_files:
            if env_file.name.startswith('.env') and not env_file.name.endswith('.example'):
                try:
                    stat = env_file.stat()
                    mode = oct(stat.st_mode)[-3:]
                    if mode != '600':
                        score -= 10
                        issues.append(f"{env_file.name} 权限应该是 600，当前是 {mode}")
                except:
                    pass

        # 检查是否有敏感文件在版本控制中
        sensitive_patterns = ['.pem', '.key', '.p12', '.pfx', 'secrets/']
        for pattern in sensitive_patterns:
            result = subprocess.run(
                ["git", "ls-files", pattern],
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                score -= 20
                issues.append(f"发现敏感文件在版本控制中: {pattern}")

        # 检查是否有硬编码密码（简单检查）
        result = subprocess.run(
            ["grep", "-r", "password\\s*=\\s*['\"][^'\"]+['\"]", "src/", "--include=*.py"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            score -= 15
            issues.append("发现可能的硬编码密码")

        # 检查是否有安全配置文件
        security_configs = ['.bandit', '.pre-commit-config.yaml', 'security-check.sh']
        for config in security_configs:
            if not (self.project_root / config).exists():
                score -= 5
                issues.append(f"缺少安全配置文件: {config}")

        return {
            'score': max(0, score),
            'issues': issues,
            'passed_checks': len(security_configs) - sum(1 for c in security_configs if not (self.project_root / c).exists())
        }

    def calculate_health_score(self, vulnerabilities: Dict, code_issues: Dict, practices: Dict) -> Dict:
        """计算安全健康度评分"""
        # 基础分100分
        score = 100

        # 根据漏洞扣分
        score -= vulnerabilities['critical'] * 30
        score -= vulnerabilities['high'] * 20
        score -= vulnerabilities['medium'] * 10
        score -= vulnerabilities['low'] * 5

        # 根据代码问题扣分
        score -= code_issues['high'] * 15
        score -= code_issues['medium'] * 10
        score -= code_issues['low'] * 5

        # 最佳实践加分
        score = min(100, score + (practices['score'] - 100) * 0.3)

        # 确保分数在0-100之间
        score = max(0, min(100, score))

        # 确定等级
        if score >= 90:
            grade = 'A'
            status = '优秀'
        elif score >= 80:
            grade = 'B'
            status = '良好'
        elif score >= 70:
            grade = 'C'
            status = '一般'
        elif score >= 60:
            grade = 'D'
            status = '较差'
        else:
            grade = 'F'
            status = '严重'

        return {
            'score': round(score, 1),
            'grade': grade,
            'status': status,
            'components': {
                'vulnerabilities': vulnerabilities,
                'code_issues': code_issues,
                'best_practices': practices
            }
        }

    def generate_trend_analysis(self, history: List[Dict]) -> Dict:
        """生成趋势分析"""
        if len(history) < 2:
            return {
                'trend': 'stable',
                'change': 0,
                'direction': 'unknown',
                'prediction': None
            }

        # 获取最近7天的数据
        recent = history[-7:]

        # 计算趋势
        scores = [entry['health_score'] for entry in recent]

        # 简单线性回归预测
        n = len(scores)
        if n < 2:
            return {'trend': 'stable', 'change': 0, 'direction': 'unknown', 'prediction': None}

        x_values = list(range(n))
        x_mean = sum(x_values) / n
        y_mean = sum(scores) / n

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, scores))
        denominator = sum((x - x_mean) ** 2 for x in x_values)

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        # 计算变化
        change = scores[-1] - scores[0]

        # 确定趋势
        if abs(slope) < 0.5:
            trend = 'stable'
            direction = '→'
        elif slope > 0:
            trend = 'improving'
            direction = '↗'
        else:
            trend = 'declining'
            direction = '↘'

        # 预测下一周的分数
        prediction = scores[-1] + slope * 7
        prediction = max(0, min(100, prediction))

        return {
            'trend': trend,
            'change': round(change, 1),
            'direction': direction,
            'slope': round(slope, 2),
            'prediction': round(prediction, 1),
            'confidence': 'high' if n >= 5 else 'medium'
        }

    def generate_report(self, health_data: Dict, trend: Dict, history: List[Dict]):
        """生成健康度报告"""
        report = f"""# 安全健康度报告

## 概览

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### 健康度评分

| 评分 | 等级 | 状态 | 趋势 |
|------|------|------|------|
| {health_data['score']}/100 | {health_data['grade']} | {health_data['status']} | {trend['direction']} {trend['trend']} |

### 趋势分析

- **变化**: {trend['change']}分 ({'+' if trend['change'] > 0 else ''}{trend['change']})
- **变化率**: {trend.get('slope', 0)}/天
- **预测下周**: {trend['prediction']}/100
- **置信度**: {trend['confidence']}

## 详细指标

### 1. 依赖漏洞

| 级别 | 数量 | 影响 |
|------|------|------|
| 严重 | {health_data['components']['vulnerabilities']['critical']} | -30分/个 |
| 高危 | {health_data['components']['vulnerabilities']['high']} | -20分/个 |
| 中危 | {health_data['components']['vulnerabilities']['medium']} | -10分/个 |
| 低危 | {health_data['components']['vulnerabilities']['low']} | -5分/个 |

### 2. 代码安全问题

| 级别 | 数量 | 影响 |
|------|------|------|
| 高危 | {health_data['components']['code_issues']['high']} | -15分/个 |
| 中危 | {health_data['components']['code_issues']['medium']} | -10分/个 |
| 低危 | {health_data['components']['code_issues']['low']} | -5分/个 |

### 3. 安全最佳实践

- **得分**: {health_data['components']['best_practices']['score']}/100
- **通过检查**: {health_data['components']['best_practices']['passed_checks']}/4
- **问题**: {len(health_data['components']['best_practices']['issues'])}个

## 历史记录

最近7天的评分：

"""

        # 添加最近7天的历史
        recent_history = history[-7:]
        for entry in recent_history:
            date = entry['date']
            score = entry['health_score']
            grade = entry.get('grade', 'N/A')
            report += f"- {date}: {score}/100 ({grade})\n"

        # 添加改进建议
        report += f"""
## 改进建议

"""

        if health_data['score'] < 80:
            if health_data['components']['vulnerabilities']['critical'] > 0:
                report += "1. **紧急**: 立即修复所有严重漏洞\n"
            if health_data['components']['vulnerabilities']['high'] > 0:
                report += "2. **高优先级**: 修复高危漏洞\n"
            if health_data['components']['code_issues']['high'] > 0:
                report += "3. **高优先级**: 修复高危代码安全问题\n"

        if len(health_data['components']['best_practices']['issues']) > 0:
            report += "\n### 最佳实践问题\n\n"
            for issue in health_data['components']['best_practices']['issues']:
                report += f"- {issue}\n"

        report += f"""
## 自动化

- 每日自动运行: `python scripts/security/security_health_tracker.py`
- CI/CD集成: [Security Health Check](../../.github/workflows/security-health.yml)
- 历史数据: [health_history.json](./health_history.json)

---

*此报告由安全健康度跟踪器自动生成*
"""

        with open(self.report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        self.log(f"报告已生成: {self.report_file.relative_to(self.project_root)}", "SUCCESS")

    def run(self):
        """运行健康度检查"""
        self.log("=" * 70)
        self.log("开始安全健康度评估...", "SUCCESS")
        self.log("=" * 70)

        # 运行各种检查
        vulnerabilities = self.run_dependency_audit()
        code_issues = self.run_code_scan()
        practices = self.check_security_best_practices()

        # 计算健康度
        health_score = self.calculate_health_score(vulnerabilities, code_issues, practices)

        # 加载历史
        history = self.load_history()

        # 添加新记录
        new_record = {
            'date': datetime.now().isoformat(),
            'health_score': health_score['score'],
            'grade': health_score['grade'],
            'status': health_score['status'],
            'vulnerabilities': vulnerabilities,
            'code_issues': code_issues,
            'best_practices_score': practices['score']
        }

        history.append(new_record)

        # 保留最近90天的记录
        cutoff_date = datetime.now() - timedelta(days=90)
        history = [entry for entry in history
                  if datetime.fromisoformat(entry['date']) > cutoff_date]

        # 保存历史
        self.save_history(history)

        # 生成趋势分析
        trend = self.generate_trend_analysis(history)

        # 保存趋势数据
        with open(self.trend_file, 'w') as f:
            json.dump({
                'current': health_score,
                'trend': trend,
                'history': history[-30:]  # 保存最近30天
            }, f, indent=2, default=str)

        # 生成报告
        self.generate_report(health_score, trend, history)

        # 输出结果
        self.log("\n" + "=" * 70)
        self.log("安全健康度评估完成！", "SUCCESS")
        self.log(f"当前评分: {health_score['score']}/100 ({health_score['grade']})", "HIGHLIGHT")
        self.log(f"状态: {health_score['status']}", "INFO")
        self.log(f"趋势: {trend['direction']} {trend['trend']} ({trend['change']}分)", "INFO")
        self.log("=" * 70)

        return health_score, trend


if __name__ == "__main__":
    tracker = SecurityHealthTracker()
    score, trend = tracker.run()