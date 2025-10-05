#!/usr/bin/env bash
set -euo pipefail

# 在容器内运行测试，隔离本地依赖。可通过环境变量调整：
#   COMPOSE_FILE      - 指定 docker compose 文件，默认 docker-compose.yml
#   TEST_SERVICE      - 使用的服务名称，默认 app
#   ENABLE_FEAST      - 控制容器内是否启用 Feast，默认 false 以避免依赖冲突
#   TEST_COMMAND      - 覆盖默认的测试命令，默认 "make test"

COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.yml}
TEST_SERVICE=${TEST_SERVICE:-app}
TEST_COMMAND=${TEST_COMMAND:-"make test"}
ENABLE_FEAST=${ENABLE_FEAST:-false}

export ENABLE_FEAST

echo "[docker-test] 使用 compose 文件: ${COMPOSE_FILE}"
echo "[docker-test] 目标服务: ${TEST_SERVICE}"
echo "[docker-test] ENABLE_FEAST=${ENABLE_FEAST}"
echo "[docker-test] 执行命令: ${TEST_COMMAND}"

docker compose -f "${COMPOSE_FILE}" run --rm \
  -e ENABLE_FEAST="${ENABLE_FEAST}" \
  "${TEST_SERVICE}" \
  bash -lc "${TEST_COMMAND}"
