#!/usr/bin/env bash

set -euo pipefail

resolve_default_proxy_port() {
  node - <<'NODE'
const fs = require('node:fs');

const fallbackPort = 10001;
try {
  const raw = fs.readFileSync('config/proxy_pool.json', 'utf8');
  const config = JSON.parse(raw);
  const candidates = [
    config.defaultPort,
    ...(Array.isArray(config.active_ports) ? config.active_ports : []),
    ...(Array.isArray(config.ports) ? config.ports : [])
  ];
  const port = candidates.map(Number).find(value => Number.isInteger(value) && value > 0);
  console.log(port || fallbackPort);
} catch {
  console.log(fallbackPort);
}
NODE
}

export PROXY_LOOPBACK_GATEWAY="${PROXY_LOOPBACK_GATEWAY:-172.19.0.1}"
export PROXY_HOST="${PROXY_HOST:-$PROXY_LOOPBACK_GATEWAY}"
export WSL2_PROXY_HOST="${WSL2_PROXY_HOST:-$PROXY_HOST}"
export PROXY_PROTOCOL="${PROXY_PROTOCOL:-socks5}"
export HOST_PROXY_PORT="${HOST_PROXY_PORT:-${DEV_HOST_PROXY_PORT:-$(resolve_default_proxy_port)}}"
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
