#!/bin/bash
# Phase 7: AI-Driven Coverage Improvement Loop

echo "🤖 Phase 7: AI 覆盖率改进循环"
echo "目标: 将覆盖率从 30% 提升到 40%"

# 设置环境
export PYTHONPATH="src:tests:$PYTHONPATH"

# 分析零覆盖率模块
echo "📍 分析零覆盖率模块..."
python -c "
import os
from pathlib import Path

src_dir = Path('src')
zero_modules = []

for root, dirs, files in os.walk(src_dir):
    for file in files:
        if file.endswith('.py') and not file.startswith('__'):
            module_path = os.path.relpath(os.path.join(root, file), 'src')
            zero_modules.append(module_path.replace('.py', '').replace('/', '.'))

print(f'发现 {len(zero_modules)} 个模块')
for i, module in enumerate(zero_modules[:10], 1):
    print(f'{i}. {module}')
"

# 生成基础测试
echo "🤖 生成AI测试..."
python scripts/phase7_generate_tests.py

# 运行测试验证
echo "✅ 验证生成的测试..."
make test-quick

echo "📊 生成覆盖率报告..."
make coverage-local

echo "✅ Phase 7 完成!"
