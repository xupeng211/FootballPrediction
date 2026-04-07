#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOKS_DIR="${ROOT_DIR}/.githooks"

if ! command -v git >/dev/null 2>&1; then
  printf '[Hooks] ERROR: git 不可用，无法安装仓库 Hook。\n' >&2
  exit 1
fi

cd "$ROOT_DIR"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  printf '[Hooks] 非 Git 仓库，跳过 Hook 安装。\n'
  exit 0
fi

if [[ ! -d "$HOOKS_DIR" ]]; then
  printf '[Hooks] ERROR: 缺少 .githooks 目录。\n' >&2
  exit 1
fi

find "$HOOKS_DIR" -type f -exec chmod +x {} +
git config --local core.hooksPath .githooks

printf '[Hooks] core.hooksPath 已指向 .githooks。\n'
