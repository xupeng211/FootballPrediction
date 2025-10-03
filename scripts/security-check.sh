#!/bin/bash
# 安全检查脚本

echo "🔍 执行安全检查..."

echo "1. 扫描依赖漏洞..."
pip-audit -r requirements.txt --severity="high,critical"

echo -e "
2. 扫描代码安全问题..."
bandit -r src/ -f text

echo -e "
3. 检查敏感文件..."
find . -type f -name "*.env*" -not -path "./.git/*" | head -10

echo -e "
4. 检查权限问题..."
find . -type f -name "*.key" -o -name "*.pem" | head -10

echo -e "
✅ 安全检查完成"
