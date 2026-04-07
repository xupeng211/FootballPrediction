#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${INIT_DEV_COMPOSE_FILE:-docker-compose.dev.yml}"
DEV_SERVICE="${INIT_DEV_DEV_SERVICE:-dev}"

resolve_compose() {
  if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose)
    return 0
  fi

  if docker-compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose)
    return 0
  fi

  printf '[InitDev] ERROR: 未找到 docker compose 或 docker-compose。\n' >&2
  exit 1
}

resolve_compose
cd "$ROOT_DIR"

printf '[InitDev] 启动并构建开发容器...\n'
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" up -d --build "$DEV_SERVICE" db redis

printf '[InitDev] 容器内安装 Node/Python 依赖...\n'
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" exec -T "$DEV_SERVICE" bash -lc '
  npm install --no-fund --no-audit &&
  python -m pip install --no-cache-dir -r requirements.txt
'

printf '[InitDev] 安装 Git Hooks...\n'
bash scripts/devops/install_git_hooks.sh

printf '[InitDev] 运行配置与门禁自检...\n'
bash scripts/devops/gatekeeper.sh --mode=commit
