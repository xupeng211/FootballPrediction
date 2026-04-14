#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${GATEKEEPER_COMPOSE_FILE:-docker-compose.dev.yml}"
DEV_SERVICE="${GATEKEEPER_DEV_SERVICE:-dev}"
MODE="${GATEKEEPER_MODE:-push}"
WORKSPACE_ROOT="${GATEKEEPER_WORKSPACE_ROOT:-/app}"
CONTAINER_GATEKEEPER_PATH="${WORKSPACE_ROOT%/}/scripts/devops/gatekeeper.sh"

for arg in "$@"; do
  case "$arg" in
    --mode=commit)
      MODE="commit"
      ;;
    --mode=pr)
      MODE="pr"
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

  ensure_container_gatekeeper() {
    if "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" exec -T "$DEV_SERVICE" test -f "$CONTAINER_GATEKEEPER_PATH"; then
      return 0
    fi

    log "容器内未找到 ${CONTAINER_GATEKEEPER_PATH}，强制重建 ${DEV_SERVICE} 后重试。"
    "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" up -d --force-recreate "$DEV_SERVICE" db redis >/dev/null

    "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" exec -T "$DEV_SERVICE" test -f "$CONTAINER_GATEKEEPER_PATH" \
      || fail "容器内仍缺少 ${CONTAINER_GATEKEEPER_PATH}，请检查 docker-compose 挂载。"
  }

  resolve_compose
  cd "$ROOT_DIR"

  UP_ARGS=(-d)
  if [[ "${GATEKEEPER_BUILD:-0}" == "1" ]]; then
    UP_ARGS=(-d --build)
  fi

  log "准备开发容器（mode=${MODE}）..."
  "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" up "${UP_ARGS[@]}" "$DEV_SERVICE" db redis >/dev/null

  ensure_container_gatekeeper

  log '切入 dev 容器执行门禁。'
  "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" exec -T "$DEV_SERVICE" \
    env GATEKEEPER_IN_CONTAINER=1 GATEKEEPER_MODE="$MODE" GATEKEEPER_WORKSPACE_ROOT="$WORKSPACE_ROOT" \
    bash "$CONTAINER_GATEKEEPER_PATH"
  exit $?
fi

cd "$WORKSPACE_ROOT" || fail "容器工作目录不存在: ${WORKSPACE_ROOT}"

readonly MODE
readonly WORKSPACE_ROOT
readonly CONTAINER_GATEKEEPER_PATH
readonly PORT_REGEX='7890|7891|7892|7893|7894|7895|7896|7897|7898|7899|7900|7901|7902|7903|7904|7905|7906|7907|7908|7909|7910|7911|7912'
readonly LEAK_REGEX="172\\.25\\.16\\.1|\\b(${PORT_REGEX})\\b"
readonly CONTRACT_REGEX='require\(["'"'"'](axios|node-fetch|got|http|https|node:http|node:https|http-proxy-agent|https-proxy-agent)["'"'"']\)|from ["'"'"'](axios|node-fetch|got|undici)["'"'"']'
readonly PYTHON_FILE_LINE_LIMIT=800
readonly COVERAGE_THRESHOLD=80
readonly COVERAGE_DIR='reports/coverage'
readonly NODE_COVERAGE_SUMMARY="${COVERAGE_DIR}/node/coverage-summary.json"
readonly PYTHON_COVERAGE_JSON="${COVERAGE_DIR}/python/coverage.json"

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
  if [[ ! -x node_modules/.bin/eslint || ! -x node_modules/.bin/c8 ]]; then
    log 'Node 依赖缺失，执行 npm install 补齐开发工具链。'
    npm install --no-fund --no-audit >/dev/null
  fi
}

bootstrap_python_dependencies() {
  if ! python -m mypy --version >/dev/null 2>&1 \
    || ! python -m ruff --version >/dev/null 2>&1 \
    || ! python -c 'import pytest_cov' >/dev/null 2>&1; then
    log 'Python QA 依赖缺失，执行 pip install -r requirements.txt。'
    pip install --no-cache-dir -r requirements.txt >/dev/null
  fi
}

ensure_git_context() {
  if command -v git >/dev/null 2>&1; then
    if ! git config --global --add safe.directory "$WORKSPACE_ROOT" >/dev/null 2>&1; then
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
  command -v pytest >/dev/null 2>&1 || fail '容器内缺少 pytest。'
  python -m mypy --version >/dev/null 2>&1 || fail '容器内缺少 mypy，请先重建开发镜像。'
  python -m ruff --version >/dev/null 2>&1 || fail '容器内缺少 ruff，请先重建开发镜像。'
  python -c 'import pytest_cov' >/dev/null 2>&1 || fail '容器内缺少 pytest-cov，请先重建开发镜像。'
  [[ -x node_modules/.bin/eslint ]] || fail '项目依赖中缺少 eslint。'
  [[ -x node_modules/.bin/c8 ]] || fail '项目依赖中缺少 c8。'
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

    if grep -qE 'from src\.config import|import src\.config|get_settings|get_shared_proxy_pool_config|proxy_server_template|proxy_ports|proxy_wsl2_host' "$file"; then
      continue
    fi

    findings+=("$line")
  done < <(
    run_optional_grep '(^|[[:space:]])(import|from)[[:space:]]+(requests|httpx|aiohttp|curl_cffi)(\.|[[:space:]]|$)' "${py_files[@]}"
  )

  if [[ "${#findings[@]}" -gt 0 ]]; then
    printf '[Gatekeeper] 命中未接入统一代理配置的 Python 底层网络调用:\n' >&2
    printf '  %s\n' "${findings[@]}" >&2
    fail '发现 Python 侧绕过 src.config / ProxyProvider 的网络依赖，请先接入统一代理配置。'
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

    if [[ "$file" == src/config/*.py ]]; then
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

run_config_compat_guard() {
  log '执行 src.config_unified 兼容壳收口检查。'

  mapfile -t changed_files < <(collect_changed_files | sed '/^$/d' | sort -u)
  local findings=()
  local file

  for file in "${changed_files[@]}"; do
    [[ -f "$file" ]] || continue
    case "$file" in
      src/*.py|src/**/*.py)
        if grep -nE '(^|[[:space:]])(from|import)[[:space:]]+src\.config_unified([[:space:]]|$|\.)' "$file" >/dev/null 2>&1; then
          findings+=("$file")
        fi
        ;;
    esac
  done

  if [[ "${#findings[@]}" -gt 0 ]]; then
    printf '[Gatekeeper] 命中内部兼容壳引用:\n' >&2
    printf '  %s\n' "${findings[@]}" >&2
    fail 'src/ 内部 Python 模块禁止继续引用 src.config_unified，请直接改用 src.config。'
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

run_js_incremental_gate() {
  log '执行增量 JS 测试门禁。'
  local changed_files=()

  mapfile -t changed_files < <(collect_changed_files | sed '/^$/d' | sort -u)
  if [[ "${#changed_files[@]}" -eq 0 ]]; then
    log '未检测到显式变更文件，回退到关键烟雾测试。'
    node scripts/test/run_test_suite.js affected
    return 0
  fi

  node scripts/test/run_test_suite.js affected "${changed_files[@]}"
}

run_coverage_report() {
  python <<'PY'
import json
import os
from pathlib import Path

node_summary_path = Path("reports/coverage/node/coverage-summary.json")
python_summary_path = Path("reports/coverage/python/coverage.json")
workspace_root = os.environ.get("GATEKEEPER_WORKSPACE_ROOT", "/app").rstrip("/")
workspace_prefix = f"{workspace_root}/" if workspace_root else ""

def normalize_path(file_path: str) -> str:
    if workspace_prefix and file_path.startswith(workspace_prefix):
        return file_path[len(workspace_prefix):]
    return file_path

def read_node_summary() -> tuple[dict, list[str]]:
    if not node_summary_path.exists():
        return {}, []

    payload = json.loads(node_summary_path.read_text(encoding="utf-8"))
    total = payload.get("total", {})
    bare = []
    for file_path, summary in payload.items():
        if file_path == "total":
            continue
        lines = summary.get("lines", {})
        if float(lines.get("pct", 0.0) or 0.0) == 0.0:
            bare.append(normalize_path(file_path))

    return total, sorted(bare)

def read_python_summary() -> tuple[dict, list[str]]:
    if not python_summary_path.exists():
        return {}, []

    payload = json.loads(python_summary_path.read_text(encoding="utf-8"))
    total = payload.get("totals", {})
    bare = []
    for file_path, summary in payload.get("files", {}).items():
        summary_block = summary.get("summary", {})
        percent = float(summary_block.get("percent_covered", 0.0) or 0.0)
        if percent == 0.0:
            bare.append(normalize_path(file_path))

    return total, sorted(bare)

def pct(value: float | int | None) -> str:
    if value is None:
        return "  N/A"
    return f"{float(value):5.1f}%"

node_total, node_bare = read_node_summary()
python_total, python_bare = read_python_summary()

node_lines_total = float(node_total.get("lines", {}).get("total", 0.0) or 0.0)
node_lines_covered = float(node_total.get("lines", {}).get("covered", 0.0) or 0.0)
python_lines_total = float(python_total.get("num_statements", 0.0) or 0.0)
python_lines_covered = float(python_total.get("covered_lines", 0.0) or 0.0)
combined_total = node_lines_total + python_lines_total
combined_pct = ((node_lines_covered + python_lines_covered) / combined_total * 100.0) if combined_total else 0.0

rows = [
    (
        "Node",
        pct(node_total.get("lines", {}).get("pct")),
        pct(node_total.get("branches", {}).get("pct")),
        pct(node_total.get("functions", {}).get("pct")),
    ),
    (
        "Python",
        pct(python_total.get("percent_covered")),
        "  N/A",
        "  N/A",
    ),
    (
        "Combined",
        f"{combined_pct:5.1f}%",
        "  N/A",
        "  N/A",
    ),
]

border = "┌──────────┬────────┬──────────┬──────────┐"
separator = "├──────────┼────────┼──────────┼──────────┤"
footer = "└──────────┴────────┴──────────┴──────────┘"

print("[Gatekeeper] 覆盖率汇总:")
print(border)
print("│ Scope    │ Lines  │ Branches │ Functions│")
print(separator)
for scope, lines, branches, functions in rows:
    print(f"│ {scope:<8} │ {lines:>6} │ {branches:>8} │ {functions:>8}│")
print(footer)

if node_bare:
    print("[Gatekeeper] JS 裸奔文件（0%）:")
    for file_path in node_bare[:10]:
        print(f"  - {file_path}")
    if len(node_bare) > 10:
        print(f"  - ... 还有 {len(node_bare) - 10} 个")

if python_bare:
    print("[Gatekeeper] Python 裸奔文件（0%）:")
    for file_path in python_bare[:10]:
        print(f"  - {file_path}")
    if len(python_bare) > 10:
        print(f"  - ... 还有 {len(python_bare) - 10} 个")
PY
}

run_js_coverage_guard() {
  log "执行 Node 覆盖率门禁（阈值 ${COVERAGE_THRESHOLD}%）。"
  rm -rf "${COVERAGE_DIR}/node"
  mkdir -p "${COVERAGE_DIR}/node"
  npm run test:coverage
}

run_python_coverage_guard() {
  log "执行 Python 覆盖率门禁（阈值 ${COVERAGE_THRESHOLD}%）。"
  rm -rf "${COVERAGE_DIR}/python"
  mkdir -p "${COVERAGE_DIR}/python"
  python -m pytest \
    tests/unit/config_package_test.py \
    --cov=src/config \
    --cov-report=term-missing:skip-covered \
    --cov-report="json:${PYTHON_COVERAGE_JSON}"

  python <<'PY'
import json
import os
import sys
from pathlib import Path

threshold = float(os.environ.get("GATEKEEPER_COVERAGE_THRESHOLD", "70"))
summary_path = Path("reports/coverage/python/coverage.json")
payload = json.loads(summary_path.read_text(encoding="utf-8"))
coverage = float(payload["totals"]["percent_covered"])

if coverage < threshold:
    print(
        f"[Gatekeeper] ERROR: Python 覆盖率 {coverage:.1f}% 低于阈值 {threshold:.1f}%",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"[Gatekeeper] Python 覆盖率达标: {coverage:.1f}%")
PY
}

run_coverage_guards() {
  export GATEKEEPER_COVERAGE_THRESHOLD="${COVERAGE_THRESHOLD}"
  run_js_coverage_guard
  run_python_coverage_guard
  run_coverage_report
}

run_recon_core_coverage_guard() {
  log '执行 Recon 核心独立覆盖率门禁（行覆盖率 >= 90%）。'
  npm run test:coverage:recon-core
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
  run_config_compat_guard
  run_python_architecture_guard
  run_static_quality_checks
  run_proxyprovider_smoke_test

  if [[ "$MODE" == "pr" ]]; then
    run_js_incremental_gate
    run_recon_core_coverage_guard
  fi

  if [[ "$MODE" == "push" ]]; then
    run_coverage_guards
    run_recon_core_coverage_guard
  fi

  log "门禁通过（mode=${MODE}）。"
}

main "$@"
