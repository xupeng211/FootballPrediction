#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${GATEKEEPER_COMPOSE_FILE:-docker-compose.dev.yml}"
DEV_SERVICE="${GATEKEEPER_DEV_SERVICE:-dev}"
MODE="${GATEKEEPER_MODE:-push}"

for arg in "$@"; do
  case "$arg" in
    --mode=commit)
      MODE="commit"
      ;;
    --mode=push|--mode=full)
      MODE="push"
      ;;
  esac
done

log() {
  printf '[Gatekeeper] %s\n' "$*"
}

fail() {
  printf '[Gatekeeper] ERROR: %s\n' "$*" >&2
  exit 1
}

if [[ "${GATEKEEPER_IN_CONTAINER:-0}" != "1" ]]; then
  resolve_compose() {
    if docker compose version >/dev/null 2>&1; then
      COMPOSE_CMD=(docker compose)
      return 0
    fi

    if docker-compose version >/dev/null 2>&1; then
      COMPOSE_CMD=(docker-compose)
      return 0
    fi

    fail '未找到 docker compose 或 docker-compose，无法启动容器门禁。'
  }

  resolve_compose
  cd "$ROOT_DIR"

  UP_ARGS=(-d)
  if [[ "${GATEKEEPER_BUILD:-0}" == "1" ]]; then
    UP_ARGS=(-d --build)
  fi

  log "准备开发容器（mode=${MODE}）..."
  "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" up "${UP_ARGS[@]}" "$DEV_SERVICE" db redis >/dev/null

  log '切入 dev 容器执行门禁。'
  "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" exec -T "$DEV_SERVICE" \
    env GATEKEEPER_IN_CONTAINER=1 GATEKEEPER_MODE="$MODE" \
    bash "/app/scripts/devops/gatekeeper.sh"
  exit $?
fi

cd /app

readonly MODE
readonly PORT_REGEX='7890|7891|7892|7893|7894|7895|7896|7897|7898|7899|7900|7901|7902|7903|7904|7905|7906|7907|7908|7909|7910|7911'
readonly LEAK_REGEX="172\\.25\\.16\\.1|\\b(${PORT_REGEX})\\b"
readonly CONTRACT_REGEX='require\(["'"'"'](axios|node-fetch|got|http|https|node:http|node:https|http-proxy-agent|https-proxy-agent)["'"'"']\)|from ["'"'"'](axios|node-fetch|got|undici)["'"'"']'
readonly PYTHON_FILE_LINE_LIMIT=800

path_is_leak_allowlisted() {
  local file="$1"
  case "$file" in
    scripts/devops/gatekeeper.sh|config/proxy_pool.json|config/active_registry.json|config/.env)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

path_is_contract_allowlisted() {
  local file="$1"
  case "$file" in
    src/infrastructure/recon/ReconHealthServer.js|src/infrastructure/monitoring/MetricsClient.js|scripts/ops/generate_league_dictionary.js|scripts/ops/titan_seeder.js)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

path_is_python_contract_allowlisted() {
  local file="$1"
  case "$file" in
    src/infrastructure/network/stealth_client.py|src/utils/notifier.py)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

collect_scan_files() {
  local roots=(src scripts config .github .githooks package.json)
  local files=()
  local root

  for root in "${roots[@]}"; do
    if [[ -f "$root" ]]; then
      files+=("$root")
      continue
    fi

    if [[ -d "$root" ]]; then
      while IFS= read -r file; do
        files+=("$file")
      done < <(
        find "$root" -type f \
          ! -name '*.md' \
          ! -name '*.disabled' \
          ! -path '*/tests/*' \
          ! -path '*/node_modules/*' \
          ! -path '*/docs/*' \
          ! -path '*/archive_vault_2026/*' \
          ! -path '*/logs/*' \
          ! -path '*/tmp/*' \
          ! -path '*/__pycache__/*'
      )
    fi
  done

  printf '%s\n' "${files[@]}" | sort -u
}

path_is_python_quality_target() {
  local file="$1"

  case "$file" in
    src/*.py|src/**/*.py|scripts/ops/*.py|scripts/ops/**/*.py|scripts/devops/*.py|scripts/devops/**/*.py|tests/*.py|tests/**/*.py)
      ;;
    *)
      return 1
      ;;
  esac

  case "$file" in
    */tests/fixtures/*|tests/fixtures/*|scripts/maintenance/archives/*|archive_vault_2026/*|legacy_research/*)
      return 1
      ;;
  esac

  return 0
}

collect_changed_files() {
  local git_base=''

  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if git diff --cached --quiet --exit-code; then
      :
    else
      git diff --cached --name-only --diff-filter=ACMR
      git ls-files --others --exclude-standard
      return 0
    fi

    if ! git diff --quiet --exit-code HEAD --; then
      git diff --name-only --diff-filter=ACMR HEAD
      git ls-files --others --exclude-standard
      return 0
    fi

    if [[ -n "${GITHUB_BASE_REF:-}" ]] && git rev-parse --verify "origin/${GITHUB_BASE_REF}" >/dev/null 2>&1; then
      git_base="$(git merge-base HEAD "origin/${GITHUB_BASE_REF}")"
      git diff --name-only --diff-filter=ACMR "${git_base}...HEAD"
      return 0
    fi

    if git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
      git diff --name-only --diff-filter=ACMR HEAD~1..HEAD
      return 0
    fi

    git diff --name-only --diff-filter=ACMR HEAD
    return 0
  fi

  return 0
}

resolve_python_quality_targets() {
  local changed_files=()
  local python_files=()
  local file

  mapfile -t changed_files < <(collect_changed_files | sed '/^$/d' | sort -u)

  for file in "${changed_files[@]}"; do
    if path_is_python_quality_target "$file"; then
      python_files+=("$file")
    fi
  done

  if [[ "${#python_files[@]}" -eq 0 ]]; then
    return 0
  fi

  printf '%s\n' "${python_files[@]}" | sort -u
}

bootstrap_node_dependencies() {
  if [[ ! -x node_modules/.bin/eslint ]]; then
    log 'Node 依赖缺失，执行 npm install 补齐开发工具链。'
    npm install --no-fund --no-audit >/dev/null
  fi
}

bootstrap_python_dependencies() {
  if ! python -m mypy --version >/dev/null 2>&1 || ! python -m ruff --version >/dev/null 2>&1; then
    log 'Python QA 依赖缺失，执行 pip install -r requirements.txt。'
    pip install --no-cache-dir -r requirements.txt >/dev/null
  fi
}

ensure_git_context() {
  if command -v git >/dev/null 2>&1; then
    if ! git config --global --add safe.directory /app >/dev/null 2>&1; then
      log 'safe.directory 注入失败，继续执行当前门禁。'
    fi
  fi
}

run_optional_grep() {
  local pattern="$1"
  shift

  local status=0
  grep -nHE "$pattern" "$@" 2>/dev/null || status=$?
  if [[ "$status" -ne 0 && "$status" -ne 1 ]]; then
    return "$status"
  fi

  return 0
}

assert_quality_tooling() {
  command -v node >/dev/null 2>&1 || fail '容器内缺少 node。'
  command -v npm >/dev/null 2>&1 || fail '容器内缺少 npm。'
  python -m mypy --version >/dev/null 2>&1 || fail '容器内缺少 mypy，请先重建开发镜像。'
  python -m ruff --version >/dev/null 2>&1 || fail '容器内缺少 ruff，请先重建开发镜像。'
  [[ -x node_modules/.bin/eslint ]] || fail '项目依赖中缺少 eslint。'
}

validate_proxy_pool_file() {
  log '校验共享代理池配置文件。'
  [[ -f config/proxy_pool.json ]] || fail '缺少 config/proxy_pool.json。'

  node <<'NODE'
const fs = require('node:fs');
const filePath = './config/proxy_pool.json';
const raw = fs.readFileSync(filePath, 'utf8');
const config = JSON.parse(raw);

if (!config || typeof config !== 'object' || Array.isArray(config)) {
  throw new Error('proxy_pool.json 顶层必须为对象');
}
if (typeof config.host !== 'string' || config.host.trim() === '') {
  throw new Error('proxy_pool.json.host 必须为非空字符串');
}
if (typeof config.protocol !== 'string' || config.protocol.trim() === '') {
  throw new Error('proxy_pool.json.protocol 必须为非空字符串');
}
if (!Array.isArray(config.ports) || config.ports.length === 0) {
  throw new Error('proxy_pool.json.ports 必须为非空数组');
}
const ports = config.ports.map(Number);
if (ports.some(port => !Number.isInteger(port) || port <= 0)) {
  throw new Error('proxy_pool.json.ports 必须全部为正整数');
}
if (new Set(ports).size !== ports.length) {
  throw new Error('proxy_pool.json.ports 不能包含重复端口');
}
if (config.defaultPort != null && !ports.includes(Number(config.defaultPort))) {
  throw new Error('proxy_pool.json.defaultPort 必须属于 ports');
}

console.log(`[Gatekeeper] proxy_pool.json OK host=${config.host} ports=${ports.length}`);
NODE
}

validate_cross_language_proxy_source() {
  log '校验 JS/Python 代理真相源一致性。'

  node <<'NODE'
const fs = require('node:fs');
const { resolveProxyPoolConfig } = require('./config/proxy_pool');
const { ProxyProvider } = require('./src/infrastructure/network/ProxyProvider');

const pool = resolveProxyPoolConfig();
fs.writeFileSync('/tmp/gatekeeper-node-proxy.json', JSON.stringify({
  host: pool.host,
  ports: pool.ports,
  defaultPort: pool.defaultPort,
  protocol: pool.protocol,
  serverTemplate: pool.serverTemplate,
  proxyProviderHost: ProxyProvider.resolveHost(),
  proxyProviderPorts: ProxyProvider.resolvePorts()
}, null, 2));
NODE

  python <<'PY'
import json
import os
from pathlib import Path
import re

CONFIG_PATH = Path("config/proxy_pool.json")


def parse_ports(value):
    if isinstance(value, list):
        candidates = value
    elif isinstance(value, str):
        candidates = value.split(",")
    else:
        return []

    ports = []
    for candidate in candidates:
        try:
            port = int(str(candidate).strip())
        except (TypeError, ValueError):
            continue

        if port > 0:
            ports.append(port)

    return ports


def expand_port_range(start, end):
    try:
        range_start = int(start)
        range_end = int(end)
    except (TypeError, ValueError):
        return []

    if range_end < range_start:
        return []

    return list(range(range_start, range_end + 1))


def extract_proxy_host(server_template):
    if not server_template:
        return None

    match = re.match(r"^https?://([^/:]+)", str(server_template))
    return match.group(1) if match else None


file_config = {}
if CONFIG_PATH.exists():
    file_config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

protocol = os.environ.get("PROXY_PROTOCOL") or file_config.get("protocol") or "http"
server_template = os.environ.get("PROXY_SERVER") or file_config.get("serverTemplate") or ""

ports = parse_ports(os.environ.get("PROXY_PORTS"))
if not ports:
    ports = expand_port_range(
        os.environ.get("PROXY_PORT_START"),
        os.environ.get("PROXY_PORT_END"),
    )
if not ports:
    ports = parse_ports(file_config.get("ports"))

host = (
    os.environ.get("WSL2_PROXY_HOST")
    or os.environ.get("PROXY_HOST")
    or extract_proxy_host(server_template)
    or file_config.get("host")
    or "127.0.0.1"
)

try:
    default_port = int(
        os.environ.get("PROXY_PORT")
        or file_config.get("defaultPort")
        or (ports[0] if ports else 0)
    )
except (TypeError, ValueError):
    default_port = ports[0] if ports else 0

if not ports and default_port:
    ports = [default_port]

if not server_template:
    if "{port}" in str(file_config.get("serverTemplate") or ""):
        server_template = str(file_config["serverTemplate"])
    else:
        server_template = f"{protocol}://{host}:{{port}}"

payload = {
    "host": host,
    "ports": ports,
    "defaultPort": default_port,
    "protocol": protocol,
    "serverTemplate": server_template,
    "settingsHost": host,
    "settingsPorts": ports,
    "settingsProtocol": protocol,
    "settingsServerTemplate": server_template,
}
Path("/tmp/gatekeeper-python-proxy.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
PY

  python <<'PY'
import json
from pathlib import Path
import sys

node_payload = json.loads(Path("/tmp/gatekeeper-node-proxy.json").read_text(encoding="utf-8"))
python_payload = json.loads(Path("/tmp/gatekeeper-python-proxy.json").read_text(encoding="utf-8"))

failures = []

if node_payload["host"] != python_payload["host"] or node_payload["host"] != python_payload["settingsHost"]:
    failures.append("host")
if node_payload["ports"] != python_payload["ports"] or node_payload["ports"] != python_payload["settingsPorts"]:
    failures.append("ports")
if node_payload["defaultPort"] != python_payload["defaultPort"]:
    failures.append("defaultPort")
if node_payload["protocol"] != python_payload["protocol"] or node_payload["protocol"] != python_payload["settingsProtocol"]:
    failures.append("protocol")
if node_payload["serverTemplate"] != python_payload["serverTemplate"] or node_payload["serverTemplate"] != python_payload["settingsServerTemplate"]:
    failures.append("serverTemplate")
if node_payload["host"] != node_payload["proxyProviderHost"]:
    failures.append("proxyProviderHost")
if node_payload["ports"] != node_payload["proxyProviderPorts"]:
    failures.append("proxyProviderPorts")

if failures:
    print(f"[Gatekeeper] ERROR: 跨语言代理配置不一致: {', '.join(failures)}", file=sys.stderr)
    sys.exit(1)

print(f"[Gatekeeper] 跨语言代理配置一致: host={node_payload['host']} ports={len(node_payload['ports'])}")
PY
}

run_secret_ip_leak_check() {
  log '执行硬编码 IP/端口泄漏扫描。'

  mapfile -t scan_files < <(collect_scan_files)
  local findings=()
  local line
  local file

  if [[ "${#scan_files[@]}" -eq 0 ]]; then
    fail '未找到可扫描文件，拒绝空跑门禁。'
  fi

  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    file="${line%%:*}"
    file="${file#./}"
    if path_is_leak_allowlisted "$file"; then
      continue
    fi
    findings+=("$line")
  done < <(run_optional_grep "$LEAK_REGEX" "${scan_files[@]}")

  if [[ "${#findings[@]}" -gt 0 ]]; then
    printf '[Gatekeeper] 命中硬编码代理字面量:\n' >&2
    printf '  %s\n' "${findings[@]}" >&2
    fail '检测到代理 IP/端口硬编码，请改为 ProxyProvider 或共享配置。'
  fi
}

run_proxy_contract_check() {
  log '执行 ProxyProvider 契约检查。'

  mapfile -t js_files < <(
    find src scripts config -type f \
      \( -name '*.js' -o -name '*.cjs' -o -name '*.mjs' \) \
      ! -name '*.test.js' \
      ! -name '*.disabled' \
      ! -path '*/node_modules/*' \
      ! -path '*/tests/*' \
      ! -path '*/docs/*' \
      ! -path '*/archive_vault_2026/*' \
      ! -path '*/logs/*' \
      ! -path '*/tmp/*' \
      | sort
  )

  local findings=()
  local line
  local file

  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    file="${line%%:*}"
    file="${file#./}"
    if path_is_contract_allowlisted "$file"; then
      continue
    fi
    if grep -qE 'ProxyProvider|proxyProvider' "$file"; then
      continue
    fi
    findings+=("$line")
  done < <(run_optional_grep "$CONTRACT_REGEX" "${js_files[@]}")

  if [[ "${#findings[@]}" -gt 0 ]]; then
    printf '[Gatekeeper] 命中未接入 ProxyProvider 的底层网络调用:\n' >&2
    printf '  %s\n' "${findings[@]}" >&2
    fail '发现绕过 ProxyProvider 的底层网络依赖，请先接入统一代理层或显式评审白名单。'
  fi
}

run_python_proxy_contract_check() {
  log '执行 Python 代理契约检查。'

  mapfile -t py_files < <(
    find src -type f -name '*.py' \
      ! -path '*/tests/*' \
      ! -path '*/__pycache__/*' \
      | sort
  )

  local findings=()
  local line
  local file

  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    file="${line%%:*}"
    file="${file#./}"

    if path_is_python_contract_allowlisted "$file"; then
      continue
    fi

    if grep -qE 'from src\.config_unified import|get_settings|get_shared_proxy_pool_config|proxy_server_template|proxy_ports|proxy_wsl2_host' "$file"; then
      continue
    fi

    findings+=("$line")
  done < <(
    run_optional_grep '(^|[[:space:]])(import|from)[[:space:]]+(requests|httpx|aiohttp|curl_cffi)(\.|[[:space:]]|$)' "${py_files[@]}"
  )

  if [[ "${#findings[@]}" -gt 0 ]]; then
    printf '[Gatekeeper] 命中未接入统一代理配置的 Python 底层网络调用:\n' >&2
    printf '  %s\n' "${findings[@]}" >&2
    fail '发现 Python 侧绕过 config_unified / ProxyProvider 的网络依赖，请先接入统一代理配置。'
  fi
}

run_python_architecture_guard() {
  log '执行 Python 架构体量检查。'

  mapfile -t python_targets < <(resolve_python_quality_targets)
  if [[ "${#python_targets[@]}" -eq 0 ]]; then
    log '未检测到本次变更涉及 Python 目标文件，跳过巨石文件检查。'
    return 0
  fi

  local findings=()
  local file
  local line_count

  for file in "${python_targets[@]}"; do
    [[ -f "$file" ]] || continue
    line_count="$(wc -l < "$file" | tr -d '[:space:]')"
    if (( line_count <= PYTHON_FILE_LINE_LIMIT )); then
      continue
    fi

    if [[ "$file" == "src/config_unified.py" ]]; then
      fail "检测到‘巨石文件’，请先进行模块化拆分再提交：${file} 当前 ${line_count} 行，已超过 ${PYTHON_FILE_LINE_LIMIT} 行上限。"
    fi

    findings+=("${file}:${line_count}")
  done

  if [[ "${#findings[@]}" -gt 0 ]]; then
    printf '[Gatekeeper] 命中超长 Python 文件（>%s 行）:\n' "$PYTHON_FILE_LINE_LIMIT" >&2
    printf '  %s\n' "${findings[@]}" >&2
    fail '检测到超长 Python 文件，请先拆分模块后再提交。'
  fi
}

run_static_quality_checks() {
  log '执行静态质量检查。'
  local python_targets=()
  local mypy_targets=()
  local file

  npm run lint

  mapfile -t python_targets < <(resolve_python_quality_targets)
  if [[ "${#python_targets[@]}" -eq 0 ]]; then
    log '未检测到本次变更涉及 Python 目标文件，跳过 Python 风格与类型检查。'
    return 0
  fi

  log "Python 质量检查目标数: ${#python_targets[@]}"
  python -m ruff check "${python_targets[@]}"
  python -m ruff format --check "${python_targets[@]}"

  for file in "${python_targets[@]}"; do
    case "$file" in
      src/*.py|src/**/*.py)
        mypy_targets+=("$file")
        ;;
    esac
  done

  if [[ "${#mypy_targets[@]}" -gt 0 ]]; then
    python -m mypy --config-file mypy.ini --follow-imports=silent "${mypy_targets[@]}"
  else
    log '本次变更未触达 src Python 模块，跳过 mypy。'
  fi
}

run_proxyprovider_smoke_test() {
  log '执行 ProxyProvider 契约单测。'
  [[ -f tests/unit/ProxyProvider.test.js ]] || fail '缺少 tests/unit/ProxyProvider.test.js。'
  node --test tests/unit/ProxyProvider.test.js
}

run_full_unit_suite() {
  log '执行容器内全量单测。'
  npm run test:unit
}

main() {
  log "进入门禁容器执行阶段（mode=${MODE}）。"

  ensure_git_context
  bootstrap_node_dependencies
  bootstrap_python_dependencies
  assert_quality_tooling

  validate_proxy_pool_file
  validate_cross_language_proxy_source
  run_secret_ip_leak_check
  run_proxy_contract_check
  run_python_proxy_contract_check
  run_python_architecture_guard
  run_static_quality_checks
  run_proxyprovider_smoke_test

  if [[ "$MODE" == "push" ]]; then
    run_full_unit_suite
  fi

  log "门禁通过（mode=${MODE}）。"
}

main "$@"
