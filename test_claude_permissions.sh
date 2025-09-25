#!/bin/bash

echo "=== 测试 1: --permission-mode bypassPermissions ==="
echo "claude --permission-mode bypassPermissions -p 'echo \"测试1 - 不需要确认吗？\"'"

echo ""
echo "=== 测试 2: --dangerously-skip-permissions ==="
echo "claude --dangerously-skip-permissions -p 'echo \"测试2 - 不需要确认吗？\"'"

echo ""
echo "=== 测试 3: --allowed-tools ==="
echo "claude --allowed-tools '*' -p 'echo \"测试3 - 不需要确认吗？\"'"
