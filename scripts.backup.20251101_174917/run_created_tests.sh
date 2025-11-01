#!/bin/bash
# 运行新创建的测试

echo "🧪 运行新创建的测试..."
echo ""

# 运行各个目录的测试
for dir in tests/unit/api tests/unit/services tests/unit/database tests/unit/cache tests/unit/streaming; do
    if [ -d "$dir" ] && [ "$(ls -A $dir)" ]; then
        echo "运行 $dir..."
        pytest $dir -v --tb=short --maxfail=5 -x
    fi
done
