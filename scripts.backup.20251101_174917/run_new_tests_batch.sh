#!/bin/bash
# 快速运行新创建的测试

echo "🧪 运行新创建的测试..."
echo ""

# 运行新测试
pytest tests/unit/*_test.py -v --tb=short --maxfail=10 -x --disable-warnings

echo ""
echo "✅ 测试完成！"
echo ""
echo "查看覆盖率:"
echo "  make coverage-local"
echo ""
echo "提升更多覆盖率:"
echo "  python scripts/super_boost_coverage.py"
