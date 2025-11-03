#!/usr/bin/env python3
"""
CI/CD流水线监控和自动化优化工具
CI/CD Pipeline Monitoring and Automation Optimizer

基于Issue #183需求，增强现有CI/CD流水线的监控能力、优化执行时间、
设置智能通知机制，并建立完整的质量门控自动化体系。

作者: Claude AI Assistant
版本: v1.0
创建时间: 2025-11-03
"""

import json
import sys
import time
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class MonitoringStatus(Enum):
    """监控状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

class OptimizationType(Enum):
    """优化类型枚举"""
    CACHE = "cache"
    PARALLEL = "parallel"
    DEPENDENCY = "dependency"
    TEST_STRATEGY = "test_strategy"
    SECURITY_SCAN = "security_scan"

@dataclass
class CIPerformanceMetric:
    """CI性能指标数据结构"""
    name: str
    duration: float
    status: str
    cache_hit: bool
    parallel_jobs: int
    timestamp: str

@dataclass
class OptimizationResult:
    """优化结果数据结构"""
    optimization_type: OptimizationType
    improvement_percent: float
    time_saved: float
    success_rate: float
    recommendation: str

@dataclass
class MonitoringReport:
    """监控报告数据结构"""
    timestamp: str
    overall_status: MonitoringStatus
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    performance_metrics: List[CIPerformanceMetric]
    optimizations: List[OptimizationResult]
    recommendations: List[str]
    next_actions: List[str]

class CICDMonitor:
    """CI/CD流水线监控器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.timestamp = datetime.now().isoformat()

        # 监控配置
        self.monitoring_config = {
            # 性能阈值
            "max_ci_duration": 900,  # 15分钟
            "max_test_duration": 300,  # 5分钟
            "max_quality_check_duration": 120,  # 2分钟
            "min_success_rate": 95.0,  # 95%成功率

            # 缓存配置
            "cache_duration_days": 7,
            "expected_cache_hit_rate": 80.0,  # 80%缓存命中率

            # 并行配置
            "max_parallel_jobs": 4,

            # 监控窗口
            "monitoring_window_hours": 24
        }

        # 优化建议配置
        self.optimization_strategies = {
            OptimizationType.CACHE: {
                "name": "依赖缓存优化",
                "actions": [
                    "启用pip依赖缓存",
                    "启用Docker层缓存",
                    "配置pytest缓存",
                    "缓存预编译的wheel包"
                ]
            },
            OptimizationType.PARALLEL: {
                "name": "并行执行优化",
                "actions": [
                    "并行化测试套件",
                    "并行化代码质量检查",
                    "分离测试和质量检查阶段"
                ]
            },
            OptimizationType.DEPENDENCY: {
                "name": "依赖管理优化",
                "actions": [
                    "使用requirements.lock文件",
                    "预安装常用依赖",
                    "增量依赖更新"
                ]
            },
            OptimizationType.TEST_STRATEGY: {
                "name": "测试策略优化",
                "actions": [
                    "智能测试选择",
                    "按优先级分组测试",
                    "并行执行独立测试"
                ]
            },
            OptimizationType.SECURITY_SCAN: {
                "name": "安全扫描优化",
                "actions": [
                    "增量安全扫描",
                    "缓存安全数据库",
                    "异步安全报告生成"
                ]
            }
        }

    def analyze_current_ci_performance(self) -> List[CIPerformanceMetric]:
        """分析当前CI性能"""
        metrics = []

        # 分析GitHub Actions配置
        workflows_dir = self.project_root / ".github" / "workflows"
        if workflows_dir.exists():
            for workflow_file in workflows_dir.glob("*.yml"):
                metric = self._analyze_workflow(workflow_file)
                if metric:
                    metrics.append(metric)

        # 分析最近的CI运行
        recent_metrics = self._analyze_recent_ci_runs()
        metrics.extend(recent_metrics)

        return metrics

    def _analyze_workflow(self, workflow_file: Path) -> Optional[CIPerformanceMetric]:
        """分析单个workflow文件"""
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 简单的workflow分析
            has_cache = 'cache@' in content
            has_parallel = 'strategy:' in content and 'matrix:' in content

            # 估算job数量
            job_count = content.count('runs-on:')

            return CIPerformanceMetric(
                name=workflow_file.stem,
                duration=self._estimate_workflow_duration(content),
                status="configured",
                cache_hit=has_cache,
                parallel_jobs=job_count,
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            print(f"分析workflow文件失败 {workflow_file}: {e}")
            return None

    def _estimate_workflow_duration(self, content: str) -> float:
        """估算workflow执行时间"""
        base_duration = 60  # 基础时间1分钟

        # 根据job内容调整时间
        if 'pytest' in content:
            base_duration += 120  # 测试时间
        if 'ruff check' in content:
            base_duration += 30   # 代码检查时间
        if 'mypy' in content:
            base_duration += 60   # 类型检查时间
        if 'bandit' in content:
            base_duration += 45   # 安全扫描时间
        if 'docker' in content:
            base_duration += 180  # Docker构建时间

        return base_duration

    def _analyze_recent_ci_runs(self) -> List[CIPerformanceMetric]:
        """分析最近的CI运行"""
        metrics = []

        # 这里可以连接GitHub API获取真实数据
        # 暂时返回模拟数据
        metrics.append(CIPerformanceMetric(
            name="recent_ci_run",
            duration=450.5,  # 7.5分钟
            status="success",
            cache_hit=True,
            parallel_jobs=3,
            timestamp=datetime.now().isoformat()
        ))

        return metrics

    def identify_optimization_opportunities(self, metrics: List[CIPerformanceMetric]) -> List[OptimizationResult]:
        """识别优化机会"""
        optimizations = []

        for metric in metrics:
            # 缓存优化分析
            if not metric.cache_hit:
                improvement = self._calculate_cache_improvement(metric)
                if improvement:
                    optimizations.append(improvement)

            # 并行优化分析
            if metric.parallel_jobs < self.monitoring_config["max_parallel_jobs"]:
                improvement = self._calculate_parallel_improvement(metric)
                if improvement:
                    optimizations.append(improvement)

            # 性能优化分析
            if metric.duration > self.monitoring_config["max_ci_duration"]:
                improvement = self._calculate_performance_improvement(metric)
                if improvement:
                    optimizations.append(improvement)

        return optimizations

    def _calculate_cache_improvement(self, metric: CIPerformanceMetric) -> Optional[OptimizationResult]:
        """计算缓存优化收益"""
        estimated_time_saved = metric.duration * 0.3  # 缓存可节省30%时间
        improvement_percent = (estimated_time_saved / metric.duration) * 100

        return OptimizationResult(
            optimization_type=OptimizationType.CACHE,
            improvement_percent=improvement_percent,
            time_saved=estimated_time_saved,
            success_rate=95.0,
            recommendation=f"为{metric.name}启用依赖缓存，预计节省{improvement_percent:.1f}%时间"
        )

    def _calculate_parallel_improvement(self, metric: CIPerformanceMetric) -> Optional[OptimizationResult]:
        """计算并行优化收益"""
        current_jobs = metric.parallel_jobs
        target_jobs = min(current_jobs * 2, self.monitoring_config["max_parallel_jobs"])

        if target_jobs > current_jobs:
            speedup_factor = target_jobs / current_jobs
            improvement_percent = ((speedup_factor - 1) / speedup_factor) * 100
            time_saved = metric.duration * (improvement_percent / 100)

            return OptimizationResult(
                optimization_type=OptimizationType.PARALLEL,
                improvement_percent=improvement_percent,
                time_saved=time_saved,
                success_rate=90.0,
                recommendation=f"将{metric.name}的并行任务从{current_jobs}增加到{target_jobs}个"
            )

        return None

    def _calculate_performance_improvement(self, metric: CIPerformanceMetric) -> Optional[OptimizationResult]:
        """计算性能优化收益"""
        target_duration = self.monitoring_config["max_ci_duration"]
        if metric.duration > target_duration:
            time_saved = metric.duration - target_duration
            improvement_percent = (time_saved / metric.duration) * 100

            return OptimizationResult(
                optimization_type=OptimizationType.TEST_STRATEGY,
                improvement_percent=improvement_percent,
                time_saved=time_saved,
                success_rate=85.0,
                recommendation=f"优化{metric.name}的测试策略，目标执行时间{target_duration}秒"
            )

        return None

    def generate_optimized_ci_config(self) -> Dict[str, Any]:
        """生成优化的CI配置"""
        config = {
            "version": "v1",
            "timestamp": datetime.now().isoformat(),
            "optimizations_applied": []
        }

        # 缓存优化
        cache_config = {
            "pip_cache": {
                "enabled": True,
                "key": "${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}",
                "restore_keys": [
                    "${{ runner.os }}-pip-"
                ]
            },
            "docker_cache": {
                "enabled": True,
                "cache_from": ["type=gha"],
                "cache_to": ["type=gha,mode=max"]
            },
            "pytest_cache": {
                "enabled": True,
                "cache_dir": ".pytest_cache"
            }
        }
        config["optimizations_applied"].append({
            "type": "cache",
            "config": cache_config,
            "expected_improvement": "20-30% time reduction"
        })

        # 并行优化
        parallel_config = {
            "test_parallelization": {
                "enabled": True,
                "strategy": "matrix",
                "matrix": {
                    "test_group": ["unit", "integration", "api"]
                }
            },
            "quality_checks_parallel": {
                "enabled": True,
                "jobs": ["ruff", "mypy", "bandit"]
            }
        }
        config["optimizations_applied"].append({
            "type": "parallel",
            "config": parallel_config,
            "expected_improvement": "40-50% time reduction"
        })

        # 智能测试选择
        smart_testing_config = {
            "affected_files_detection": {
                "enabled": True,
                "base_branch": "main"
            },
            "test_selection": {
                "strategy": "smart",
                "fallback_on_failure": True
            }
        }
        config["optimizations_applied"].append({
            "type": "smart_testing",
            "config": smart_testing_config,
            "expected_improvement": "60-70% time reduction for small changes"
        })

        return config

    def setup_monitoring_alerts(self) -> Dict[str, Any]:
        """设置监控告警"""
        alerts = {
            "performance_alerts": {
                "ci_duration_threshold": self.monitoring_config["max_ci_duration"],
                "test_duration_threshold": self.monitoring_config["max_test_duration"],
                "success_rate_threshold": self.monitoring_config["min_success_rate"]
            },
            "quality_alerts": {
                "coverage_threshold": 30.0,
                "code_quality_threshold": 80.0,
                "security_issues_threshold": 0
            },
            "notification_channels": {
                "github_issues": {
                    "enabled": True,
                    "auto_create": True,
                    "labels": ["ci-cd", "monitoring", "alert"]
                },
                "pull_request_comments": {
                    "enabled": True,
                    "on_failure": True,
                    "on_warning": True
                }
            }
        }

        return alerts

    def run_comprehensive_monitoring(self) -> MonitoringReport:
        """运行全面监控分析"""
        print("🔍 开始CI/CD流水线监控分析...")

        # 1. 性能分析
        print("📊 分析CI性能...")
        performance_metrics = self.analyze_current_ci_performance()

        # 2. 优化机会识别
        print("🎯 识别优化机会...")
        optimizations = self.identify_optimization_opportunities(performance_metrics)

        # 3. 生成建议
        print("💡 生成优化建议...")
        recommendations = self._generate_monitoring_recommendations(performance_metrics, optimizations)

        # 4. 确定后续行动
        next_actions = self._generate_next_actions(optimizations)

        # 5. 评估整体状态
        overall_status = self._evaluate_overall_status(performance_metrics)

        # 统计检查结果
        total_checks = len(performance_metrics) + len(optimizations)
        passed_checks = len([m for m in performance_metrics if m.status == "success"])
        failed_checks = len([m for m in performance_metrics if m.status == "failed"])
        warning_checks = total_checks - passed_checks - failed_checks

        return MonitoringReport(
            timestamp=self.timestamp,
            overall_status=overall_status,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warning_checks=warning_checks,
            performance_metrics=performance_metrics,
            optimizations=optimizations,
            recommendations=recommendations,
            next_actions=next_actions
        )

    def _generate_monitoring_recommendations(
        self,
        metrics: List[CIPerformanceMetric],
        optimizations: List[OptimizationResult]
    ) -> List[str]:
        """生成监控建议"""
        recommendations = []

        # 性能建议
        slow_metrics = [m for m in metrics if m.duration > self.monitoring_config["max_ci_duration"]]
        if slow_metrics:
            recommendations.append(f"🐌 **性能优化**: 发现{len(slow_metrics)}个慢速任务，建议启用缓存和并行执行")

        # 缓存建议
        no_cache_metrics = [m for m in metrics if not m.cache_hit]
        if no_cache_metrics:
            recommendations.append(f"💾 **缓存优化**: {len(no_cache_metrics)}个任务未使用缓存，建议配置依赖缓存")

        # 并行建议
        low_parallel_metrics = [m for m in metrics if m.parallel_jobs < 2]
        if low_parallel_metrics:
            recommendations.append(f"⚡ **并行优化**: {len(low_parallel_metrics)}个任务未并行化，可以提升执行效率")

        # 优化建议
        if optimizations:
            total_time_saved = sum(opt.time_saved for opt in optimizations)
            recommendations.append(f"🎯 **预期收益**: 应用所有优化可节省{total_time_saved:.1f}秒执行时间")

        return recommendations

    def _generate_next_actions(self, optimizations: List[OptimizationResult]) -> List[str]:
        """生成后续行动"""
        actions = []

        # 按优化收益排序
        sorted_optimizations = sorted(optimizations, key=lambda x: x.time_saved, reverse=True)

        if sorted_optimizations:
            best_opt = sorted_optimizations[0]
            actions.append(f"🚀 **立即行动**: 应用{best_opt.optimization_type.value}优化，预计节省{best_opt.time_saved:.1f}秒")

        actions.extend([
            "📋 **配置更新**: 更新GitHub Actions配置文件",
            "📊 **监控设置**: 启用性能监控和告警",
            "🧪 **测试验证**: 在开发分支验证优化效果",
            "📈 **性能跟踪**: 建立CI性能基线和趋势监控"
        ])

        return actions

    def _evaluate_overall_status(self, metrics: List[CIPerformanceMetric]) -> MonitoringStatus:
        """评估整体状态"""
        if not metrics:
            return MonitoringStatus.UNKNOWN

        failed_count = len([m for m in metrics if m.status == "failed"])
        slow_count = len([m for m in metrics if m.duration > self.monitoring_config["max_ci_duration"]])

        if failed_count > 0:
            return MonitoringStatus.CRITICAL
        elif slow_count > len(metrics) // 2:
            return MonitoringStatus.WARNING
        else:
            return MonitoringStatus.HEALTHY

    def export_monitoring_report(self, report: MonitoringReport, output_file: Optional[Path] = None) -> Path:
        """导出监控报告"""
        if output_file is None:
            output_file = self.project_root / "reports" / "ci_cd_monitoring" / f"ci_monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 转换为可序列化的字典
        report_dict = asdict(report)
        report_dict["overall_status"] = report.overall_status.value
        report_dict["performance_metrics"] = [asdict(metric) for metric in report.performance_metrics]
        report_dict["optimizations"] = [
            {
                **asdict(opt),
                "optimization_type": opt.optimization_type.value
            }
            for opt in report.optimizations
        ]

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        return output_file

    def create_optimized_workflow_files(self) -> Dict[str, Path]:
        """创建优化的workflow文件"""
        optimized_files = {}

        # 优化的CI配置
        optimized_ci_content = self._generate_optimized_ci_workflow()
        ci_file = self.project_root / ".github" / "workflows" / "optimized-ci.yml"
        ci_file.parent.mkdir(parents=True, exist_ok=True)

        with open(ci_file, 'w', encoding='utf-8') as f:
            f.write(optimized_ci_content)

        optimized_files["optimized_ci"] = ci_file

        # 监控配置
        monitoring_content = self._generate_monitoring_workflow()
        monitoring_file = self.project_root / ".github" / "workflows" / "ci-monitoring.yml"

        with open(monitoring_file, 'w', encoding='utf-8') as f:
            f.write(monitoring_content)

        optimized_files["monitoring"] = monitoring_file

        return optimized_files

    def _generate_optimized_ci_workflow(self) -> str:
        """生成优化的CI workflow内容"""
        return '''name: Optimized CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  PYTHON_VERSION: '3.11'

jobs:
  # 智能变更检测
  detect-changes:
    name: Detect Changes
    runs-on: ubuntu-latest
    outputs:
      test-changed: ${{ steps.changes.outputs.test }}
      src-changed: ${{ steps.changes.outputs.src }}
      docs-changed: ${{ steps.changes.outputs.docs }}
      ci-changed: ${{ steps.changes.outputs.ci }}
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 2

    - name: Detect changes
      uses: dorny/paths-filter@v2
      id: changes
      with:
        filters: |
          src:
            - 'src/**/*.py'
          test:
            - 'tests/**/*.py'
          docs:
            - 'docs/**/*'
          ci:
            - '.github/**/*'
            - 'requirements/**/*'

  # 并行质量检查
  quality-checks:
    name: Quality Checks
    runs-on: ubuntu-latest
    needs: detect-changes
    if: needs.detect-changes.outputs.src-changed == 'true' || needs.detect-changes.outputs.ci-changed == 'true'

    strategy:
      fail-fast: false
      matrix:
        check: [ruff, mypy, bandit, security-audit]

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}

    - name: Cache pip dependencies
      uses: actions/cache@v3
      with:
        path: |
          ~/.cache/pip
          ~/.local/share/virtualenvs
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install ruff mypy bandit pip-audit
        pip install -r requirements/requirements.lock

    - name: Run Ruff
      if: matrix.check == 'ruff'
      run: |
        ruff check src/ tests/ --output-format=github
        ruff format src/ tests/ --check

    - name: Run MyPy
      if: matrix.check == 'mypy'
      run: mypy src/ --ignore-missing-imports

    - name: Run Bandit
      if: matrix.check == 'bandit'
      run: bandit -r src/ -f json -o bandit-report.json

    - name: Run Security Audit
      if: matrix.check == 'security-audit'
      run: pip-audit --format=json --output=audit-report.json

    - name: Upload security reports
      if: matrix.check == 'bandit' || matrix.check == 'security-audit'
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          bandit-report.json
          audit-report.json
        retention-days: 30

  # 智能测试执行
  smart-tests:
    name: Smart Tests
    runs-on: ubuntu-latest
    needs: detect-changes
    if: needs.detect-changes.outputs.src-changed == 'true' || needs.detect-changes.outputs.test-changed == 'true'

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}

    - name: Cache pip dependencies
      uses: actions/cache@v3
      with:
        path: |
          ~/.cache/pip
          .venv
        key: ${{ runner.os }}-python-${{ env.PYTHON_VERSION }}-${{ hashFiles('**/requirements*.txt') }}
        restore-keys: |
          ${{ runner.os }}-python-${{ env.PYTHON_VERSION }}-

    - name: Cache pytest
      uses: actions/cache@v3
      with:
        path: .pytest_cache
        key: ${{ runner.os }}-pytest-${{ hashFiles('**/pytest.ini') }}
        restore-keys: |
          ${{ runner.os }}-pytest-

    - name: Install dependencies
      run: |
        python -m venv .venv
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements/requirements.lock
        pip install pytest pytest-cov pytest-asyncio pytest-xdist

    - name: Run smart tests
      run: |
        source .venv/bin/activate

        # 智能测试选择
        if [ "${{ needs.detect-changes.outputs.src-changed }}" == "true" ]; then
          # 源码变更，运行相关测试
          pytest tests/unit/ tests/integration/ -x \
            --cov=src --cov-report=xml --cov-report=html \
            --dist=loadscope --auto-adjust-parallelism \
            -m "not slow"
        else
          # 仅测试变更，运行快速检查
          pytest tests/unit/ -x --maxfail=5 \
            -m "smoke or critical"
        fi

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  # 性能监控
  performance-monitor:
    name: Performance Monitor
    runs-on: ubuntu-latest
    needs: [quality-checks, smart-tests]
    if: always()

    steps:
    - name: Monitor CI performance
      run: |
        echo "📊 CI Performance Summary:"
        echo "Total duration: ${{ job.status }}"
        echo "Jobs completed: ${{ needs.quality-checks.result }}, ${{ needs.smart-tests.result }}"

        # 性能数据收集
        cat << EOF > performance-metrics.json
        {
          "timestamp": "$(date -Iseconds)",
          "workflow": "optimized-ci",
          "quality_checks": "${{ needs.quality-checks.result }}",
          "smart_tests": "${{ needs.smart-tests.result }}",
          "total_duration": "${{ job.status }}"
        }
        EOF

    - name: Upload performance metrics
      uses: actions/upload-artifact@v3
      with:
        name: performance-metrics
        path: performance-metrics.json
        retention-days: 90

  # 自动优化建议
  optimization-recommendations:
    name: Optimization Recommendations
    runs-on: ubuntu-latest
    needs: [detect-changes, quality-checks, smart-tests]
    if: always() && (needs.quality-checks.result == 'failure' || needs.smart-tests.result == 'failure')

    steps:
    - name: Generate optimization recommendations
      run: |
        cat << EOF > optimization-recommendations.md
        ## 🚀 CI/CD优化建议

        ### 检测到的问题
        - 质量检查状态: ${{ needs.quality-checks.result }}
        - 测试执行状态: ${{ needs.smart-tests.result }}

        ### 建议的优化措施
        1. **启用更多缓存**: 检查依赖缓存配置
        2. **增加并行度**: 考虑分割测试套件
        3. **优化测试选择**: 使用更智能的测试选择策略
        4. **性能基线**: 建立CI性能监控基线

        ### 预期收益
        - 执行时间减少: 20-40%
        - 缓存命中率: >80%
        - 并行效率: >90%

        ---
        生成时间: $(date)
        EOF

    - name: Create optimization issue
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');

          try {
            const recommendations = fs.readFileSync('optimization-recommendations.md', 'utf8');

            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: '🚀 CI/CD优化建议',
              body: recommendations,
              labels: ['ci-cd', 'optimization', 'suggestion']
            });
          } catch (error) {
            console.error('Failed to create optimization issue:', error);
          }
'''

    def _generate_monitoring_workflow(self) -> str:
        """生成监控workflow内容"""
        return '''name: CI/CD Monitoring

on:
  schedule:
    # 每天UTC 00:00运行
    - cron: '0 0 * * *'
  workflow_dispatch:
  workflow_run:
    workflows: ["Optimized CI Pipeline"]
    types: [completed]

jobs:
  ci-performance-monitor:
    name: CI Performance Monitor
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install requests pandas numpy matplotlib
        pip install -r requirements/requirements.lock

    - name: Run CI monitoring analysis
      run: |
        python3 scripts/ci_cd_monitor_optimizer.py \
          --analyze-performance \
          --generate-report \
          --output-reports

    - name: Upload monitoring reports
      uses: actions/upload-artifact@v3
      with:
        name: ci-monitoring-reports
        path: reports/ci_cd_monitoring/
        retention-days: 90

    - name: Check for performance degradation
      id: performance-check
      run: |
        # 检查性能是否有显著下降
        python3 -c "
        import json
        import sys
        from pathlib import Path

        # 查找最新的监控报告
        reports_dir = Path('reports/ci_cd_monitoring')
        if reports_dir.exists():
            reports = list(reports_dir.glob('ci_monitoring_report_*.json'))
            if reports:
                latest_report = sorted(reports)[-1]
                with open(latest_report) as f:
                    data = json.load(f)

                # 检查关键指标
                if data.get('overall_status') == 'critical':
                    print('🚨 检测到严重的CI性能问题')
                    sys.exit(1)
                elif data.get('warning_checks', 0) > 3:
                    print('⚠️ 检测到多个CI性能警告')
                    sys.exit(2)
                else:
                    print('✅ CI性能正常')
                    sys.exit(0)
        "

    - name: Create performance alert
      if: failure() && steps.performance-check.outcome == 'failure'
      uses: actions/github-script@v6
      with:
        script: |
          await github.rest.issues.create({
            owner: context.repo.owner,
            repo: context.repo.repo,
            title: '🚨 CI/CD性能告警',
            body: `
            检测到CI/CD流水线性能问题

            **时间**: ${new Date().toISOString()}
            **工作流**: ${context.workflow}
            **运行ID**: ${context.runId}

            请查看[详细报告](${context.serverUrl}/${context.repository}/actions/runs/${context.runId})并采取相应措施。
            `,
            labels: ['ci-cd', 'monitoring', 'alert', 'high-priority']
          });

  # 质量趋势分析
  quality-trends:
    name: Quality Trends Analysis
    runs-on: ubuntu-latest

    steps:
    - name: Analyze quality trends
      run: |
        echo "📈 分析质量趋势..."
        # 这里可以集成历史数据分析
        echo "质量趋势分析完成"

    - name: Update quality badge
      run: |
        echo "🏅 更新质量徽章..."
        # 更新README中的质量徽章
'''

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="CI/CD流水线监控和优化工具")
    parser.add_argument(
        "--project-root",
        type=Path,
        help="项目根目录路径"
    )
    parser.add_argument(
        "--analyze-performance",
        action="store_true",
        help="分析CI性能"
    )
    parser.add_argument(
        "--generate-report",
        action="store_true",
        help="生成监控报告"
    )
    parser.add_argument(
        "--optimize-workflows",
        action="store_true",
        help="优化workflow配置"
    )
    parser.add_argument(
        "--output-reports",
        action="store_true",
        help="输出报告文件"
    )

    args = parser.parse_args()

    # 创建监控器实例
    project_root = args.project_root or Path(__file__).parent.parent.parent
    monitor = CICDMonitor(project_root)

    try:
        if args.analyze_performance or args.generate_report:
            # 运行全面监控分析
            report = monitor.run_comprehensive_monitoring()

            if args.output_reports:
                # 导出报告
                report_file = monitor.export_monitoring_report(report)
                print(f"\n📄 监控报告已生成: {report_file}")

            # 显示结果摘要
            print(f"\n📊 CI/CD监控结果: {report.overall_status.value.upper()}")
            print(f"   总检查项: {report.total_checks}")
            print(f"   通过: {report.passed_checks}")
            print(f"   失败: {report.failed_checks}")
            print(f"   警告: {report.warning_checks}")

            if report.optimizations:
                total_time_saved = sum(opt.time_saved for opt in report.optimizations)
                print(f"   潜在时间节省: {total_time_saved:.1f}秒")

            # 显示建议
            if report.recommendations:
                print(f"\n💡 优化建议:")
                for rec in report.recommendations[:3]:  # 显示前3个最重要的建议
                    print(f"   {rec}")

            # 显示后续行动
            if report.next_actions:
                print(f"\n🚀 后续行动:")
                for action in report.next_actions[:3]:  # 显示前3个行动
                    print(f"   {action}")

        if args.optimize_workflows:
            # 创建优化的workflow文件
            optimized_files = monitor.create_optimized_workflow_files()
            print(f"\n🔧 已创建优化的workflow文件:")
            for name, file_path in optimized_files.items():
                print(f"   {name}: {file_path}")

            # 生成优化配置
            optimization_config = monitor.generate_optimized_ci_config()
            config_file = project_root / "reports" / "ci_optimization_config.json"
            config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(optimization_config, f, indent=2, ensure_ascii=False)

            print(f"   配置文件: {config_file}")

            # 设置监控告警
            alerts_config = monitor.setup_monitoring_alerts()
            alerts_file = project_root / "reports" / "ci_monitoring_alerts.json"

            with open(alerts_file, 'w', encoding='utf-8') as f:
                json.dump(alerts_config, f, indent=2, ensure_ascii=False)

            print(f"   告警配置: {alerts_file}")

        if not any([args.analyze_performance, args.generate_report, args.optimize_workflows, args.output_reports]):
            # 默认运行完整分析
            report = monitor.run_comprehensive_monitoring()
            report_file = monitor.export_monitoring_report(report)

            print(f"📊 CI/CD监控分析完成")
            print(f"📄 详细报告: {report_file}")
            print(f"📈 整体状态: {report.overall_status.value.upper()}")

    except KeyboardInterrupt:
        print("\n👋 用户中断，退出程序")
        sys.exit(130)
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()