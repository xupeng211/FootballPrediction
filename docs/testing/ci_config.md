# CI/CD配置指南

本文档详细说明足球预测系统的CI/CD配置，包括GitHub Actions工作流、覆盖率监控、自动化检查等。

## 📋 目录

- [GitHub Actions配置](#github-actions配置)
  - [主工作流](#主工作流)
  - [PR检查工作流](#pr检查工作流)
  - [定时任务工作流](#定时任务工作流)
  - [部署工作流](#部署工作流)
- [覆盖率监控配置](#覆盖率监控配置)
  - [Codecov集成](#codecov集成)
  - [覆盖率报告生成](#覆盖率报告生成)
  - [覆盖率趋势分析](#覆盖率趋势分析)
- [自动化检查配置](#自动化检查配置)
  - [代码质量检查](#代码质量检查)
  - [安全检查](#安全检查)
  - [性能检查](#性能检查)
- [Docker配置](#docker配置)
  - [CI镜像构建](#ci镜像构建)
  - [测试环境配置](#测试环境配置)
  - [多环境部署](#多环境部署)
- [通知与报告](#通知与报告)
  - [Slack通知](#slack通知)
  - [邮件报告](#邮件报告)
  - [仪表板集成](#仪表板集成)

---

## GitHub Actions配置

### 主工作流

```yaml
# .github/workflows/main.yml
name: Main CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '18'
  POSTGRES_VERSION: '15'
  REDIS_VERSION: '7'

jobs:
  test:
    name: Test Suite
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:${{ env.POSTGRES_VERSION }}
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: football_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:${{ env.REDIS_VERSION }}
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    strategy:
      matrix:
        test-type: [unit, integration, e2e]

    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        cache: 'pip'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Setup database
      run: |
        make db-init
        make db-migrate

    - name: Run tests
      run: |
        if [ "${{ matrix.test-type }}" == "unit" ]; then
          make test-unit
        elif [ "${{ matrix.test-type }}" == "integration" ]; then
          make test-integration
        else
          make test-e2e
        fi

    - name: Generate coverage report
      if: matrix.test-type == 'unit'
      run: |
        make coverage-report

    - name: Upload coverage to Codecov
      if: matrix.test-type == 'unit'
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
        fail_ci_if_error: false

  quality:
    name: Code Quality
    runs-on: ubuntu-latest
    needs: test

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        cache: 'pip'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt

    - name: Run linting
      run: make lint

    - name: Run type checking
      run: make type-check

    - name: Run security check
      run: make security-check

    - name: Check formatting
      run: make fmt-check

  performance:
    name: Performance Test
    runs-on: ubuntu-latest
    needs: test
    if: github.ref == 'refs/heads/main'

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run performance benchmarks
      run: make benchmark

    - name: Upload performance results
      uses: actions/upload-artifact@v3
      with:
        name: performance-results
        path: performance-reports/

  build:
    name: Build and Deploy
    runs-on: ubuntu-latest
    needs: [test, quality, performance]
    if: github.ref == 'refs/heads/main'

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Login to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: football-prediction/api
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-
          type=raw,value=latest,enable={{is_default_branch}}

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        file: Dockerfile
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

    - name: Deploy to staging
      if: github.ref == 'refs/heads/main'
      run: |
        echo "Deploying to staging environment..."
        # Add deployment commands here
```

### PR检查工作流

```yaml
# .github/workflows/pr-check.yml
name: PR Check

on:
  pull_request:
    types: [opened, synchronize, reopened, labeled]

jobs:
  pr-validation:
    name: PR Validation
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Check PR description
      uses: actions/github-script@v6
      with:
        script: |
          const { data: pr } = await github.rest.pulls.get({
            owner: context.repo.owner,
            repo: context.repo.repo,
            pull_number: context.issue.number
          });

          if (!pr.body || pr.body.length < 50) {
            core.setFailed('PR description must be at least 50 characters long');
          }

    - name: Check for breaking changes
      run: |
        if git diff --name-only HEAD~1 HEAD | grep -q "BREAKING_CHANGE"; then
          echo "::warning::Breaking change detected"
        fi

    - name: Run quick tests
      run: make test-quick

    - name: Check coverage threshold
      run: make coverage-gate

    - name: Comment PR with results
      uses: actions/github-script@v6
      with:
        script: |
          const { data: pr } = await github.rest.pulls.get({
            owner: context.repo.owner,
            repo: context.repo.repo,
            pull_number: context.issue.number
          });

          const comment = `
          ## PR Check Results ✅

          - **Tests**: All tests passed
          - **Coverage**: Above threshold
          - **Quality**: All checks passed

          This PR is ready for review! 🎉
          `;

          await github.rest.issues.createComment({
            owner: context.repo.owner,
            repo: context.repo.repo,
            issue_number: context.issue.number,
            body: comment
          });
```

### 定时任务工作流

```yaml
# .github/workflows/scheduled.yml
name: Scheduled Tasks

on:
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨2点
  workflow_dispatch:

jobs:
  daily-maintenance:
    name: Daily Maintenance
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run daily maintenance tasks
      run: |
        python scripts/daily_maintenance.py

    - name: Generate daily report
      run: |
        python scripts/generate_daily_report.py

    - name: Upload report
      uses: actions/upload-artifact@v3
      with:
        name: daily-report
        path: reports/daily/

  weekly-cleanup:
    name: Weekly Cleanup
    runs-on: ubuntu-latest
    if: github.event.schedule == '0 2 * * 0'  # 每周日凌晨2点

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run weekly cleanup
      run: |
        python scripts/weekly_cleanup.py

    - name: Cleanup old artifacts
      uses: actions/github-script@v6
      with:
        script: |
          // Delete artifacts older than 30 days
          const artifacts = await github.rest.actions.listArtifactsForRepo({
            owner: context.repo.owner,
            repo: context.repo.repo,
            per_page: 100
          });

          const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);

          for (const artifact of artifacts.data.artifacts) {
            const artifactDate = new Date(artifact.created_at);
            if (artifactDate < thirtyDaysAgo) {
              await github.rest.actions.deleteArtifact({
                owner: context.repo.owner,
                repo: context.repo.repo,
                artifact_id: artifact.id
              });
            }
          }
```

### 部署工作流

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        default: 'staging'
        type: choice
        options:
        - staging
        - production

jobs:
  deploy:
    name: Deploy to ${{ github.event.inputs.environment || 'production' }}
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.environment || 'production' }}

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install deployment tools
      run: |
        python -m pip install --upgrade pip
        pip install ansible boto3 docker

    - name: Configure AWS credentials
      if: github.event.inputs.environment == 'production'
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1

    - name: Build application
      run: |
        make build

    - name: Deploy to staging
      if: github.event.inputs.environment == 'staging' || !github.event.inputs.environment
      run: |
        ansible-playbook -i ansible/staging.ini ansible/deploy.yml

    - name: Deploy to production
      if: github.event.inputs.environment == 'production'
      run: |
        ansible-playbook -i ansible/production.ini ansible/deploy.yml

    - name: Run post-deployment tests
      run: |
        python scripts/post_deployment_tests.py

    - name: Notify deployment
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ job.status }}
        channel: '#deployment'
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

---

## 覆盖率监控配置

### Codecov集成

```yaml
# codecov.yml
coverage:
  status:
    project:
      default:
        target: 80%
        threshold: 1%
        base: auto
    patch:
      default:
        target: 70%
        threshold: 1%
        base: auto

comment:
  layout: "reach,diff,flags,tree"
  behavior: default
  require_changes: false

ignore:
  - "tests/"
  - "src/migrations/"
  - "scripts/"
  - "docs/"
```

### 覆盖率报告生成

```python
# scripts/generate_coverage_report.py
import json
import os
import subprocess
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd

class CoverageReportGenerator:
    """覆盖率报告生成器"""

    def __init__(self):
        self.coverage_file = "coverage.json"
        self.history_file = "coverage_history.json"
        self.output_dir = "docs/coverage_reports"

    def generate_coverage_data(self):
        """生成覆盖率数据"""
        # 运行测试并生成覆盖率数据
        result = subprocess.run([
            "pytest", "--cov=src", "--cov-report=json"
        ], capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"Coverage generation failed: {result.stderr}")

        # 读取覆盖率数据
        with open(self.coverage_file, 'r') as f:
            coverage_data = json.load(f)

        return coverage_data

    def analyze_coverage_by_module(self, coverage_data):
        """分析模块覆盖率"""
        module_coverage = {}
        files = coverage_data.get('files', {})

        for file_path, file_data in files.items():
            if file_path.startswith('src/'):
                module = file_path.split('/')[1]
                if module not in module_coverage:
                    module_coverage[module] = []

                summary = file_data.get('summary', {})
                line_coverage = summary.get('percent_covered', 0)
                module_coverage[module].append(line_coverage)

        # 计算模块平均覆盖率
        module_avg = {}
        for module, coverages in module_coverage.items():
            module_avg[module] = sum(coverages) / len(coverages)

        return module_avg

    def generate_html_report(self, coverage_data):
        """生成HTML报告"""
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)

        # 生成HTML覆盖率报告
        subprocess.run([
            "pytest", "--cov=src", "--cov-report=html"
        ])

        # 移动HTML报告到指定目录
        import shutil
        if os.path.exists("htmlcov"):
            shutil.move("htmlcov", f"{self.output_dir}/html")

    def generate_visualization(self, coverage_data):
        """生成可视化图表"""
        module_coverage = self.analyze_coverage_by_module(coverage_data)

        # 创建柱状图
        fig, ax = plt.subplots(figsize=(12, 6))

        modules = list(module_coverage.keys())
        coverages = list(module_coverage.values())

        bars = ax.bar(modules, coverages)

        # 设置颜色
        for bar, coverage in zip(bars, coverages):
            if coverage >= 80:
                bar.set_color('green')
            elif coverage >= 60:
                bar.set_color('yellow')
            else:
                bar.set_color('red')

        # 添加标签和标题
        ax.set_xlabel('Module')
        ax.set_ylabel('Coverage %')
        ax.set_title('Test Coverage by Module')
        ax.set_ylim(0, 100)

        # 添加数值标签
        for bar, coverage in zip(bars, coverages):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                   f'{coverage:.1f}%', ha='center', va='bottom')

        # 保存图表
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/coverage_by_module.png')
        plt.close()

    def generate_trend_analysis(self):
        """生成趋势分析"""
        # 加载历史数据
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        else:
            history = []

        # 生成趋势图
        if len(history) > 1:
            df = pd.DataFrame(history)
            df['date'] = pd.to_datetime(df['timestamp'])

            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(df['date'], df['total_coverage'], marker='o', linewidth=2)
            ax.axhline(y=80, color='r', linestyle='--', label='Target (80%)')
            ax.axhline(y=85, color='g', linestyle='--', label='Goal (85%)')

            ax.set_xlabel('Date')
            ax.set_ylabel('Coverage %')
            ax.set_title('Test Coverage Trend')
            ax.legend()
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(f'{self.output_dir}/coverage_trend.png')
            plt.close()

    def generate_summary_report(self, coverage_data):
        """生成总结报告"""
        total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
        module_coverage = self.analyze_coverage_by_module(coverage_data)

        # 生成Markdown报告
        report = f"""# Coverage Report

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- **Total Coverage**: {total_coverage:.1f}%
- **Files Covered**: {len(coverage_data.get('files', {}))}
- **Lines of Code**: {coverage_data.get('totals', {}).get('num_statements', 0)}

## Module Coverage
| Module | Coverage | Status |
|--------|----------|---------|
"""

        for module, coverage in sorted(module_coverage.items()):
            status = "✅ Excellent" if coverage >= 80 else "⚠️ Needs Work" if coverage >= 60 else "❌ Poor"
            report += f"| {module} | {coverage:.1f}% | {status} |\n"

        report += f"""
## Recommendations
"""

        if total_coverage < 80:
            report += "- 🎯 Focus on increasing overall coverage to 80%+\n"

        for module, coverage in module_coverage.items():
            if coverage < 60:
                report += f"- 📈 Module {module} needs immediate attention ({coverage:.1f}%)\n"
            elif coverage < 80:
                report += f"- 🔧 Module {module} could be improved ({coverage:.1f}%)\n"

        # 保存报告
        with open(f'{self.output_dir}/summary.md', 'w') as f:
            f.write(report)

    def run_full_report(self):
        """运行完整报告生成"""
        print("Generating coverage report...")

        # 生成覆盖率数据
        coverage_data = self.generate_coverage_data()

        # 生成各种报告
        self.generate_html_report(coverage_data)
        self.generate_visualization(coverage_data)
        self.generate_trend_analysis()
        self.generate_summary_report(coverage_data)

        print(f"Coverage report generated in {self.output_dir}/")

if __name__ == "__main__":
    generator = CoverageReportGenerator()
    generator.run_full_report()
```

### 覆盖率趋势分析

```python
# scripts/coverage_monitor.py
import json
import os
import sqlite3
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
from typing import Dict, List, Any

class CoverageMonitor:
    """覆盖率监控工具"""

    def __init__(self, db_path="coverage_monitoring.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coverage_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                git_sha TEXT,
                branch TEXT,
                total_coverage REAL,
                module_coverage TEXT,
                test_count INTEGER,
                execution_time REAL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coverage_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                avg_coverage REAL,
                min_coverage REAL,
                max_coverage REAL,
                trend_direction TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def record_coverage(self, coverage_data: Dict[str, Any], git_sha: str = None, branch: str = None):
        """记录覆盖率数据"""
        total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
        module_coverage = json.dumps(self.analyze_module_coverage(coverage_data))

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO coverage_data (git_sha, branch, total_coverage, module_coverage)
            VALUES (?, ?, ?, ?)
        ''', (git_sha, branch, total_coverage, module_coverage))

        conn.commit()
        conn.close()

    def analyze_module_coverage(self, coverage_data: Dict[str, Any]) -> Dict[str, float]:
        """分析模块覆盖率"""
        module_coverage = {}
        files = coverage_data.get('files', {})

        for file_path, file_data in files.items():
            if file_path.startswith('src/'):
                module = file_path.split('/')[1]
                if module not in module_coverage:
                    module_coverage[module] = []

                summary = file_data.get('summary', {})
                line_coverage = summary.get('percent_covered', 0)
                module_coverage[module].append(line_coverage)

        # 计算模块平均覆盖率
        return {module: sum(coverages) / len(coverages)
                for module, coverages in module_coverage.items()}

    def get_coverage_trend(self, days: int = 30) -> pd.DataFrame:
        """获取覆盖率趋势"""
        conn = sqlite3.connect(self.db_path)

        query = '''
            SELECT timestamp, total_coverage, branch
            FROM coverage_data
            WHERE timestamp >= datetime('now', '-{} days')
            ORDER BY timestamp
        '''.format(days)

        df = pd.read_sql_query(query, conn)
        conn.close()

        return df

    def generate_trend_chart(self, days: int = 30):
        """生成趋势图"""
        df = self.get_coverage_trend(days)

        if df.empty:
            print("No coverage data available for trend analysis")
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # 整体趋势
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        ax1.plot(df['timestamp'], df['total_coverage'], marker='o', linewidth=2)
        ax1.axhline(y=80, color='r', linestyle='--', label='Target (80%)')
        ax1.axhline(y=85, color='g', linestyle='--', label='Goal (85%)')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Coverage %')
        ax1.set_title('Overall Coverage Trend')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 分支对比
        if 'branch' in df.columns and df['branch'].nunique() > 1:
            for branch in df['branch'].unique():
                branch_data = df[df['branch'] == branch]
                ax2.plot(branch_data['timestamp'], branch_data['total_coverage'],
                        marker='o', label=branch, linewidth=2)

            ax2.axhline(y=80, color='r', linestyle='--', alpha=0.5)
            ax2.axhline(y=85, color='g', linestyle='--', alpha=0.5)
            ax2.set_xlabel('Date')
            ax2.set_ylabel('Coverage %')
            ax2.set_title('Coverage by Branch')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        else:
            ax2.remove()

        plt.tight_layout()
        plt.savefig('docs/coverage_monitoring/trend_analysis.png')
        plt.close()

    def detect_coverage_regression(self, threshold: float = 2.0) -> List[Dict[str, Any]]:
        """检测覆盖率回归"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 获取最近两次的覆盖率数据
        cursor.execute('''
            SELECT timestamp, total_coverage, git_sha
            FROM coverage_data
            ORDER BY timestamp DESC
            LIMIT 2
        ''')

        results = cursor.fetchall()
        conn.close()

        regressions = []

        if len(results) >= 2:
            current_coverage = results[0][1]
            previous_coverage = results[1][1]

            if previous_coverage - current_coverage > threshold:
                regressions.append({
                    'timestamp': results[0][0],
                    'current_coverage': current_coverage,
                    'previous_coverage': previous_coverage,
                    'drop': previous_coverage - current_coverage,
                    'git_sha': results[0][2]
                })

        return regressions

    def generate_weekly_report(self):
        """生成周报告"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 获取本周数据
        cursor.execute('''
            SELECT AVG(total_coverage), MIN(total_coverage), MAX(total_coverage)
            FROM coverage_data
            WHERE timestamp >= datetime('now', '-7 days')
        ''')

        week_stats = cursor.fetchone()
        avg_coverage, min_coverage, max_coverage = week_stats

        # 获取上周数据对比
        cursor.execute('''
            SELECT AVG(total_coverage)
            FROM coverage_data
            WHERE timestamp >= datetime('now', '-14 days')
            AND timestamp < datetime('now', '-7 days')
        ''')

        last_week_avg = cursor.fetchone()[0]

        conn.close()

        # 生成报告
        report = f"""
# Weekly Coverage Report

## This Week's Performance
- **Average Coverage**: {avg_coverage:.1f}%
- **Minimum Coverage**: {min_coverage:.1f}%
- **Maximum Coverage**: {max_coverage:.1f}%

## Comparison with Last Week
- **Last Week Average**: {last_week_avg:.1f}%
- **Change**: {avg_coverage - last_week_avg:+.1f}%

## Module Performance
"""

        # 添加模块性能分析
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT module_coverage
            FROM coverage_data
            WHERE timestamp >= datetime('now', '-7 days')
        ''')

        module_data_list = cursor.fetchall()
        conn.close()

        # 分析模块性能
        if module_data_list:
            all_modules = {}
            for row in module_data_list:
                module_coverage = json.loads(row[0])
                for module, coverage in module_coverage.items():
                    if module not in all_modules:
                        all_modules[module] = []
                    all_modules[module].append(coverage)

            for module, coverages in all_modules.items():
                avg = sum(coverages) / len(coverages)
                status = "✅" if avg >= 80 else "⚠️" if avg >= 60 else "❌"
                report += f"- {status} {module}: {avg:.1f}%\n"

        return report

    def run_monitoring(self):
        """运行监控"""
        print("Running coverage monitoring...")

        # 检查覆盖率回归
        regressions = self.detect_coverage_regression()

        if regressions:
            print("⚠️ Coverage regression detected:")
            for regression in regressions:
                print(f"  - Drop of {regression['drop']:.1f}% detected")
                print(f"  - Current: {regression['current_coverage']:.1f}%")
                print(f"  - Previous: {regression['previous_coverage']:.1f}%")
                print(f"  - Commit: {regression['git_sha']}")

        # 生成趋势图
        self.generate_trend_chart()

        # 生成周报告
        weekly_report = self.generate_weekly_report()

        # 保存报告
        with open('docs/coverage_monitoring/weekly_report.md', 'w') as f:
            f.write(weekly_report)

        print("Monitoring completed. Reports saved to docs/coverage_monitoring/")
```

---

## 自动化检查配置

### 代码质量检查

```python
# scripts/quality_checks.py
import subprocess
import json
import os
from typing import Dict, List, Any
from datetime import datetime

class QualityChecker:
    """代码质量检查器"""

    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }

    def run_flake8_check(self) -> Dict[str, Any]:
        """运行flake8检查"""
        print("Running flake8 checks...")

        try:
            result = subprocess.run([
                'flake8', 'src/', '--format=json', '--statistics'
            ], capture_output=True, text=True)

            if result.stdout:
                issues = json.loads(result.stdout)
                return {
                    'status': 'failed',
                    'issues': issues,
                    'total_issues': len(issues)
                }
            else:
                return {
                    'status': 'passed',
                    'issues': [],
                    'total_issues': 0
                }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def run_mypy_check(self) -> Dict[str, Any]:
        """运行mypy类型检查"""
        print("Running mypy checks...")

        try:
            result = subprocess.run([
                'mypy', 'src/', '--show-error-codes', '--no-error-summary'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                return {
                    'status': 'passed',
                    'issues': []
                }
            else:
                # 解析mypy输出
                issues = []
                for line in result.stdout.split('\n'):
                    if line.strip():
                        issues.append(line.strip())

                return {
                    'status': 'failed',
                    'issues': issues,
                    'total_issues': len(issues)
                }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def run_bandit_check(self) -> Dict[str, Any]:
        """运行bandit安全检查"""
        print("Running bandit security checks...")

        try:
            result = subprocess.run([
                'bandit', '-r', 'src/', '-f', 'json'
            ], capture_output=True, text=True)

            if result.stdout:
                report = json.loads(result.stdout)
                return {
                    'status': 'passed' if report['metrics']['_totals']['severity.UNDEFINED'] == 0 else 'failed',
                    'issues': report.get('results', []),
                    'metrics': report.get('metrics', {})
                }
            else:
                return {
                    'status': 'passed',
                    'issues': [],
                    'metrics': {}
                }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def run_black_check(self) -> Dict[str, Any]:
        """运行black格式检查"""
        print("Running black formatting checks...")

        try:
            result = subprocess.run([
                'black', '--check', '--diff', 'src/'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                return {
                    'status': 'passed',
                    'issues': []
                }
            else:
                return {
                    'status': 'failed',
                    'issues': [result.stdout],
                    'needs_formatting': True
                }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def run_safety_check(self) -> Dict[str, Any]:
        """运行safety依赖检查"""
        print("Running safety dependency checks...")

        try:
            result = subprocess.run([
                'safety', 'check', '--json'
            ], capture_output=True, text=True)

            if result.stdout:
                report = json.loads(result.stdout)
                return {
                    'status': 'passed' if len(report) == 0 else 'failed',
                    'vulnerabilities': report
                }
            else:
                return {
                    'status': 'passed',
                    'vulnerabilities': []
                }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def run_complexity_check(self) -> Dict[str, Any]:
        """运行复杂度检查"""
        print("Running complexity checks...")

        try:
            result = subprocess.run([
                'radon', 'cc', 'src/', '-a', '-nb'
            ], capture_output=True, text=True)

            if result.stdout:
                # 解析radon输出
                lines = result.stdout.split('\n')
                complexity_data = []

                for line in lines:
                    if line.strip() and not line.startswith('_'):
                        complexity_data.append(line.strip())

                return {
                    'status': 'passed',
                    'complexity_data': complexity_data
                }
            else:
                return {
                    'status': 'passed',
                    'complexity_data': []
                }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def run_all_checks(self) -> Dict[str, Any]:
        """运行所有质量检查"""
        print("Running all quality checks...")

        # 运行各项检查
        self.results['checks']['flake8'] = self.run_flake8_check()
        self.results['checks']['mypy'] = self.run_mypy_check()
        self.results['checks']['bandit'] = self.run_bandit_check()
        self.results['checks']['black'] = self.run_black_check()
        self.results['checks']['safety'] = self.run_safety_check()
        self.results['checks']['complexity'] = self.run_complexity_check()

        # 计算总体状态
        all_passed = all(
            check.get('status') == 'passed'
            for check in self.results['checks'].values()
        )

        self.results['overall_status'] = 'passed' if all_passed else 'failed'

        return self.results

    def generate_report(self) -> str:
        """生成质量报告"""
        report = f"""
# Code Quality Report

Generated on: {self.results['timestamp']}

## Overall Status: {self.results['overall_status'].upper()}

## Detailed Results
"""

        for check_name, check_result in self.results['checks'].items():
            status = check_result.get('status', 'unknown')
            report += f"\n### {check_name.upper()}: {status.upper()}\n"

            if status == 'failed':
                if check_name == 'flake8':
                    report += f"- Total issues: {check_result.get('total_issues', 0)}\n"
                elif check_name == 'mypy':
                    report += f"- Type errors: {check_result.get('total_issues', 0)}\n"
                elif check_name == 'bandit':
                    report += f"- Security issues: {len(check_result.get('issues', []))}\n"
                elif check_name == 'black':
                    report += "- Code needs formatting\n"
                elif check_name == 'safety':
                    report += f"- Vulnerabilities found: {len(check_result.get('vulnerabilities', []))}\n"

        return report

    def save_results(self, output_dir: str = "quality_reports"):
        """保存检查结果"""
        os.makedirs(output_dir, exist_ok=True)

        # 保存详细结果
        with open(f"{output_dir}/quality_check_results.json", 'w') as f:
            json.dump(self.results, f, indent=2)

        # 生成并保存报告
        report = self.generate_report()
        with open(f"{output_dir}/quality_report.md", 'w') as f:
            f.write(report)

        print(f"Quality check results saved to {output_dir}/")

if __name__ == "__main__":
    checker = QualityChecker()
    results = checker.run_all_checks()
    checker.save_results()

    # 输出简要结果
    print(f"\nQuality Check Results: {results['overall_status'].upper()}")
    for check_name, check_result in results['checks'].items():
        print(f"  {check_name}: {check_result.get('status', 'unknown').upper()}")
```

### 安全检查

```yaml
# .github/workflows/security.yml
name: Security Scan

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 3 * * 1'  # 每周一凌晨3点

jobs:
  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install bandit safety

    - name: Run Bandit Security Scan
      run: |
        bandit -r src/ -f json -o bandit-report.json
      continue-on-error: true

    - name: Run Safety Dependency Check
      run: |
        safety check --json --output safety-report.json
      continue-on-error: true

    - name: Run Trivy Vulnerability Scan
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'

    - name: Upload Security Reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          bandit-report.json
          safety-report.json
          trivy-results.sarif

    - name: Comment on PR
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');

          // 读取安全报告
          let banditReport = {};
          let safetyReport = {};

          try {
            banditReport = JSON.parse(fs.readFileSync('bandit-report.json', 'utf8'));
          } catch (e) {
            console.log('No bandit report found');
          }

          try {
            safetyReport = JSON.parse(fs.readFileSync('safety-report.json', 'utf8'));
          } catch (e) {
            console.log('No safety report found');
          }

          // 生成评论
          let comment = '## Security Scan Results 🔒\n\n';

          if (banditReport.errors && banditReport.errors.length > 0) {
            comment += '⚠️ **Bandit found issues:**\n';
            banditReport.errors.forEach(error => {
              comment += `- ${error.test_name}: ${error.text}\n`;
            });
          } else {
            comment += '✅ **Bandit scan passed**\n';
          }

          if (safetyReport.length > 0) {
            comment += '⚠️ **Safety found vulnerabilities:**\n';
            safetyReport.forEach(vuln => {
              comment += `- ${vuln.id}: ${vuln.advisory}\n`;
            });
          } else {
            comment += '✅ **Safety scan passed**\n';
          }

          comment += '\n---\n';
          comment += 'Security scan completed successfully! 🎉';

          // 创建评论
          await github.rest.issues.createComment({
            owner: context.repo.owner,
            repo: context.repo.repo,
            issue_number: context.issue.number,
            body: comment
          });
```

---

## Docker配置

### CI镜像构建

```dockerfile
# Dockerfile.ci
FROM python:3.11-slim as ci-base

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt requirements-dev.txt ./

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-dev.txt

# 复制测试配置
COPY pytest.ini .coveragerc mypy.ini ./

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTEST_ADDOPTS="--maxfail=1 --tb=short"

# 默认命令
CMD ["pytest"]

# 测试阶段镜像
FROM ci-base as test

# 复制源代码
COPY src/ ./src/
COPY tests/ ./tests/

# 运行测试
CMD ["pytest", "tests/", "--cov=src", "--cov-report=xml"]

# 质量检查阶段镜像
FROM ci-base as quality

# 复制源代码
COPY src/ ./src/

# 运行质量检查
CMD ["sh", "-c", "flake8 src/ && mypy src/ && black --check src/"]

# 构建阶段镜像
FROM python:3.11-slim as build

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖文件
COPY requirements.txt ./

# 安装生产依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ ./src/

# 生产镜像
FROM python:3.11-slim

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从构建阶段复制依赖
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /app/src ./src

# 创建非root用户
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 测试环境配置

```yaml
# docker-compose.test.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.ci
      target: test
    depends_on:
      - postgres
      - redis
      - mlflow
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/football_test
      - REDIS_URL=redis://redis:6379/0
      - MLFLOW_TRACKING_URI=http://mlflow:5000
      - ENVIRONMENT=test
    volumes:
      - ./reports:/app/reports
    networks:
      - test-network

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=football_test
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-test-db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    networks:
      - test-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - test-network

  mlflow:
    image: ghcr.io/mlflow/mlflow:v1.30.0
    environment:
      - MLFLOW_BACKEND_STORE_URI=postgresql://postgres:postgres@postgres:5432/mlflow_test
      - MLFLOW_DEFAULT_ARTIFACT_ROOT=s3://mlflow/
    ports:
      - "5000:5000"
    depends_on:
      - postgres
    networks:
      - test-network

  test-runner:
    build:
      context: .
      dockerfile: Dockerfile.ci
      target: test
    depends_on:
      - postgres
      - redis
      - mlflow
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/football_test
      - REDIS_URL=redis://redis:6379/0
      - MLFLOW_TRACKING_URI=http://mlflow:5000
      - ENVIRONMENT=test
    command: pytest tests/ --cov=src --cov-report=xml --cov-report=html
    volumes:
      - ./reports:/app/reports
    networks:
      - test-network

volumes:
  postgres_data:

networks:
  test-network:
    driver: bridge
```

### 多环境部署

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    image: football-prediction/api:${TAG:-latest}
    depends_on:
      - postgres
      - redis
      - mlflow
      - kafka
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI}
      - KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS}
      - ENVIRONMENT=production
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - prod-network
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    networks:
      - prod-network
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1'
        reservations:
          memory: 1G
          cpus: '0.5'

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    networks:
      - prod-network
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.25'

  mlflow:
    image: ghcr.io/mlflow/mlflow:v1.30.0
    environment:
      - MLFLOW_BACKEND_STORE_URI=${MLFLOW_BACKEND_STORE_URI}
      - MLFLOW_DEFAULT_ARTIFACT_ROOT=${MLFLOW_ARTIFACT_ROOT}
    ports:
      - "5000:5000"
    networks:
      - prod-network

  kafka:
    image: confluentinc/cp-kafka:7.3.2
    depends_on:
      - zookeeper
    environment:
      - KAFKA_BROKER_ID=1
      - KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092
      - KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1
      - KAFKA_AUTO_CREATE_TOPICS_ENABLE=true
    volumes:
      - kafka_data:/var/lib/kafka/data
    networks:
      - prod-network

  zookeeper:
    image: confluentinc/cp-zookeeper:7.3.2
    environment:
      - ZOOKEEPER_CLIENT_PORT=2181
      - ZOOKEEPER_TICK_TIME=2000
    volumes:
      - zookeeper_data:/var/lib/zookeeper/data
    networks:
      - prod-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    networks:
      - prod-network

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - prod-network

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - prod-network

volumes:
  postgres_data:
  redis_data:
  kafka_data:
  zookeeper_data:
  prometheus_data:
  grafana_data:

networks:
  prod-network:
    driver: bridge
```

---

## 通知与报告

### Slack通知

```python
# scripts/slack_notifier.py
import requests
import json
import os
from typing import Dict, Any, List

class SlackNotifier:
    """Slack通知器"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_message(self, message: str, channel: str = "#general", username: str = "CI Bot") -> bool:
        """发送消息到Slack"""
        payload = {
            "channel": channel,
            "username": username,
            "text": message,
            "icon_emoji": ":robot_face:"
        }

        try:
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to send Slack message: {e}")
            return False

    def send_ci_status(self, status: str, details: Dict[str, Any]) -> bool:
        """发送CI状态通知"""
        status_emoji = {
            "success": ":white_check_mark:",
            "failed": ":x:",
            "running": ":running:",
            "cancelled": ":warning:"
        }.get(status, ":question:")

        message = f"""
{status_emoji} CI Pipeline {status.upper()}

*Repository:* {details.get('repository', 'Unknown')}
*Branch:* {details.get('branch', 'Unknown')}
*Commit:* {details.get('commit', 'Unknown')[:7]}
*Author:* {details.get('author', 'Unknown')}
*Duration:* {details.get('duration', 'Unknown')}

{self._format_test_results(details.get('tests', {}))}
{self._format_coverage_info(details.get('coverage', {}))}
{self._format_quality_metrics(details.get('quality', {}))}
        """

        return self.send_message(message, "#ci-cd")

    def send_coverage_alert(self, coverage_data: Dict[str, Any]) -> bool:
        """发送覆盖率警报"""
        current_coverage = coverage_data.get('current', 0)
        previous_coverage = coverage_data.get('previous', 0)
        threshold = coverage_data.get('threshold', 80)

        if current_coverage < threshold:
            message = f"""
:warning: Coverage Alert!

Current coverage ({current_coverage:.1f}%) is below threshold ({threshold}%)
Previous coverage: {previous_coverage:.1f}%
Change: {current_coverage - previous_coverage:+.1f}%

Commit: {coverage_data.get('commit', 'Unknown')[:7]}
Branch: {coverage_data.get('branch', 'Unknown')}
            """
            return self.send_message(message, "#alerts")

        return True

    def send_security_alert(self, security_data: Dict[str, Any]) -> bool:
        """发送安全警报"""
        vulnerabilities = security_data.get('vulnerabilities', [])
        severity = security_data.get('severity', 'unknown')

        message = f"""
:rotating_light: Security Alert!

*Severity:* {severity.upper()}
*Vulnerabilities Found:* {len(vulnerabilities)}
*Scan Type:* {security_data.get('scan_type', 'Unknown')}

*Repository:* {security_data.get('repository', 'Unknown')}
*Commit:* {security_data.get('commit', 'Unknown')[:7]}
        """

        if vulnerabilities:
            message += "\n*Top Issues:*\n"
            for vuln in vulnerabilities[:5]:  # 只显示前5个
                message += f"- {vuln.get('id', 'Unknown')}: {vuln.get('description', 'No description')}\n"

        return self.send_message(message, "#security")

    def send_performance_report(self, performance_data: Dict[str, Any]) -> bool:
        """发送性能报告"""
        message = f"""
:chart_with_upwards_trend: Performance Report

*Response Time:* {performance_data.get('response_time', 'Unknown')}ms
*Throughput:* {performance_data.get('throughput', 'Unknown')} req/s
*Error Rate:* {performance_data.get('error_rate', 'Unknown')}%
*Memory Usage:* {performance_data.get('memory_usage', 'Unknown')}%
*CPU Usage:* {performance_data.get('cpu_usage', 'Unknown')}%

*Environment:* {performance_data.get('environment', 'Unknown')}
*Timestamp:* {performance_data.get('timestamp', 'Unknown')}
        """

        return self.send_message(message, "#performance")

    def send_deployment_notification(self, deployment_data: Dict[str, Any]) -> bool:
        """发送部署通知"""
        status_emoji = {
            "success": ":rocket:",
            "failed": ":boom:",
            "started": ":gear:"
        }.get(deployment_data.get('status', ''), ":question:")

        message = f"""
{status_emoji} Deployment {deployment_data.get('status', '').upper()}

*Environment:* {deployment_data.get('environment', 'Unknown')}
*Service:* {deployment_data.get('service', 'Unknown')}
*Version:* {deployment_data.get('version', 'Unknown')}
*Commit:* {deployment_data.get('commit', 'Unknown')[:7]}
*Deployer:* {deployment_data.get('deployer', 'Unknown')}

{self._format_deployment_details(deployment_data.get('details', {}))}
        """

        return self.send_message(message, "#deployment")

    def _format_test_results(self, test_results: Dict[str, Any]) -> str:
        """格式化测试结果"""
        if not test_results:
            return ""

        passed = test_results.get('passed', 0)
        failed = test_results.get('failed', 0)
        skipped = test_results.get('skipped', 0)
        total = passed + failed + skipped

        return f"""
*Tests:* {passed}/{total} passed, {failed} failed, {skipped} skipped
*Coverage:* {test_results.get('coverage', 0):.1f}%
        """

    def _format_coverage_info(self, coverage_info: Dict[str, Any]) -> str:
        """格式化覆盖率信息"""
        if not coverage_info:
            return ""

        return f"""
*Coverage:* {coverage_info.get('total', 0):.1f}% (target: {coverage_info.get('target', 80)}%)
*Lines:* {coverage_info.get('lines', 0)}
*Branches:* {coverage_info.get('branches', 0)}
        """

    def _format_quality_metrics(self, quality_metrics: Dict[str, Any]) -> str:
        """格式化质量指标"""
        if not quality_metrics:
            return ""

        return f"""
*Code Quality:* {quality_metrics.get('score', 'Unknown')}
*Issues:* {quality_metrics.get('issues', 0)}
*Debt:* {quality_metrics.get('debt', 'Unknown')}
        """

    def _format_deployment_details(self, details: Dict[str, Any]) -> str:
        """格式化部署详情"""
        if not details:
            return ""

        return f"""
*Duration:* {details.get('duration', 'Unknown')}
*Rollback:* {'Yes' if details.get('rollback', False) else 'No'}
*Health Check:* {'Pass' if details.get('health_check', False) else 'Fail'}
        """
```

### 邮件报告

```python
# scripts/email_reporter.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from typing import List, Dict, Any
from datetime import datetime
import jinja2

class EmailReporter:
    """邮件报告生成器"""

    def __init__(self, smtp_config: Dict[str, Any]):
        self.smtp_server = smtp_config['host']
        self.smtp_port = smtp_config['port']
        self.smtp_username = smtp_config['username']
        self.smtp_password = smtp_config['password']
        self.from_email = smtp_config['from_email']

    def send_daily_report(self, report_data: Dict[str, Any], recipients: List[str]) -> bool:
        """发送日报"""
        subject = f"Daily CI/CD Report - {datetime.now().strftime('%Y-%m-%d')}"

        html_content = self._render_template('daily_report.html', report_data)
        text_content = self._render_template('daily_report.txt', report_data)

        return self._send_email(subject, text_content, html_content, recipients)

    def send_weekly_summary(self, report_data: Dict[str, Any], recipients: List[str]) -> bool:
        """发送周报"""
        subject = f"Weekly CI/CD Summary - {datetime.now().strftime('%Y-%m-%d')}"

        html_content = self._render_template('weekly_summary.html', report_data)
        text_content = self._render_template('weekly_summary.txt', report_data)

        return self._send_email(subject, text_content, html_content, recipients)

    def send_coverage_alert(self, alert_data: Dict[str, Any], recipients: List[str]) -> bool:
        """发送覆盖率警报"""
        subject = f"⚠️ Coverage Alert - {alert_data.get('repository', 'Unknown')}"

        html_content = self._render_template('coverage_alert.html', alert_data)
        text_content = self._render_template('coverage_alert.txt', alert_data)

        return self._send_email(subject, text_content, html_content, recipients)

    def send_security_alert(self, alert_data: Dict[str, Any], recipients: List[str]) -> bool:
        """发送安全警报"""
        subject = f"🔒 Security Alert - {alert_data.get('repository', 'Unknown')}"

        html_content = self._render_template('security_alert.html', alert_data)
        text_content = self._render_template('security_alert.txt', alert_data)

        return self._send_email(subject, text_content, html_content, recipients)

    def send_deployment_report(self, deployment_data: Dict[str, Any], recipients: List[str]) -> bool:
        """发送部署报告"""
        status = deployment_data.get('status', 'unknown')
        subject = f"Deployment Report - {status.upper()} - {deployment_data.get('environment', 'Unknown')}"

        html_content = self._render_template('deployment_report.html', deployment_data)
        text_content = self._render_template('deployment_report.txt', deployment_data)

        return self._send_email(subject, text_content, html_content, recipients)

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """渲染模板"""
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')

        if not os.path.exists(template_dir):
            os.makedirs(template_dir)

        template_path = os.path.join(template_dir, template_name)

        # 如果模板不存在，创建默认模板
        if not os.path.exists(template_path):
            self._create_default_template(template_name, template_path)

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()

            template = jinja2.Template(template_content)
            return template.render(**context)
        except Exception as e:
            print(f"Failed to render template {template_name}: {e}")
            return f"Report data: {json.dumps(context, indent=2)}"

    def _create_default_template(self, template_name: str, template_path: str):
        """创建默认模板"""
        if template_name == 'daily_report.html':
            template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Daily CI/CD Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background-color: #e9ecef; border-radius: 3px; }
        .success { color: #28a745; }
        .failed { color: #dc3545; }
        .warning { color: #ffc107; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Daily CI/CD Report</h1>
        <p>Date: {{ date }}</p>
        <p>Repository: {{ repository }}</p>
    </div>

    <div class="section">
        <h2>Test Results</h2>
        <div class="metric">Total Tests: {{ tests.total }}</div>
        <div class="metric success">Passed: {{ tests.passed }}</div>
        <div class="metric failed">Failed: {{ tests.failed }}</div>
        <div class="metric">Skipped: {{ tests.skipped }}</div>
        <div class="metric">Coverage: {{ tests.coverage }}%</div>
    </div>

    <div class="section">
        <h2>Build Information</h2>
        <p>Commits: {{ builds.commits }}</p>
        <p>Successful Builds: {{ builds.successful }}</p>
        <p>Failed Builds: {{ builds.failed }}</p>
        <p>Average Build Time: {{ builds.avg_time }}</p>
    </div>

    <div class="section">
        <h2>Code Quality</h2>
        <p>Issues Found: {{ quality.issues }}</p>
        <p>Coverage Trend: {{ quality.coverage_trend }}</p>
        <p>Code Debt: {{ quality.debt }}</p>
    </div>
</body>
</html>
            """
        elif template_name == 'coverage_alert.html':
            template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Coverage Alert</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .alert { background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 20px; border-radius: 5px; }
        .metric { margin: 10px 0; }
    </style>
</head>
<body>
    <div class="alert">
        <h1>⚠️ Coverage Alert</h1>
        <div class="metric">
            <strong>Current Coverage:</strong> {{ current_coverage }}%
        </div>
        <div class="metric">
            <strong>Threshold:</strong> {{ threshold }}%
        </div>
        <div class="metric">
            <strong>Previous Coverage:</strong> {{ previous_coverage }}%
        </div>
        <div class="metric">
            <strong>Change:</strong> {{ change }}%
        </div>
        <div class="metric">
            <strong>Repository:</strong> {{ repository }}
        </div>
        <div class="metric">
            <strong>Branch:</strong> {{ branch }}
        </div>
        <div class="metric">
            <strong>Commit:</strong> {{ commit }}
        </div>
    </div>
</body>
</html>
            """
        else:
            template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Report</title>
</head>
<body>
    <h1>Report</h1>
    <pre>{{ context | tojson(indent=2) }}</pre>
</body>
</html>
            """

        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)

    def _send_email(self, subject: str, text_content: str, html_content: str, recipients: List[str]) -> bool:
        """发送邮件"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(recipients)

            # 添加文本内容
            text_part = MIMEText(text_content, 'plain')
            msg.attach(text_part)

            # 添加HTML内容
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # 发送邮件
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
```

---

## 总结

本文档详细介绍了足球预测系统的CI/CD配置，包括：

1. **GitHub Actions工作流**: 完整的CI/CD流水线配置
2. **覆盖率监控**: Codecov集成和趋势分析
3. **自动化检查**: 代码质量、安全、性能检查
4. **Docker配置**: 测试环境和生产环境配置
5. **通知系统**: Slack通知和邮件报告

这些配置确保了代码质量、测试覆盖率和部署流程的自动化管理，为项目的持续交付提供了坚实基础。