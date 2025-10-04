#!/usr/bin/env bash
set -e
echo "🔍 Verifying dependency consistency..."

pip check || (echo "❌ pip check failed" && exit 1)

if [ -f requirements/base.in ]; then
  pip-compile requirements/base.in --quiet --output-file=/tmp/base.lock
  # 忽略头部注释差异（第1-6行），只比较依赖内容
  if ! tail -n +7 requirements/base.lock | diff -q - <(tail -n +7 /tmp/base.lock) >/dev/null; then
    echo "⚠️  base.lock 与 base.in 不一致，请执行 make lock-deps"
    exit 1
  fi
fi

echo "✅ Dependencies are consistent"