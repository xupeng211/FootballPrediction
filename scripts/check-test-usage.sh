#!/bin/bash
# 检查是否使用了错误的测试命令

# 检查最近的命令是否错误地运行了单个文件
check_last_command() {
    # 获取最近的 git 提交信息
    if git log -1 --pretty=format:%s | grep -q "test"; then
        echo ""
        echo "🧪 测试提醒："
        echo "------------"
        echo "确保使用了正确的测试命令："
        echo "✅ make test-phase1"
        echo "✅ make coverage"
        echo "❌ pytest tests/unit/api/test_xxx.py --cov=src"
        echo ""
    fi
}

# 检查即将提交的文件中是否有测试文件
if git diff --cached --name-only | grep -q "test_.*\.py"; then
    echo ""
    echo "⚠️  检测到测试文件变更，请确保："
    echo "1. 使用 'make test-quick' 验证测试"
    echo "2. 使用 'make coverage' 检查覆盖率"
    echo "3. 不要使用 'pytest single_file.py --cov=src'"
    echo ""
fi

check_last_command
