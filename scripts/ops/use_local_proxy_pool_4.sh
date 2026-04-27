#!/usr/bin/env bash

set -euo pipefail

export PROXY_LOOPBACK_GATEWAY="${PROXY_LOOPBACK_GATEWAY:-172.19.0.1}"
export PROXY_HOST="${PROXY_HOST:-$PROXY_LOOPBACK_GATEWAY}"
export WSL2_PROXY_HOST="${WSL2_PROXY_HOST:-$PROXY_HOST}"
export PROXY_PROTOCOL="${PROXY_PROTOCOL:-socks5}"
export HOST_PROXY_PORT="${HOST_PROXY_PORT:-10001}"
export PROXY_PORT="${PROXY_PORT:-$HOST_PROXY_PORT}"
export PROXY_PORT_START="${PROXY_PORT_START:-$HOST_PROXY_PORT}"
export PROXY_PORT_END="${PROXY_PORT_END:-$HOST_PROXY_PORT}"
export PROXY_PORTS="${PROXY_PORTS:-$HOST_PROXY_PORT}"

export HTTP_PROXY="http://${PROXY_HOST}:${HOST_PROXY_PORT}"
export HTTPS_PROXY="http://${PROXY_HOST}:${HOST_PROXY_PORT}"
export ALL_PROXY="socks5://${PROXY_HOST}:${HOST_PROXY_PORT}"
export http_proxy="$HTTP_PROXY"
export https_proxy="$HTTPS_PROXY"
export all_proxy="$ALL_PROXY"
export NO_PROXY="localhost,${PROXY_HOST}"
export no_proxy="$NO_PROXY"

if [ "$#" -eq 0 ]; then
  echo "用法: bash scripts/ops/use_local_proxy_pool_4.sh <command> [args...]"
  exit 1
fi

exec "$@"
