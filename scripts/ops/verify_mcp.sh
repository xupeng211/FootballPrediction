#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

pass() {
  printf '[OK] %s\n' "$1"
}

warn() {
  printf '[WARN] %s\n' "$1"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf '[ERR] 缺少命令: %s\n' "$1" >&2
    exit 1
  fi
}

echo '== MCP 配置验证 =='

require_cmd python3
require_cmd docker-compose

python3 -m json.tool .claude/mcp-config.json >/dev/null
pass '.claude/mcp-config.json JSON 格式有效'

python3 -m py_compile mcp_servers/pytest_server.py mcp_servers/docker_server.py
pass 'MCP Python 入口脚本可编译'

python3 - <<'PY'
import docker
import mcp
from mcp_servers.pytest_server import run_pytest

print(f"docker_py={docker.__version__}")
print(f"mcp_sdk={getattr(mcp, '__file__', 'loaded')}")
print(f"pytest_runner={run_pytest.__name__}")
PY
pass '宿主机 Python 侧依赖可导入'

docker-compose -f docker-compose.dev.yml ps >/dev/null
pass 'docker-compose 配置可解析'

if docker-compose -f docker-compose.dev.yml ps --services --filter status=running | grep -qx 'dev'; then
  docker-compose -f docker-compose.dev.yml exec -T dev python - <<'PY'
import pandas
import pytest

print(f"pandas={pandas.__version__}")
print(f"pytest={pytest.__version__}")
PY
  pass 'dev 容器内 pytest / pandas 可用'
else
  warn 'dev 容器未运行，跳过容器内 Python 依赖检查'
fi

cat <<'EOF'

== MCP 重载步骤 ==
1. 如果修改了 .claude/mcp-config.json 或 mcp_servers/*.py，当前 Claude/Codex 会话不会热加载。
2. 退出当前客户端会话。
3. 在仓库根目录重新启动客户端。
4. 重新运行 bash scripts/ops/verify_mcp.sh 确认变更已生效。
EOF
