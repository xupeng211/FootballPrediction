#!/bin/bash

# 安全扫描脚本
# Football Prediction Project

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 配置
SCAN_DIR=${SCAN_DIR:-.}
REPORT_DIR="security-reports/$(date +%Y%m%d_%H%M%S)"
GITHUB_TOKEN=${GITHUB_TOKEN:-}
CODEQL_DATABASE=${CODEQL_DATABASE:-}
SEVERITY_THRESHOLD=${SEVERITY_THRESHOLD:-medium}

# 创建报告目录
create_report_dir() {
    log_step "创建安全扫描报告目录..."
    mkdir -p "$REPORT_DIR"
    mkdir -p "$REPORT_DIR"/{trivy,snyk,codeql,semgrep,safety,bandit}
    log_info "报告目录: $REPORT_DIR"
}

# 依赖漏洞扫描
scan_dependencies() {
    log_step "扫描依赖漏洞..."

    # 使用Safety扫描Python依赖
    if command -v safety &> /dev/null; then
        log_info "运行Safety扫描..."
        safety check --json --output "$REPORT_DIR/safety/report.json" requirements/
        safety check --output "$REPORT_DIR/safety/report.txt" requirements/
    else
        log_warn "Safety未安装，跳过Python依赖扫描"
    fi

    # 使用Trivy扫描镜像依赖
    if command -v trivy &> /dev/null; then
        log_info "运行Trivy镜像扫描..."
        docker build -t football-prediction:scan . > /dev/null 2>&1
        trivy image --format json --output "$REPORT_DIR/trivy/image.json" football-prediction:scan
        trivy image --output "$REPORT_DIR/trivy/image.txt" football-prediction:scan
    else
        log_warn "Trivy未安装，跳过镜像依赖扫描"
    fi

    # 使用Snyk扫描（如果配置了token）
    if command -v snyk &> /dev/null && [[ -n "$GITHUB_TOKEN" ]]; then
        log_info "运行Snyk扫描..."
        export SNYK_TOKEN="$GITHUB_TOKEN"
        snyk test --json --output-file="$REPORT_DIR/snyk/report.json" . > /dev/null 2>&1 || true
        snyk test --output="$REPORT_DIR/snyk/report.txt" . > /dev/null 2>&1 || true
    fi
}

# 静态代码分析
run_static_analysis() {
    log_step "运行静态代码分析..."

    # 使用Semgrep
    if command -v semgrep &> /dev/null; then
        log_info "运行Semgrep扫描..."
        semgrep --config=auto --json --output="$REPORT_DIR/semgrep/report.json" "$SCAN_DIR/src"
        semgrep --config=auto --output="$REPORT_DIR/semgrep/report.txt" "$SCAN_DIR/src"
    else
        log_warn "Semgrep未安装，运行pip安装..."
        pip install semgrep
        semgrep --config=auto --json --output="$REPORT_DIR/semgrep/report.json" "$SCAN_DIR/src"
        semgrep --config=auto --output="$REPORT_DIR/semgrep/report.txt" "$SCAN_DIR/src"
    fi

    # 使用Bandit扫描Python代码
    if command -v bandit &> /dev/null; then
        log_info "运行Bandit扫描..."
        bandit -r "$SCAN_DIR/src" -f json -o "$REPORT_DIR/bandit/report.json"
        bandit -r "$SCAN_DIR/src" -o "$REPORT_DIR/bandit/report.txt"
    else
        log_warn "Bandit未安装，运行pip安装..."
        pip install bandit
        bandit -r "$SCAN_DIR/src" -f json -o "$REPORT_DIR/bandit/report.json"
        bandit -r "$SCAN_DIR/src" -o "$REPORT_DIR/bandit/report.txt"
    fi

    # 使用CodeQL（如果配置了）
    if command -v codeql &> /dev/null && [[ -n "$CODEQL_DATABASE" ]]; then
        log_info "运行CodeQL扫描..."
        codeql database create --language=python "$CODEQL_DATABASE"
        codeql database analyze "$CODEQL_DATABASE" "$SCAN_DIR/src" --format=json --output="$REPORT_DIR/codeql/results.sarif"
    fi
}

# 容器安全扫描
scan_containers() {
    log_step "扫描容器安全..."

    if command -v trivy &> /dev/null; then
        # 扫描镜像配置
        log_info "扫描Dockerfile..."
        trivy config --format json --output "$REPORT_DIR/trivy/dockerfile.json" Dockerfile*
        trivy config --output "$REPORT_DIR/trivy/dockerfile.txt" Dockerfile*

        # 扫描Kubernetes配置
        if [[ -d "k8s" ]]; then
            log_info "扫描Kubernetes配置..."
            trivy config --format json --output "$REPORT_DIR/trivy/k8s.json" k8s/
            trivy config --output "$REPORT_DIR/trivy/k8s.txt" k8s/
        fi

        # 扫描运行中的容器
        log_info "扫描运行中的容器..."
        docker ps --format "table {{.Names}}" | grep -v NAMES | while read container; do
            if [[ -n "$container" ]]; then
                trivy container --format json --output "$REPORT_DIR/trivy/container_$(echo $container | tr -d ' ').json" "$container"
                trivy container --output "$REPORT_DIR/trivy/container_$(echo $container | tr -d ' ').txt" "$container"
            fi
        done
    fi
}

# 基础设施扫描
scan_infrastructure() {
    log_step "扫描基础设施安全..."

    # Terraform扫描（如果存在）
    if [[ -f "terraform.tf" ]] || [[ -f "main.tf" ]]; then
        if command -v tfsec &> /dev/null; then
            log_info "运行Terraform安全扫描..."
            tfsec --format=json --out="$REPORT_DIR/tfsec/report.json" .
            tfsec --out="$REPORT_DIR/tfsec/report.txt" .
        else
            log_warn "tfsec未安装，跳过Terraform扫描"
        fi
    fi

    # Docker Compose扫描
    if [[ -f "docker-compose.yml" ]] || [[ -f "docker-compose.prod.yml" ]]; then
        if command -v docker-compose &> /dev/null; then
            log_info "检查Docker Compose配置..."
            # 检查是否使用了root用户
            grep -r "user: 0" docker-compose*.yml > "$REPORT_DIR/docker/root_user_check.txt" || true

            # 检查暴露的端口
            grep -r "ports:" docker-compose*.yml | grep -v "127.0.0.1" > "$REPORT_DIR/docker/exposed_ports.txt" || true

            # 检查环境变量
            grep -r "environment:" docker-compose*.yml -A 5 > "$REPORT_DIR/docker/environment_vars.txt" || true
        fi
    fi
}

# 密钥泄露扫描
scan_secrets() {
    log_step "扫描密钥泄露..."

    # 使用Gitleaks
    if command -v gitleaks &> /dev/null; then
        log_info "运行Gitleaks扫描..."
        gitleaks detect --source="$SCAN_DIR" --report-path="$REPORT_DIR/gitleaks" --report-format="json"
    else
        log_warn "Gitleaks未安装，运行下载..."
        wget https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks-linux-amd64 -O gitleaks
        chmod +x gitleaks
        sudo mv gitleaks /usr/local/bin/
        gitleaks detect --source="$SCAN_DIR" --report-path="$REPORT_DIR/gitleaks" --report-format="json"
    fi

    # 手动扫描常见密钥模式
    log_info "扫描常见密钥模式..."
    grep -r -i "password\|secret\|key\|token\|api[_-]?key" "$SCAN_DIR" \
        --include="*.py" --include="*.yml" --include="*.yaml" --include="*.json" --include="*.env*" \
        -n | grep -v "__pycache__" > "$REPORT_DIR/secrets/potential_secrets.txt" || true

    # 扫描环境变量文件
    if [[ -f ".env" ]]; then
        log_warn "发现.env文件，检查敏感信息..."
        grep -E "(password|secret|key|token)" .env > "$REPORT_DIR/secrets/env_secrets.txt" || true
    fi
}

# 网络安全扫描
scan_network() {
    log_step "扫描网络安全配置..."

    # 检查开放端口
    log_info "检查开放端口..."
    netstat -tuln | grep LISTEN > "$REPORT_DIR/network/open_ports.txt"

    # 检查防火墙状态
    if command -v ufw &> /dev/null; then
        ufw status verbose > "$REPORT_DIR/network/ufw_status.txt"
    elif command -v iptables &> /dev/null; then
        iptables -L -n > "$REPORT_DIR/network/iptables_rules.txt"
    fi

    # 检查SSL证书
    if command -v openssl &> /dev/null; then
        log_info "检查SSL证书..."
        echo "localhost:8000" | \
            timeout 5 openssl s_client -connect localhost:8000 2>/dev/null | \
            openssl x509 -noout -dates > "$REPORT_DIR/network/ssl_info.txt" || \
            echo "无法获取SSL证书信息" > "$REPORT_DIR/network/ssl_info.txt"
    fi
}

# 权限检查
check_permissions() {
    log_step "检查文件权限..."

    # 检查关键文件权限
    log_info "检查文件权限..."
    find "$SCAN_DIR" -type f -name "*.pem" -o -name "*.key" -o -name "id_rsa" | \
        while read file; do
            ls -la "$file" >> "$REPORT_DIR/permissions/key_permissions.txt"
        done

    # 检查可执行文件
    find "$SCAN_DIR" -type f -executable -ls > "$REPORT_DIR/permissions/executables.txt"

    # 检查配置文件权限
    find "$SCAN_DIR" -type f -name "*.conf" -o -name "*.yml" -o -name "*.yaml" | \
        while read file; do
            ls -la "$file" >> "$REPORT_DIR/permissions/config_permissions.txt"
        done

    # 检查目录权限
    ls -ld "$SCAN_DIR"/{config,scripts,secrets} > "$REPORT_DIR/permissions/dir_permissions.txt" 2>/dev/null || true
}

# 生成安全报告
generate_report() {
    log_step "生成安全报告摘要..."

    cat > "$REPORT_DIR/security_summary.md" <<EOF
# 安全扫描报告

## 扫描时间
$(date)

## 扫描范围
- 源代码目录: $SCAN_DIR
- 扫描工具: Safety, Trivy, Semgrep, Bandit, Gitleaks

## 发现的问题

### 1. 依赖漏洞
EOF

    # 统计各工具发现的问题
    if [[ -f "$REPORT_DIR/safety/report.txt" ]]; then
        safety_issues=$(grep -c "Vulnerability" "$REPORT_DIR/safety/report.txt" || echo 0)
        echo "- Safety (Python依赖): $safety_issues 个漏洞" >> "$REPORT_DIR/security_summary.md"
    fi

    if [[ -f "$REPORT_DIR/trivy/image.txt" ]]; then
        trivy_issues=$(grep -c "HIGH\|CRITICAL" "$REPORT_DIR/trivy/image.txt" || echo 0)
        echo "- Trivy (容器镜像): $trivy_issues 个高危漏洞" >> "$REPORT_DIR/security_summary.md"
    fi

    echo "" >> "$REPORT_DIR/security_summary.md"
    echo "### 2. 代码安全问题" >> "$REPORT_DIR/security_summary.md"

    if [[ -f "$REPORT_DIR/bandit/report.txt" ]]; then
        bandit_issues=$(grep -c "Issue:" "$REPORT_DIR/bandit/report.txt" || echo 0)
        echo "- Bandit: $bandit_issues 个问题" >> "$REPORT_DIR/security_summary.md"
    fi

    if [[ -f "$REPORT_DIR/semgrep/report.txt" ]]; then
        semgrep_issues=$(grep -c "error\|warning" "$REPORT_DIR/semgrep/report.txt" || echo 0)
        echo "- Semgrep: $semgrep_issues 个问题" >> "$REPORT_DIR/security_summary.md"
    fi

    echo "" >> "$REPORT_DIR/security_summary.md"
    echo "### 3. 密钥泄露风险" >> "$REPORT_DIR/security_summary.md"

    if [[ -f "$REPORT_DIR/gitleaks/report.json" ]]; then
        gitleaks_issues=$(grep -o '"type":"[^"]*"' "$REPORT_DIR/gitleaks/report.json" | wc -l || echo 0)
        echo "- Gitleaks: $gitleaks 个潜在泄露" >> "$REPORT_DIR/security_summary.md"
    fi

    if [[ -f "$REPORT_DIR/secrets/potential_secrets.txt" ]]; then
        potential_secrets=$(wc -l < "$REPORT_DIR/secrets/potential_secrets.txt")
        echo "- 模式匹配: $potential_secrets 个潜在密钥" >> "$REPORT_DIR/security_summary.md"
    fi

    echo "" >> "$REPORT_DIR/security_summary.md"
    echo "## 详细报告" >> "$REPORT_DIR/security_summary.md"
    echo "查看各工具的详细报告：" >> "$REPORT_DIR/security_summary.md"
    echo "- Safety: [report.txt](safety/report.txt)" >> "$REPORT_DIR/security_summary.md"
    echo "- Trivy: [image.txt](trivy/image.txt)" >> "$REPORT_DIR/security_summary.md"
    echo "- Bandit: [report.txt](bandit/report.txt)" >> "$REPORT_DIR/security_summary.md"
    echo "- Semgrep: [report.txt](semgrep/report.txt)" >> "$REPORT_DIR/security_summary.md"
    echo "- Gitleaks: [report.json](gitleaks/report.json)" >> "$REPORT_DIR/security_summary.md"
    echo "- 密钥扫描: [potential_secrets.txt](secrets/potential_secrets.txt)" >> "$REPORT_DIR/security_summary.md"
    echo "- 权限检查: [dir_permissions.txt](permissions/dir_permissions.txt)" >> "$REPORT_DIR/security_summary.md"

    echo "" >> "$REPORT_DIR/security_summary.md"
    echo "## 建议" >> "$REPORT_DIR/security_summary.md"
    echo "1. 修复所有高危漏洞" >> "$REPORT_DIR/security_summary.md"
    echo "2. 移除硬编码的密钥和敏感信息" >> "$REPORT_DIR/security_summary.md"
    echo "3. 定期更新依赖项" >> "$REPORT_DIR/security_summary.md"
    echo "4. 启用CI/CD中的自动化安全扫描" >> "$REPORT_DIR/security_summary.md"
    echo "5. 实施最小权限原则" >> "$REPORT_DIR/security_summary.md"

    log_info "安全报告已生成: $REPORT_DIR/security_summary.md"
}

# 修复常见问题
fix_common_issues() {
    log_step "修复常见安全问题..."

    # 删除硬编码密码
    log_info "检查并提示删除硬编码密码..."
    grep -r "password\s*=\s*['\"][^'\"]*['\"]" "$SCAN_DIR/src" \
        --include="*.py" | head -5 > "$REPORT_DIR/issues/hardcoded_passwords.txt" || true

    # 修复文件权限
    log_info "修复文件权限..."
    if [[ -f "$SCAN_DIR/.env" ]]; then
        chmod 600 "$SCAN_DIR/.env"
        echo "已修复.env文件权限" >> "$REPORT_DIR/fixes/permissions.txt"
    fi

    # 检查不安全的默认设置
    log_info "检查不安全的默认设置..."
    grep -r "debug.*=.*True" "$SCAN_DIR" \
        --include="*.py" --include="*.yml" --include="*.yaml" > "$REPORT_DIR/issues/debug_enabled.txt" || true
}

# 安装扫描工具
install_tools() {
    log_step "安装安全扫描工具..."

    # Python工具
    pip install --quiet \
        safety \
        bandit \
        semgrep \
        trivy \
        gitleaks \
        tfsec 2>/dev/null || echo "部分工具已存在或安装失败"

    # 如果有Go，安装Go工具
    if command -v go &> /dev/null; then
        go install github.com/zricethezav/znoyder/znoyder@latest > /dev/null 2>&1 || true
    fi

    log_info "安全工具安装完成"
}

# 创建CI/CD配置
create_cicd_security() {
    log_step "创建CI/CD安全配置..."

    # GitHub Actions工作流
    cat > .github/workflows/security.yml <<'EOF'
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

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install safety bandit semgrep

      - name: Run Bandit security scan
        run: |
          bandit -r src/ -f json -o bandit-report.json
          bandit -r src/

      - name: Run Safety dependency check
        run: |
          safety check --json --output safety-report.json
          safety check

      - name: Run Semgrep scan
        run: |
          semgrep --config=auto --json --output semgrep-report.json src/
          semgrep --config=auto src/

      - name: Run Gitleaks secret scan
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy scan results to GitHub Security tab
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Upload security reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: security-reports
          path: |
            bandit-report.json
            safety-report.json
            semgrep-report.json
            trivy-results.sarif
EOF

    log_info "CI/CD安全配置已创建: .github/workflows/security.yml"
}

# 主函数
main() {
    echo ""
    echo "=========================================="
    echo "安全扫描系统"
    echo "=========================================="
    echo ""

    # 检查是否为root用户
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要以root用户运行此脚本"
        exit 1
    fi

    # 安装工具
    install_tools

    # 执行扫描
    create_report_dir
    scan_dependencies
    run_static_analysis
    scan_containers
    scan_infrastructure
    scan_secrets
    scan_network
    check_permissions
    generate_report
    fix_common_issues
    create_cicd_security

    echo ""
    echo "=========================================="
    echo "安全扫描完成！"
    echo "=========================================="
    echo ""
    echo "报告位置: $REPORT_DIR"
    echo ""
    echo "下一步："
    echo "1. 查看报告摘要: cat $REPORT_DIR/security_summary.md"
    echo "2. 修复发现的问题"
    echo "3. 在CI/CD中启用自动化扫描"
    echo ""
}

# 执行主函数
main "$@"
