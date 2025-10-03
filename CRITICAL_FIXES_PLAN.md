# 🔧 严重问题修复方案

**制定时间**: 2025-10-04 01:05
**方案类型**: 全面系统修复
**优先级**: 🔴 极高

---

## 📋 修复路线图

### Phase 1: 紧急安全修复（1-2天）
### Phase 2: 代码质量提升（1周）
### Phase 3: 建立防护机制（2周）
### Phase 4: 持续改进（持续）

---

## 🚨 Phase 1: 紧急安全修复（24小时内）

### 1.1 密码安全修复（最高优先级）

#### 创建密码扫描和替换工具
```python
# scripts/security/password_fixer.py
"""
自动修复硬编码密码
"""

import re
import os
from pathlib import Path
from dotenv import load_dotenv

class PasswordFixer:
    def __init__(self):
        self.password_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', 'password'),
            (r'api_key\s*=\s*["\'][^"\']+["\']', 'api_key'),
            (r'secret\s*=\s*["\'][^"\']+["\']', 'secret'),
            (r'token\s*=\s*["\'][^"\']+["\']', 'token'),
            (r'aws_secret_access_key\s*=\s*["\'][^"\']+["\']', 'aws_secret_access_key'),
        ]
        self.fixed_files = []
        self.errors = []

    def scan_and_fix(self, project_root: Path):
        """扫描并修复所有硬编码密码"""
        for py_file in project_root.rglob("*.py"):
            if 'venv' in str(py_file) or '.git' in str(py_file):
                continue

            self.fix_file(py_file)

    def fix_file(self, file_path: Path):
        """修复单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                original_content = content

            modified = False

            # 替换硬编码密码
            for pattern, key_type in self.password_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    old_line = match.group()

                    # 提取变量名
                    var_match = re.search(r'(\w+)\s*=', old_line)
                    if var_match:
                        var_name = var_match.group(1)

                        # 生成环境变量名
                        env_var_name = f"{var_name.upper()}_ENV"

                        # 替换为环境变量
                        new_line = f'{var_name} = os.getenv("{env_var_name}")'

                        # 添加os导入（如果需要）
                        if 'import os' not in content and 'from os import' not in content:
                            content = 'import os\n' + content
                            modified = True

                        # 替换内容
                        content = content.replace(old_line, new_line)
                        modified = True

                        self.fixed_files.append({
                            'file': str(file_path),
                            'old': old_line.strip(),
                            'new': new_line,
                            'env_var': env_var_name
                        })

            # 保存修改
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

        except Exception as e:
            self.errors.append(f"处理文件失败 {file_path}: {e}")

    def generate_env_template(self):
        """生成环境变量模板"""
        env_content = "# 安全配置 - 请填写实际值\n"
        env_content += "# ⚠️ 不要提交到版本控制！\n\n"

        for fix in self.fixed_files:
            if 'env_var' in fix:
                env_content += f"{fix['env_var']}=\n"

        return env_content
```

#### 立即执行修复
```bash
# 1. 备份当前代码
git checkout -b security-fixes-$(date +%Y%m%d)

# 2. 运行密码修复工具
python scripts/security/password_fixer.py

# 3. 创建安全的环境变量模板
python scripts/security/password_fixer.py --generate-env

# 4. 手动配置敏感信息
cp .env.template .env.local
# 编辑 .env.local 填写真实密码
```

### 1.2 敏感文件保护

#### 创建敏感文件保护脚本
```python
# scripts/security/protect_sensitive_files.py
"""
保护敏感文件不被提交
"""

class SensitiveFileProtector:
    def __init__(self):
        self.sensitive_patterns = [
            "*.env",
            "*.env.*",
            "*.pem",
            "*.key",
            "*.p12",
            "*.pfx",
            "secrets/",
            "config/secrets.yaml",
            "*.keytab",
            ".aws/",
            "id_rsa*",
        ]

    def update_gitignore(self):
        """更新.gitignore文件"""
        gitignore_path = Path(".gitignore")

        with open(gitignore_path, 'a') as f:
            f.write("\n# 敏感文件 - 自动添加\n")
            for pattern in self.sensitive_patterns:
                f.write(f"{pattern}\n")

        print("✅ .gitignore已更新")

    def check_sensitive_files(self):
        """检查是否有敏感文件被跟踪"""
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True
        )

        tracked_files = result.stdout.split('\n')
        sensitive_tracked = []

        for file in tracked_files:
            for pattern in self.sensitive_patterns:
                if self.match_pattern(file, pattern):
                    sensitive_tracked.append(file)

        if sensitive_tracked:
            print("⚠️ 发现被跟踪的敏感文件：")
            for file in sensitive_tracked:
                print(f"  - {file}")
                print(f"    执行: git rm --cached {file}")

        return sensitive_tracked

    def fix_permissions(self):
        """修复敏感文件权限"""
        sensitive_files = [
            ".env",
            ".env.local",
            ".env.production",
        ]

        for file in sensitive_files:
            if Path(file).exists():
                os.chmod(file, 0o600)
                print(f"✅ {file} 权限已设置为 600")
```

### 1.3 依赖漏洞修复

```bash
# 升级所有有漏洞的依赖
pip install --upgrade requests
pip install --upgrade urllib3
pip install --upgrade pyyaml
pip install --upgrade jinja2

# 更新requirements文件
pip freeze > requirements.txt

# 锁定依赖版本
pip freeze > requirements.lock

# 扫描漏洞
pip-audit  # 需要安装 pip-audit
```

---

## 📊 Phase 2: 代码质量提升（1周）

### 2.1 大文件自动拆分工具

```python
# scripts/refactoring/file_splitter.py
"""
自动拆分大文件
"""

class FileSplitter:
    def __init__(self):
        self.max_lines = 500
        self.split_rules = {
            'src/database/connection.py': {
                'connection_manager': [
                    'class DatabaseConnection',
                    'def connect',
                    'def disconnect'
                ],
                'connection_pool': [
                    'class ConnectionPool',
                    'def get_connection',
                    'def release_connection'
                ],
                'transaction_manager': [
                    'class TransactionManager',
                    'def begin_transaction',
                    'def commit',
                    'def rollback'
                ]
            }
        }

    def split_large_files(self):
        """拆分所有大文件"""
        for file_path in Path('src').rglob('*.py'):
            if file_path.stat().st_size > 20000:  # 约500行
                self.split_file(file_path)

    def split_file(self, file_path: Path):
        """拆分单个文件"""
        print(f"拆分文件: {file_path}")

        # 读取文件内容
        with open(file_path, 'r') as f:
            lines = f.readlines()

        # 分析类和函数
        classes, functions = self.analyze_code_structure(lines)

        # 根据规则拆分
        if str(file_path) in self.split_rules:
            self.apply_split_rules(file_path, lines, classes)
        else:
            self.auto_split(file_path, lines, classes, functions)

    def auto_split(self, file_path, lines, classes, functions):
        """自动拆分策略"""
        # 创建模块目录
        module_dir = file_path.parent / file_path.stem
        module_dir.mkdir(exist_ok=True)

        # 拆分类
        for class_name, class_info in classes.items():
            if class_info['line_count'] > 100:
                self.extract_class_to_file(file_path, class_name, class_info, module_dir)

        # 拆分函数
        for func_name, func_info in functions.items():
            if func_info['line_count'] > 50:
                self.extract_function_to_file(file_path, func_name, func_info, module_dir)
```

### 2.2 代码清理工具

```python
# scripts/refactoring/code_cleaner.py
"""
代码清理工具
"""

class CodeCleaner:
    def clean_legacy_tests(self):
        """清理legacy测试文件"""
        legacy_dir = Path('tests/legacy')
        if legacy_dir.exists():
            # 统计需要清理的文件
            total_files = sum(1 for _ in legacy_dir.rglob('*.py'))
            print(f"发现 {total_files} 个legacy测试文件")

            # 备份后删除
            backup_dir = Path('tests/legacy_backup')
            if legacy_dir.exists():
                shutil.move(str(legacy_dir), str(backup_dir))
                print("✅ Legacy测试已备份到 tests/legacy_backup")

    def remove_duplicate_files(self):
        """删除重复文件"""
        file_hashes = {}
        duplicates = []

        for py_file in Path('.').rglob('*.py'):
            if 'venv' in str(py_file) or '.git' in str(py_file):
                continue

            # 计算文件哈希
            file_hash = self.calculate_hash(py_file)

            if file_hash in file_hashes:
                duplicates.append((py_file, file_hashes[file_hash]))
            else:
                file_hashes[file_hash] = py_file

        # 删除重复文件
        for duplicate, original in duplicates:
            print(f"删除重复文件: {duplicate} (与 {original} 相同)")
            duplicate.unlink()

        return duplicates

    def fix_todos(self):
        """修复TODO注释"""
        todo_patterns = [
            (r'# TODO: 实现测试', '# TODO: 需要实现测试'),
            (r'# TODO: 添加边界条件', '# TODO: 需要添加边界条件测试'),
            (r'# TODO: 实现具体逻辑', '# TODO: 实现具体业务逻辑'),
        ]

        for py_file in Path('src').rglob('*.py'):
            self.apply_fixes(py_file, todo_patterns)
```

### 2.3 自动化重构执行

```bash
#!/bin/bash
# scripts/refactoring/run_refactoring.sh

echo "🚀 开始代码重构..."

# 1. 备份当前状态
git checkout -b refactor-$(date +%Y%m%d)
git add .
git commit -m " refactor: 保存重构前状态"

# 2. 拆分大文件
python scripts/refactoring/file_splitter.py

# 3. 清理代码
python scripts/refactoring/code_cleaner.py

# 4. 修复导入
python scripts/refactoring/fix_imports.py

# 5. 运行测试
pytest tests/unit/ -v

# 6. 提交更改
git add .
git commit -m " refactor: 完成代码重构"

echo "✅ 重构完成！"
```

---

## 🛡️ Phase 3: 建立防护机制（2周）

### 3.1 安全扫描集成

```yaml
# .github/workflows/security-scan.yml
name: Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨2点

jobs:
  security-scan:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install pip-audit bandit safety semgrep

    - name: Run pip-audit
      run: pip-audit --requirements=requirements.txt

    - name: Run Bandit
      run: bandit -r src/ -f json -o bandit-report.json

    - name: Run Safety
      run: safety check --json --output safety-report.json

    - name: Run Semgrep
      run: semgrep --config=auto --json --output=semgrep-report.json src/

    - name: Upload reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          bandit-report.json
          safety-report.json
          semgrep-report.json
```

### 3.2 代码质量门禁

```yaml
# .github/workflows/quality-gate.yml
name: Quality Gate

on:
  pull_request:
    branches: [main]

jobs:
  quality-check:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3
      with:
        fetch-depth: 0

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Check file sizes
      run: |
        python scripts/quality/check_file_sizes.py --max-lines 500

    - name: Check for hardcoded secrets
      run: |
        python scripts/quality/check_secrets.py

    - name: Run tests
      run: |
        pytest tests/unit/ --cov=src --cov-fail-under=80

    - name: Check complexity
      run: |
        radon cc src/ --min B

    - name: Quality gate
      run: |
        python scripts/quality/quality_gate.py
```

### 3.3 开发环境配置

```python
# scripts/development/setup_dev_env.py
"""
开发环境自动配置
"""

class DevEnvironmentSetup:
    def setup_pre_commit_hooks(self):
        """安装pre-commit钩子"""
        hooks = {
            'repos': [
                {
                    'repo': 'https://github.com/pre-commit/pre-commit-hooks',
                    'rev': 'v4.4.0',
                    'hooks': [
                        {'id': 'trailing-whitespace'},
                        {'id': 'end-of-file-fixer'},
                        {'id': 'check-yaml'},
                        {'id': 'check-added-large-files'},
                    ]
                },
                {
                    'repo': 'https://github.com/psf/black',
                    'rev': '23.3.0',
                    'hooks': [
                        {'id': 'black'},
                    ]
                },
                {
                    'repo': 'https://github.com/pycqa/isort',
                    'rev': '5.12.0',
                    'hooks': [
                        {'id': 'isort'},
                    ]
                },
                {
                    'repo': 'https://github.com/pycqa/flake8',
                    'rev': '6.0.0',
                    'hooks': [
                        {'id': 'flake8'},
                    ]
                },
                {
                    'repo': 'https://github.com/PyCQA/bandit',
                    'rev': '1.7.5',
                    'hooks': [
                        {'id': 'bandit', 'args': ['-c', 'pyproject.toml']},
                    ]
                },
            ]
        }

        with open('.pre-commit-config.yaml', 'w') as f:
            yaml.dump(hooks, f)

        # 安装钩子
        subprocess.run(['pre-commit', 'install'])
        print("✅ Pre-commit hooks已安装")

    def create_env_template(self):
        """创建环境变量模板"""
        env_template = """# 开发环境配置
# 复制此文件为 .env.local 并填写实际值

# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_prediction_dev
DB_USER=postgres
DB_PASSWORD=

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# API密钥
FOOTBALL_API_KEY=
ODDS_API_KEY=

# 安全配置
SECRET_KEY=
JWT_SECRET=

# MLflow配置
MLFLOW_TRACKING_URI=http://localhost:5000
"""

        with open('.env.template', 'w') as f:
            f.write(env_template)

        print("✅ .env.template已创建")
```

---

## 🔄 Phase 4: 持续改进（持续）

### 4.1 定期维护脚本

```python
# scripts/maintenance/monthly_cleanup.py
"""
月度维护任务
"""

class MonthlyMaintenance:
    def run_maintenance(self):
        """执行月度维护"""
        tasks = [
            self.clean_temp_files,
            self.update_dependencies,
            self.run_security_scan,
            self.check_code_quality,
            self.generate_reports,
        ]

        for task in tasks:
            try:
                task()
            except Exception as e:
                print(f"任务失败: {e}")

    def update_dependencies(self):
        """更新依赖包"""
        subprocess.run(['pip', 'install', '--upgrade', '-r', 'requirements.txt'])
        subprocess.run(['pip', 'freeze', '>', 'requirements.lock'])

    def run_security_scan(self):
        """运行安全扫描"""
        subprocess.run(['pip-audit'], check=True)
        subprocess.run(['bandit', '-r', 'src/'], check=True)
```

### 4.2 监控和告警

```python
# scripts/monitoring/health_monitor.py
"""
项目健康监控
"""

class ProjectHealthMonitor:
    def check_project_health(self):
        """检查项目健康状态"""
        health_score = {
            'security': self.check_security_health(),
            'quality': self.check_code_quality(),
            'tests': self.check_test_coverage(),
            'docs': self.check_documentation(),
        }

        overall_score = sum(health_score.values()) / len(health_score)

        if overall_score < 80:
            self.send_alert(f"项目健康分数低: {overall_score}")

        return health_score

    def send_alert(self, message):
        """发送告警"""
        # 可以集成邮件、Slack等
        print(f"🚨 ALERT: {message}")
```

---

## 📋 执行计划

### Day 1: 紧急修复
```bash
# 1. 创建修复分支
git checkout -b security-fixes-$(date +%Y%m%d)

# 2. 运行密码修复工具
python scripts/security/password_fixer.py

# 3. 保护敏感文件
python scripts/security/protect_sensitive_files.py

# 4. 更新依赖
pip install --upgrade requests
pip freeze > requirements.txt

# 5. 提交修复
git add .
git commit -m "security: 修复所有硬编码密码和敏感文件"
```

### Day 2-3: 代码质量
```bash
# 1. 拆分大文件
python scripts/refactoring/file_splitter.py

# 2. 清理代码
python scripts/refactoring/code_cleaner.py

# 3. 运行测试
pytest tests/unit/ -v

# 4. 提交更改
git add .
git commit -m "refactor: 代码质量改进"
```

### Week 2: 建立机制
```bash
# 1. 安装开发工具
python scripts/development/setup_dev_env.py

# 2. 配置CI/CD
# GitHub Actions会自动运行

# 3. 设置定期任务
crontab -e
# 添加: 0 0 1 * * cd /path/to/project && python scripts/maintenance/monthly_cleanup.py
```

---

## ✅ 成功标准

### 安全指标
- [ ] 0个硬编码密码
- [ ] 0个敏感文件暴露
- [ ] 0个已知漏洞
- [ ] 通过所有安全扫描

### 质量指标
- [ ] 所有文件<500行
- [ ] 0个重复文件
- [ ] 代码覆盖率>80%
- [ ] 0个严重代码异味

### 维护指标
- [ ] 自动化测试100%通过
- [ ] CI/CD自动运行
- [ ] 定期维护任务执行
- [ ] 健康分数>90

---

## 🚀 开始执行

```bash
# 立即开始
git checkout -b critical-fixes-$(date +%Y%m%d)
python scripts/fix_all_critical_issues.py
```

**记住：安全无小事，立即行动！** 🚨