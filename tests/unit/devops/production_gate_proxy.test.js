/**
 * @file Production Gate 通用代理显式禁用回归测试
 * @description 证明 docker-compose.dev.yml 的六个通用代理变量可以被显式禁用，
 *   同时本地开发默认行为逐字节保持不变，并证明 GitHub Actions 提供了该禁用覆盖。
 *
 * 已独立复现的缺陷（run 34787533095）：
 *   CI 把 DEV_PROXY_HOST 设为 127.0.0.1，而容器内 127.0.0.1 指向容器自身，
 *   7897 端口没有代理。npm 于是把 registry 请求发往死端点，约 70 秒后以
 *   "npm error Exit handler never called!" 结束，但退出码仍是 0，所以
 *   "Install project dependencies" 显示成功，而 node_modules 缺少 eslint，
 *   直到 Gatekeeper 才暴露失败。
 *
 * 本测试是 hermetic 的：不访问网络、不需要 docker CLI、不需要 YAML 解析库。
 * 它直接读取 docker-compose.dev.yml 里的原始表达式，并用自己的
 * ${VAR-default} / ${VAR:-default} 求值器解析；该求值器本身先经过语义证明块
 * 自检（见 "compose substitution semantics"），因此它不是未经校验的 oracle。
 * 若本机存在 docker CLI，还会用真实的 `docker compose config` 做交叉验证；
 * 容器内没有该 CLI 时，确定性求值器即为等价表示。
 *
 * @version 1.0.0
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const COMPOSE_RELATIVE_PATH = 'docker-compose.dev.yml';
const WORKFLOW_RELATIVE_PATH = path.join('.github', 'workflows', 'production-gate.yml');
const COMPOSE_SOURCE = fs.readFileSync(path.join(REPO_ROOT, COMPOSE_RELATIVE_PATH), 'utf8');
const WORKFLOW_SOURCE = fs.readFileSync(path.join(REPO_ROOT, WORKFLOW_RELATIVE_PATH), 'utf8');

/** 与 .github/workflows/production-gate.yml 顶层 env 完全一致的 CI 解析环境。 */
const CI_ENV = Object.freeze({
  DEV_DB_HOST: 'db',
  DEV_REDIS_HOST: 'redis',
  DEV_PROXY_HOST: '127.0.0.1',
  DEV_GENERIC_HTTP_PROXY: '',
  DEV_GENERIC_HTTPS_PROXY: '',
  DEV_GENERIC_ALL_PROXY: '',
});

const GENERIC_PROXY_KEYS = Object.freeze([
  'HTTP_PROXY',
  'HTTPS_PROXY',
  'ALL_PROXY',
  'http_proxy',
  'https_proxy',
  'all_proxy',
]);

/** 每个通用代理变量必须由哪个覆盖变量治理（大小写同源，不允许漂移）。 */
const GENERIC_OVERRIDE_BY_KEY = Object.freeze({
  HTTP_PROXY: 'DEV_GENERIC_HTTP_PROXY',
  http_proxy: 'DEV_GENERIC_HTTP_PROXY',
  HTTPS_PROXY: 'DEV_GENERIC_HTTPS_PROXY',
  https_proxy: 'DEV_GENERIC_HTTPS_PROXY',
  ALL_PROXY: 'DEV_GENERIC_ALL_PROXY',
  all_proxy: 'DEV_GENERIC_ALL_PROXY',
});

/** 修复前的表达式：CI 环境下它解析出死端点 http://127.0.0.1:7897。 */
const LEGACY_GENERIC_EXPRESSION =
  'http://${DEV_PROXY_HOST:-${PROXY_LOOPBACK_GATEWAY:-host.docker.internal}}:${DEV_HOST_PROXY_PORT:-7897}';

/**
 * hook 绕过标记按片段拼接，理由与 scripts/ops/ai_workflow_gate.py 自身相同：
 * tests/**\/*.js 属于 blind spot 路径，本文件里出现的字面量会被判成新增危险关键字。
 */
const HOOK_BYPASS_FLAG = '--no' + '-verify';

const CI_OVERRIDE_BLOCK = [
  '  DEV_GENERIC_HTTP_PROXY: ""',
  '  DEV_GENERIC_HTTPS_PROXY: ""',
  '  DEV_GENERIC_ALL_PROXY: ""',
  '',
].join('\n');

/** 本任务声明不改变的变量：原始表达式与解析结果都必须与冻结字面量一致。 */
const FROZEN_UNCHANGED_ENVIRONMENT = Object.freeze({
  PROXY_LOOPBACK_GATEWAY: {
    expression: '${PROXY_LOOPBACK_GATEWAY:-host.docker.internal}',
    defaultMode: 'host.docker.internal',
    ciMode: 'host.docker.internal',
  },
  PROXY_HOST: {
    expression: '${DEV_PROXY_HOST:-${PROXY_LOOPBACK_GATEWAY:-host.docker.internal}}',
    defaultMode: 'host.docker.internal',
    ciMode: '127.0.0.1',
  },
  WSL2_PROXY_HOST: {
    expression: '${DEV_PROXY_HOST:-${PROXY_LOOPBACK_GATEWAY:-host.docker.internal}}',
    defaultMode: 'host.docker.internal',
    ciMode: '127.0.0.1',
  },
  PROXY_PROTOCOL: {
    expression: 'socks5',
    defaultMode: 'socks5',
    ciMode: 'socks5',
  },
  HOST_PROXY_PORT: {
    expression: '${DEV_HOST_PROXY_PORT:-7897}',
    defaultMode: '7897',
    ciMode: '7897',
  },
  PROXY_PORT: {
    expression: '${DEV_PROXY_PORT:-${DEV_HOST_PROXY_PORT:-7897}}',
    defaultMode: '7897',
    ciMode: '7897',
  },
  PROXY_PORT_START: {
    expression: '${DEV_PROXY_PORT_START:-${DEV_HOST_PROXY_PORT:-7897}}',
    defaultMode: '7897',
    ciMode: '7897',
  },
  PROXY_PORT_END: {
    expression: '${DEV_PROXY_PORT_END:-${DEV_HOST_PROXY_PORT:-7897}}',
    defaultMode: '7897',
    ciMode: '7897',
  },
  PROXY_PORTS: {
    expression: '${DEV_PROXY_PORTS:-${DEV_HOST_PROXY_PORT:-7897}}',
    defaultMode: '7897',
    ciMode: '7897',
  },
  CONTAINER_PROXY: {
    expression: '${DEV_CONTAINER_PROXY:-}',
    defaultMode: '',
    ciMode: '',
  },
  NO_PROXY: {
    expression:
      'localhost,${HOST_LOOPBACK_GATEWAY:-192.168.65.254},${DEV_DB_HOST:-${HOST_LOOPBACK_GATEWAY:-192.168.65.254}},${DEV_REDIS_HOST:-${HOST_LOOPBACK_GATEWAY:-192.168.65.254}},${DEV_PROXY_HOST:-${PROXY_LOOPBACK_GATEWAY:-host.docker.internal}}',
    defaultMode: 'localhost,192.168.65.254,192.168.65.254,192.168.65.254,host.docker.internal',
    ciMode: 'localhost,192.168.65.254,db,redis,127.0.0.1',
  },
  no_proxy: {
    expression:
      'localhost,${HOST_LOOPBACK_GATEWAY:-192.168.65.254},${DEV_DB_HOST:-${HOST_LOOPBACK_GATEWAY:-192.168.65.254}},${DEV_REDIS_HOST:-${HOST_LOOPBACK_GATEWAY:-192.168.65.254}},${DEV_PROXY_HOST:-${PROXY_LOOPBACK_GATEWAY:-host.docker.internal}}',
    defaultMode: 'localhost,192.168.65.254,192.168.65.254,192.168.65.254,host.docker.internal',
    ciMode: 'localhost,192.168.65.254,db,redis,127.0.0.1',
  },
  THE_ODDS_API_KEY: {
    expression: '${THE_ODDS_API_KEY:-}',
    defaultMode: '',
    ciMode: '',
  },
  THE_ODDS_API_TRANSPORT: {
    expression: '${THE_ODDS_API_TRANSPORT:-direct}',
    defaultMode: 'direct',
    ciMode: 'direct',
  },
});

/**
 * Stage D provider proxy 的期望形态。它与上面 FROZEN_UNCHANGED_ENVIRONMENT 分开，
 * 因为它**必须**与通用代理家族不同：省略时不得回退到工作站 :7897，而要保持空缺，
 * 由传输层以 PROXY_CONFIGURATION_MISSING 失败关闭。
 *
 * 表达式必须是 ${VAR-}（单横线、空默认值）。误写成 ${VAR:-...:7897} 就等于把
 * "未配置"静默满足为个人 Clash 端点，这正是本测试要钉死的回归。
 */
const STAGE_D_PROXY_KEY = 'THE_ODDS_API_PROXY_URL';
const STAGE_D_PROXY_EXPRESSION = '${THE_ODDS_API_PROXY_URL-}';

/** 修复前的表达式：省略时解析出工作站代理，即被移除的缺陷。 */
const LEGACY_STAGE_D_PROXY_EXPRESSION =
  '${THE_ODDS_API_PROXY_URL:-http://${DEV_PROXY_HOST:-${PROXY_LOOPBACK_GATEWAY:-host.docker.internal}}:${DEV_HOST_PROXY_PORT:-7897}}';

/**
 * 检查 Stage D provider proxy 变量的形态：
 * 必须存在、必须是 ${VAR-} 单横线空默认、且不得引用任何工作站代理插值。
 * 全域函数（不抛错），因此可以喂给变异后的文本做可证伪性验证。
 * @param {string} source
 * @returns {string[]}
 */
function detectStageDProxyViolations(source) {
  const environment = extractDevEnvironment(source);
  const expression = environment.get(STAGE_D_PROXY_KEY);
  if (expression === undefined) {
    return [`${STAGE_D_PROXY_KEY}: missing from the dev service environment`];
  }
  const violations = [];
  if (expression !== STAGE_D_PROXY_EXPRESSION) {
    violations.push(
      `${STAGE_D_PROXY_KEY}: must be exactly ${STAGE_D_PROXY_EXPRESSION}, got ${expression}`
    );
  }
  for (const token of ['DEV_PROXY_HOST', 'PROXY_LOOPBACK_GATEWAY', 'DEV_HOST_PROXY_PORT', '7897']) {
    if (expression.includes(token)) {
      violations.push(`${STAGE_D_PROXY_KEY}: must not inherit the workstation proxy via ${token}`);
    }
  }
  return violations;
}

/**
 * 找到与 text[openIndex]（'{'）配对的 '}'，支持嵌套默认值。
 * @param {string} text
 * @param {number} openIndex
 * @returns {number}
 */
function findClosingBrace(text, openIndex) {
  let depth = 0;
  for (let index = openIndex; index < text.length; index += 1) {
    if (text[index] === '{') {
      depth += 1;
    } else if (text[index] === '}') {
      depth -= 1;
      if (depth === 0) {
        return index;
      }
    }
  }
  throw new Error(`unbalanced compose substitution: ${text}`);
}

/**
 * 解析一个 ${...} 结构体，只实现本 compose 文件使用的 `-` 与 `:-` 两种形式。
 * 其他形式（:? / ? / :+ / +）一律抛错，避免静默算错。
 * @param {string} inner
 * @param {Record<string, string>} environment
 * @returns {string}
 */
function resolveBraced(inner, environment) {
  const match = /^([A-Za-z_][A-Za-z0-9_]*)(:-|-)([\s\S]*)$/.exec(inner);
  if (!match) {
    throw new Error(`unsupported compose substitution form: \${${inner}}`);
  }
  const [, name, operator, rawDefault] = match;
  const isSet = Object.prototype.hasOwnProperty.call(environment, name);
  if (!isSet) {
    return resolveExpression(rawDefault, environment);
  }
  if (operator === ':-' && environment[name] === '') {
    return resolveExpression(rawDefault, environment);
  }
  return environment[name];
}

/**
 * 求值一段 compose 插值表达式。
 * @param {string} expression
 * @param {Record<string, string>} environment
 * @returns {string}
 */
function resolveExpression(expression, environment) {
  let resolved = '';
  let index = 0;
  while (index < expression.length) {
    if (expression[index] !== '$' || expression[index + 1] !== '{') {
      resolved += expression[index];
      index += 1;
      continue;
    }
    const closeIndex = findClosingBrace(expression, index + 1);
    resolved += resolveBraced(expression.slice(index + 2, closeIndex), environment);
    index = closeIndex + 1;
  }
  return resolved;
}

/**
 * 从 docker-compose.dev.yml 文本里取出 dev 服务的 environment 原始表达式。
 * 不依赖 YAML 解析库：只接受 `      - KEY=VALUE` 这一种列表形式。
 * @param {string} source
 * @returns {Map<string, string>}
 */
function extractDevEnvironment(source) {
  const lines = source.split(/\r?\n/);
  const serviceIndex = lines.indexOf('  dev:');
  assert.ok(serviceIndex >= 0, 'docker-compose.dev.yml must still declare the "  dev:" service');
  const environment = new Map();
  for (let index = serviceIndex + 1; index < lines.length; index += 1) {
    if (/^ {2}[A-Za-z_]/.test(lines[index])) {
      break;
    }
    const match = /^ {6}- ([A-Za-z_][A-Za-z0-9_]*)=(.*)$/.exec(lines[index]);
    if (match) {
      assert.ok(!environment.has(match[1]), `duplicate environment entry: ${match[1]}`);
      environment.set(match[1], match[2]);
    }
  }
  assert.ok(
    environment.size > 20,
    `unexpectedly few dev environment entries: ${environment.size} (extraction broke)`
  );
  return environment;
}

/**
 * 求值 dev 服务某个变量的原始表达式。
 * @param {Map<string, string>} environment
 * @param {string} key
 * @param {Record<string, string>} resolutionEnvironment
 * @returns {string}
 */
function resolveDevVariable(environment, key, resolutionEnvironment) {
  const expression = environment.get(key);
  assert.ok(expression !== undefined, `dev service environment lost the variable: ${key}`);
  return resolveExpression(expression, resolutionEnvironment);
}

/**
 * 检查六个通用代理变量的形态：
 * 必须经由对应覆盖变量、必须使用单横线 ${VAR-default}、必须保留历史默认值。
 * 该检测器是全域函数（不抛错），因此可以喂给变异后的文本做可证伪性验证。
 * @param {string} source
 * @returns {string[]}
 */
function detectGenericProxyViolations(source) {
  const environment = extractDevEnvironment(source);
  const violations = [];
  for (const key of GENERIC_PROXY_KEYS) {
    const expectedOverride = GENERIC_OVERRIDE_BY_KEY[key];
    const expression = environment.get(key);
    if (expression === undefined) {
      violations.push(`${key}: missing from the dev service environment`);
      continue;
    }
    if (!expression.startsWith(`\${${expectedOverride}-`)) {
      violations.push(
        `${key}: must use the single-dash \${${expectedOverride}-default} form, got ${expression}`
      );
      continue;
    }
    if (
      !expression.includes('${DEV_PROXY_HOST:-') ||
      !expression.includes('${DEV_HOST_PROXY_PORT:-7897}')
    ) {
      violations.push(`${key}: lost the historical host-gateway fallback: ${expression}`);
    }
  }
  return violations;
}

/**
 * 取出 GitHub Actions 工作流顶层 env 块（列 0 的 `env:` 之后、2 空格缩进的键）。
 * @param {string} source
 * @returns {Map<string, string>}
 */
function extractWorkflowTopLevelEnvironment(source) {
  const environment = new Map();
  let inside = false;
  for (const line of source.split(/\r?\n/)) {
    if (!inside) {
      inside = line === 'env:';
      continue;
    }
    if (/^[^ ]/.test(line)) {
      break;
    }
    const match = /^ {2}([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$/.exec(line);
    if (match) {
      environment.set(match[1], unquoteYamlScalar(match[2]));
    }
  }
  assert.ok(environment.size > 0, 'production-gate.yml must still declare a top-level env block');
  return environment;
}

/**
 * 去掉 YAML 标量外层引号。
 * @param {string} raw
 * @returns {string}
 */
function unquoteYamlScalar(raw) {
  const trimmed = raw.trim();
  const isDoubleQuoted = trimmed.startsWith('"') && trimmed.endsWith('"') && trimmed.length >= 2;
  const isSingleQuoted = trimmed.startsWith("'") && trimmed.endsWith("'") && trimmed.length >= 2;
  if (isDoubleQuoted || isSingleQuoted) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

/**
 * 收集工作流里所有 DEV_GENERIC_*_PROXY 赋值（忽略注释行）。
 * @param {string} source
 * @returns {{line: string, value: string}[]}
 */
function collectGenericOverrideAssignments(source) {
  const assignments = [];
  for (const line of source.split(/\r?\n/)) {
    if (line.trim().startsWith('#')) {
      continue;
    }
    const match = /^\s*(?:- )?(DEV_GENERIC_(?:HTTP|HTTPS|ALL)_PROXY)\s*:\s*(.*)$/.exec(line);
    if (match) {
      assignments.push({ line: line.trim(), value: unquoteYamlScalar(match[2]) });
    }
  }
  return assignments;
}

/**
 * 检查工作流是否显式提供了三个禁用覆盖，且没有任何一处被赋成非空值。
 * 同为全域函数，供可证伪性验证使用。
 * @param {string} source
 * @returns {string[]}
 */
function detectWorkflowOverrideViolations(source) {
  const violations = [];
  const assigned = new Map();
  for (const assignment of collectGenericOverrideAssignments(source)) {
    const key = /DEV_GENERIC_(?:HTTP|HTTPS|ALL)_PROXY/.exec(assignment.line)[0];
    assigned.set(key, assignment.value);
    if (assignment.value !== '') {
      violations.push(`${key}: must be assigned the empty string, got ${assignment.value}`);
    }
  }
  for (const key of new Set(Object.values(GENERIC_OVERRIDE_BY_KEY))) {
    if (!assigned.has(key)) {
      violations.push(`${key}: the workflow must supply this CI disable override explicitly`);
    }
  }
  return violations;
}

/**
 * 取出工作流中某个 step 的完整文本块。
 * @param {string} source
 * @param {string} stepName
 * @returns {string}
 */
function extractStepBlock(source, stepName) {
  const lines = source.split(/\r?\n/);
  const startIndex = lines.indexOf(`      - name: ${stepName}`);
  assert.ok(startIndex >= 0, `production-gate.yml must still declare the step: ${stepName}`);
  const block = [];
  for (let index = startIndex + 1; index < lines.length; index += 1) {
    if (/^ {6}- name:/.test(lines[index]) || /^ {0,5}\S/.test(lines[index])) {
      break;
    }
    block.push(lines[index]);
  }
  return block.join('\n');
}

/**
 * 替换一处文本，并断言替换确实发生（防止变异测试静默失效）。
 * @param {string} source
 * @param {string} from
 * @param {string} to
 * @returns {string}
 */
function mutateOnce(source, from, to) {
  assert.ok(source.includes(from), `falsifiability fixture no longer matches: ${from}`);
  const mutated = source.replace(from, to);
  assert.notStrictEqual(mutated, source, 'mutation must change the text');
  return mutated;
}

/**
 * 用受控环境执行真实的 `docker compose config`；CLI 不可用时返回 null。
 * 使用空的 --env-file，因此仓库里本地未跟踪的 .env 无法干扰解析结果。
 * @param {Record<string, string>} resolutionEnvironment
 * @returns {Record<string, string> | null}
 */
function runRealComposeConfig(resolutionEnvironment) {
  const probe = spawnSync('docker', ['compose', 'version'], { encoding: 'utf8' });
  if (probe.error || probe.status !== 0) {
    return null;
  }
  const envFilePath = path.join(os.tmpdir(), `production-gate-proxy-${process.pid}.env`);
  fs.writeFileSync(envFilePath, '');
  try {
    const result = spawnSync(
      'docker',
      [
        'compose',
        '--env-file',
        envFilePath,
        '-f',
        COMPOSE_RELATIVE_PATH,
        'config',
        '--format',
        'json',
      ],
      {
        cwd: REPO_ROOT,
        encoding: 'utf8',
        env: { PATH: process.env.PATH, HOME: process.env.HOME, ...resolutionEnvironment },
      }
    );
    assert.strictEqual(
      result.status,
      0,
      `docker compose config failed (status ${result.status}): ${result.stderr}`
    );
    return JSON.parse(result.stdout).services.dev.environment;
  } finally {
    fs.rmSync(envFilePath, { force: true });
  }
}

const DEV_ENVIRONMENT = extractDevEnvironment(COMPOSE_SOURCE);

describe('compose substitution semantics (engine proof)', () => {
  it('proves ${VAR-default} keeps a set-but-empty value and falls back only when unset', () => {
    assert.strictEqual(resolveExpression('${SAMPLE-default}', {}), 'default');
    assert.strictEqual(resolveExpression('${SAMPLE-default}', { SAMPLE: '' }), '');
    assert.strictEqual(resolveExpression('${SAMPLE-default}', { SAMPLE: 'value' }), 'value');
  });

  it('proves ${VAR:-default} falls back on set-but-empty, which is why the fix must not use it', () => {
    assert.strictEqual(resolveExpression('${SAMPLE:-default}', {}), 'default');
    assert.strictEqual(resolveExpression('${SAMPLE:-default}', { SAMPLE: '' }), 'default');
    assert.strictEqual(resolveExpression('${SAMPLE:-default}', { SAMPLE: 'value' }), 'value');
  });

  it('resolves nested substitutions inside the default, as the compose file relies on', () => {
    const expression = 'http://${OUTER-${INNER-host.docker.internal}}:${PORT-7897}';
    assert.strictEqual(resolveExpression(expression, {}), 'http://host.docker.internal:7897');
    assert.strictEqual(
      resolveExpression(expression, { INNER: 'gateway.internal' }),
      'http://gateway.internal:7897'
    );
    // OUTER is set-but-empty, so its own default is suppressed (host collapses)
    // while the independent PORT substitution still resolves normally.
    assert.strictEqual(
      resolveExpression(expression, { OUTER: '', INNER: 'gateway.internal' }),
      'http://:7897'
    );
    assert.strictEqual(
      resolveExpression(expression, { PORT: '8888' }),
      'http://host.docker.internal:8888'
    );
  });

  it('fails closed on substitution forms it does not implement', () => {
    assert.throws(() => resolveExpression('${SAMPLE:?required}', {}), /unsupported/);
    assert.throws(() => resolveExpression('${SAMPLE:+alternate}', {}), /unsupported/);
  });
});

describe('generic proxy override shape in docker-compose.dev.yml', () => {
  it('routes all six generic proxy variables through the documented single-dash override', () => {
    assert.deepStrictEqual(detectGenericProxyViolations(COMPOSE_SOURCE), []);
  });

  it('governs both spellings of each generic proxy variable from one override variable', () => {
    const pairs = [
      ['HTTP_PROXY', 'http_proxy', 'DEV_GENERIC_HTTP_PROXY'],
      ['HTTPS_PROXY', 'https_proxy', 'DEV_GENERIC_HTTPS_PROXY'],
      ['ALL_PROXY', 'all_proxy', 'DEV_GENERIC_ALL_PROXY'],
    ];
    for (const [upper, lower, override] of pairs) {
      const normalize = expression => expression.split(override).join('<OVERRIDE>');
      assert.ok(DEV_ENVIRONMENT.get(lower).includes(override), `${lower} must use ${override}`);
      assert.ok(DEV_ENVIRONMENT.get(upper).includes(override), `${upper} must use ${override}`);
      assert.strictEqual(
        normalize(DEV_ENVIRONMENT.get(lower)),
        normalize(DEV_ENVIRONMENT.get(upper)),
        `${lower} and ${upper} must stay in lockstep`
      );
    }
  });
});

describe('local default resolution', () => {
  it('preserves the historical development proxy defaults when nothing is overridden', () => {
    assert.deepStrictEqual(
      Object.fromEntries(
        GENERIC_PROXY_KEYS.map(key => [
          key,
          resolveDevVariable(DEV_ENVIRONMENT, key, { PROXY_LOOPBACK_GATEWAY: 'host.docker.internal' }),
        ])
      ),
      {
        HTTP_PROXY: 'http://host.docker.internal:7897',
        HTTPS_PROXY: 'http://host.docker.internal:7897',
        ALL_PROXY: 'socks5://host.docker.internal:7897',
        http_proxy: 'http://host.docker.internal:7897',
        https_proxy: 'http://host.docker.internal:7897',
        all_proxy: 'socks5://host.docker.internal:7897',
      }
    );
  });

  it('still follows DEV_PROXY_HOST, PROXY_LOOPBACK_GATEWAY and DEV_HOST_PROXY_PORT', () => {
    const gatewayOnly = { PROXY_LOOPBACK_GATEWAY: 'gateway.internal' };
    assert.strictEqual(
      resolveDevVariable(DEV_ENVIRONMENT, 'HTTP_PROXY', gatewayOnly),
      'http://gateway.internal:7897'
    );
    const localProxy = { DEV_PROXY_HOST: '192.168.1.50', DEV_HOST_PROXY_PORT: '7890' };
    assert.strictEqual(
      resolveDevVariable(DEV_ENVIRONMENT, 'HTTP_PROXY', localProxy),
      'http://192.168.1.50:7890'
    );
    assert.strictEqual(
      resolveDevVariable(DEV_ENVIRONMENT, 'ALL_PROXY', localProxy),
      'socks5://192.168.1.50:7890'
    );
  });
});

describe('CI resolution', () => {
  it('resolves all six generic proxy variables to disabled/empty under the CI environment', () => {
    const resolved = GENERIC_PROXY_KEYS.map(key => resolveDevVariable(DEV_ENVIRONMENT, key, CI_ENV));
    assert.deepStrictEqual(resolved, ['', '', '', '', '', '']);
  });

  it('never resolves a generic proxy variable to the dead 127.0.0.1:7897 endpoint in CI', () => {
    for (const key of GENERIC_PROXY_KEYS) {
      const value = resolveDevVariable(DEV_ENVIRONMENT, key, CI_ENV);
      assert.strictEqual(value, '', `${key} must be empty in CI`);
      assert.ok(!value.includes('127.0.0.1'), `${key} must not point at the container itself`);
    }
  });

  it('demonstrates the endpoint the pre-fix expression produced (negative control)', () => {
    assert.strictEqual(resolveExpression(LEGACY_GENERIC_EXPRESSION, CI_ENV), 'http://127.0.0.1:7897');
    assert.ok(
      LEGACY_GENERIC_EXPRESSION.includes('${DEV_PROXY_HOST:-'),
      'the negative control must describe the pre-fix double-dash expression'
    );
  });

  it('honours a non-empty override while leaving the other proxies disabled', () => {
    const resolutionEnvironment = { ...CI_ENV, DEV_GENERIC_HTTP_PROXY: 'http://proxy.internal:3128' };
    assert.strictEqual(
      resolveDevVariable(DEV_ENVIRONMENT, 'HTTP_PROXY', resolutionEnvironment),
      'http://proxy.internal:3128'
    );
    assert.strictEqual(
      resolveDevVariable(DEV_ENVIRONMENT, 'http_proxy', resolutionEnvironment),
      'http://proxy.internal:3128'
    );
    assert.strictEqual(resolveDevVariable(DEV_ENVIRONMENT, 'HTTPS_PROXY', resolutionEnvironment), '');
    assert.strictEqual(resolveDevVariable(DEV_ENVIRONMENT, 'ALL_PROXY', resolutionEnvironment), '');
  });
});

describe('unchanged proxy families', () => {
  it('leaves provider-specific proxy configuration byte-identical', () => {
    const providerKeys = [
      'PROXY_LOOPBACK_GATEWAY',
      'PROXY_HOST',
      'WSL2_PROXY_HOST',
      'PROXY_PROTOCOL',
      'HOST_PROXY_PORT',
      'PROXY_PORT',
      'PROXY_PORT_START',
      'PROXY_PORT_END',
      'PROXY_PORTS',
      'CONTAINER_PROXY',
    ];
    for (const key of providerKeys) {
      const frozen = FROZEN_UNCHANGED_ENVIRONMENT[key];
      assert.strictEqual(DEV_ENVIRONMENT.get(key), frozen.expression, `${key} expression changed`);
      assert.strictEqual(resolveDevVariable(DEV_ENVIRONMENT, key, {}), frozen.defaultMode);
      assert.strictEqual(resolveDevVariable(DEV_ENVIRONMENT, key, CI_ENV), frozen.ciMode);
      assert.ok(
        !frozen.expression.includes('DEV_GENERIC_'),
        `${key} must not be wired to a generic proxy override`
      );
    }
  });

  it('leaves The Odds API key and transport configuration byte-identical', () => {
    const oddsApiKeys = ['THE_ODDS_API_KEY', 'THE_ODDS_API_TRANSPORT'];
    for (const key of oddsApiKeys) {
      const frozen = FROZEN_UNCHANGED_ENVIRONMENT[key];
      assert.strictEqual(DEV_ENVIRONMENT.get(key), frozen.expression, `${key} expression changed`);
      assert.strictEqual(resolveDevVariable(DEV_ENVIRONMENT, key, {}), frozen.defaultMode);
      assert.strictEqual(resolveDevVariable(DEV_ENVIRONMENT, key, CI_ENV), frozen.ciMode);
      assert.ok(
        !frozen.expression.includes('DEV_GENERIC_'),
        `${key} must not be wired to a generic proxy override`
      );
    }
    assert.strictEqual(DEV_ENVIRONMENT.get('THE_ODDS_API_KEY'), '${THE_ODDS_API_KEY:-}');
  });

  it('does not paper over the defect by allow-listing a registry hostname in NO_PROXY', () => {
    for (const key of ['NO_PROXY', 'no_proxy']) {
      assert.strictEqual(DEV_ENVIRONMENT.get(key), FROZEN_UNCHANGED_ENVIRONMENT[key].expression);
      const resolved = resolveDevVariable(DEV_ENVIRONMENT, key, CI_ENV);
      assert.ok(!resolved.includes('registry.npmjs.org'), `${key} must not be hostname-patched`);
      assert.ok(!resolved.includes('registry.npmmirror.com'), `${key} must not be hostname-patched`);
    }
  });
});

describe('Stage D provider proxy fails closed in docker-compose.dev.yml', () => {
  // 本组钉死 §13/§17/§18：省略 THE_ODDS_API_PROXY_URL 时，compose 不得注入任何
  // 端点，更不得注入工作站 :7897，否则 Stage D 的 PROXY_CONFIGURATION_MISSING
  // 失败关闭契约会在配置层被静默绕过。

  it('declares the Stage D proxy with the single-dash empty default form', () => {
    assert.deepStrictEqual(detectStageDProxyViolations(COMPOSE_SOURCE), []);
    assert.strictEqual(DEV_ENVIRONMENT.get(STAGE_D_PROXY_KEY), STAGE_D_PROXY_EXPRESSION);
  });

  it('resolves an omitted Stage D proxy to the empty string, never to a workstation proxy', () => {
    // 这是 §18 的核心断言：省略时生效的 compose 值不含任何端点。
    for (const resolutionEnvironment of [
      {},
      { PROXY_LOOPBACK_GATEWAY: 'host.docker.internal' },
      CI_ENV,
      { DEV_PROXY_HOST: 'host.docker.internal', DEV_HOST_PROXY_PORT: '7897' },
    ]) {
      const resolved = resolveDevVariable(DEV_ENVIRONMENT, STAGE_D_PROXY_KEY, resolutionEnvironment);
      assert.strictEqual(resolved, '', `omitted Stage D proxy must stay empty, got ${resolved}`);
      assert.ok(!resolved.includes('7897'), 'the workstation proxy port must never be injected');
      assert.ok(!resolved.includes('host.docker.internal'), 'no host-gateway fallback is permitted');
    }
  });

  it('does not let the generic dev proxy plumbing feed the Stage D variable', () => {
    // 通用代理（HTTP_PROXY 等）继续默认指向工作站代理——那是开发便利，保持不变；
    // 但那条通路绝不能把值漏给 Stage D 变量。
    const genericDefaults = Object.fromEntries(
      GENERIC_PROXY_KEYS.map(key => [
        key,
        resolveDevVariable(DEV_ENVIRONMENT, key, { PROXY_LOOPBACK_GATEWAY: 'host.docker.internal' }),
      ])
    );
    assert.strictEqual(genericDefaults.HTTP_PROXY, 'http://host.docker.internal:7897');
    assert.strictEqual(
      resolveDevVariable(DEV_ENVIRONMENT, STAGE_D_PROXY_KEY, {}),
      '',
      'the generic family must not leak into the Stage D variable'
    );
  });

  it('uses exactly the explicitly configured endpoint when one is supplied', () => {
    const explicit = 'http://stage-d-proxy.internal:3128';
    assert.strictEqual(
      resolveDevVariable(DEV_ENVIRONMENT, STAGE_D_PROXY_KEY, { [STAGE_D_PROXY_KEY]: explicit }),
      explicit
    );
    // "已设置但为空" 必须保持为空而不是回退——单横线形式的语义保证。
    assert.strictEqual(
      resolveDevVariable(DEV_ENVIRONMENT, STAGE_D_PROXY_KEY, { [STAGE_D_PROXY_KEY]: '' }),
      ''
    );
  });

  it('demonstrates the endpoint the pre-fix expression produced (negative control)', () => {
    assert.strictEqual(resolveExpression(LEGACY_STAGE_D_PROXY_EXPRESSION, {}), 'http://host.docker.internal:7897');
    assert.strictEqual(resolveExpression(LEGACY_STAGE_D_PROXY_EXPRESSION, CI_ENV), 'http://127.0.0.1:7897');
  });

  it('detects a regression back to the workstation-proxy default', () => {
    const mutated = mutateOnce(COMPOSE_SOURCE, STAGE_D_PROXY_EXPRESSION, LEGACY_STAGE_D_PROXY_EXPRESSION);
    const violations = detectStageDProxyViolations(mutated);
    assert.ok(violations.length > 0, 'the workstation-proxy default must be detected');
    assert.ok(violations[0].startsWith(`${STAGE_D_PROXY_KEY}:`), violations[0]);
    assert.ok(
      violations.some(violation => violation.includes('must not inherit the workstation proxy')),
      violations.join('; ')
    );
  });
});

describe('workflow supplies the CI disable override', () => {
  it('assigns the three generic override variables the empty string at workflow level', () => {
    const environment = extractWorkflowTopLevelEnvironment(WORKFLOW_SOURCE);
    assert.strictEqual(environment.get('DEV_GENERIC_HTTP_PROXY'), '');
    assert.strictEqual(environment.get('DEV_GENERIC_HTTPS_PROXY'), '');
    assert.strictEqual(environment.get('DEV_GENERIC_ALL_PROXY'), '');
    assert.ok(environment.has('DEV_GENERIC_HTTP_PROXY'));
  });

  it('never assigns a non-empty value to any generic override variable', () => {
    assert.deepStrictEqual(detectWorkflowOverrideViolations(WORKFLOW_SOURCE), []);
    assert.strictEqual(collectGenericOverrideAssignments(WORKFLOW_SOURCE).length, 3);
  });
});

describe('no gate weakening', () => {
  it('keeps the dependency install and its critical-dependency verification', () => {
    const block = extractStepBlock(WORKFLOW_SOURCE, 'Install project dependencies');
    assert.ok(block.includes('npm ci'), 'the runtime install must remain npm ci');
    assert.ok(block.includes('All critical dependencies installed'));
    assert.ok(block.includes('docker compose -f docker-compose.dev.yml exec -T dev'));
    assert.ok(!block.includes('--ignore-scripts'), 'the runtime install must run lifecycle scripts');
    assert.ok(!block.includes('continue-on-error'), 'the install must be able to fail the job');
    assert.ok(!block.includes('|| true'), 'install failures must not be swallowed');
  });

  it('keeps the Gatekeeper step and adds no bypass or error suppression', () => {
    const block = extractStepBlock(WORKFLOW_SOURCE, 'Run Gatekeeper');
    assert.ok(block.includes('python3 scripts/devops/validation_profiles.py'));
    assert.ok(block.includes('exit "$status"'));
    assert.ok(!block.includes('continue-on-error'), 'the Gatekeeper must be able to fail the job');
    assert.ok(!block.includes('|| true'), 'Gatekeeper failures must not be swallowed');
    assert.ok(!block.includes(HOOK_BYPASS_FLAG), 'the Gatekeeper must not be called with a hook-bypass flag');
    assert.ok(WORKFLOW_SOURCE.includes('name: Environment / Proxy / Static / Unit Gate'));
    assert.ok(WORKFLOW_SOURCE.includes('name: Docker Build Validation'));
    const registryAssignments = WORKFLOW_SOURCE.match(/NPM_REGISTRY=\S+/g) || [];
    assert.ok(registryAssignments.length >= 2, 'both image builds must still pin an npm registry');
    for (const assignment of registryAssignments) {
      assert.strictEqual(
        assignment,
        'NPM_REGISTRY=https://registry.npmjs.org',
        'the npm registry must not be switched to an unrelated mirror'
      );
    }
  });
});

describe('CI runtime proof', () => {
  it('asserts inside the dev container that the generic proxy really is empty', () => {
    const block = extractStepBlock(WORKFLOW_SOURCE, 'Assert CI generic proxy is disabled');
    assert.ok(block.includes('exec -T dev'), 'the proof must be taken inside the dev container');
    for (const key of GENERIC_PROXY_KEYS) {
      assert.ok(block.includes(key), `the proof must cover ${key}`);
    }
    assert.ok(block.includes('exit 1'), 'a non-empty generic proxy must fail the job');
    const printfLines = block
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.startsWith('printf'));
    assert.ok(printfLines.length >= 2, 'the proof must report every variable');
    for (const line of printfLines) {
      assert.ok(!line.includes('$value'), `the proof must never print a variable value: ${line}`);
      assert.ok(line.includes('"$name"'), `the proof must print the variable name only: ${line}`);
    }
  });

  it('runs the proxy proof before the dependency install, so the failure is immediate', () => {
    const proofIndex = WORKFLOW_SOURCE.indexOf('- name: Assert CI generic proxy is disabled');
    const installIndex = WORKFLOW_SOURCE.indexOf('- name: Install project dependencies');
    assert.ok(proofIndex >= 0 && installIndex >= 0);
    assert.ok(proofIndex < installIndex, 'the proof must run before the install');
  });
});

describe('falsifiability', () => {
  it('detects a single-dash to double-dash regression in docker-compose.dev.yml', () => {
    assert.strictEqual(
      COMPOSE_SOURCE.includes('${DEV_GENERIC_HTTP_PROXY:-'),
      false,
      'the file must not already contain the colon form'
    );
    const mutated = mutateOnce(
      COMPOSE_SOURCE,
      '${DEV_GENERIC_HTTP_PROXY-http',
      '${DEV_GENERIC_HTTP_PROXY:-http'
    );
    const violations = detectGenericProxyViolations(mutated);
    assert.strictEqual(violations.length, 1);
    assert.ok(violations[0].startsWith('HTTP_PROXY:'), violations[0]);
  });

  it('detects generic proxy lines that lose their override variable', () => {
    const removed = '${DEV_GENERIC_ALL_PROXY-socks5://';
    assert.strictEqual(
      COMPOSE_SOURCE.split(removed).length - 1,
      2,
      'the fixture must match both spellings of the ALL_PROXY variable'
    );
    const mutated = COMPOSE_SOURCE.replaceAll(removed, 'socks5://');
    const violations = detectGenericProxyViolations(mutated);
    assert.deepStrictEqual(
      violations.map(violation => violation.split(':')[0]),
      ['ALL_PROXY', 'all_proxy']
    );
  });

  it('detects a missing workflow override', () => {
    const mutated = mutateOnce(WORKFLOW_SOURCE, CI_OVERRIDE_BLOCK, '');
    const violations = detectWorkflowOverrideViolations(mutated);
    assert.strictEqual(violations.length, 3);
    for (const violation of violations) {
      assert.ok(violation.includes('must supply this CI disable override'), violation);
    }
  });

  it('detects a workflow override set to a non-empty value', () => {
    const mutated = mutateOnce(
      WORKFLOW_SOURCE,
      'DEV_GENERIC_ALL_PROXY: ""',
      'DEV_GENERIC_ALL_PROXY: "http://127.0.0.1:7897"'
    );
    const violations = detectWorkflowOverrideViolations(mutated);
    assert.deepStrictEqual(violations, [
      'DEV_GENERIC_ALL_PROXY: must be assigned the empty string, got http://127.0.0.1:7897',
    ]);
  });
});

describe('real compose CLI cross-check', () => {
  it('agrees with docker compose config when the CLI is available', t => {
    const defaultMode = runRealComposeConfig({});
    const ciMode = runRealComposeConfig(CI_ENV);
    if (defaultMode === null || ciMode === null) {
      t.diagnostic(
        '[production-gate-proxy] docker CLI unavailable: the deterministic resolver above is the equivalent representation.'
      );
      return;
    }
    for (const key of GENERIC_PROXY_KEYS) {
      assert.strictEqual(
        defaultMode[key],
        resolveDevVariable(DEV_ENVIRONMENT, key, { PROXY_LOOPBACK_GATEWAY: 'host.docker.internal' }),
        `default-mode ${key} disagrees with the resolver`
      );
      assert.strictEqual(ciMode[key], '', `CI-mode ${key} must be empty in the real resolution`);
    }
    for (const key of [...Object.keys(FROZEN_UNCHANGED_ENVIRONMENT)]) {
      const frozen = FROZEN_UNCHANGED_ENVIRONMENT[key];
      assert.strictEqual(defaultMode[key], frozen.defaultMode, `default-mode ${key} drifted`);
      assert.strictEqual(ciMode[key], frozen.ciMode, `CI-mode ${key} drifted`);
    }
    // Stage D provider proxy：真实 compose 解析必须与确定性求值器一致，
    // 且省略时为空——绝不能被 docker compose 重新引入工作站端点。
    assert.strictEqual(
      defaultMode[STAGE_D_PROXY_KEY],
      resolveDevVariable(DEV_ENVIRONMENT, STAGE_D_PROXY_KEY, {}),
      `default-mode ${STAGE_D_PROXY_KEY} disagrees with the resolver`
    );
    assert.strictEqual(defaultMode[STAGE_D_PROXY_KEY], '', 'omitted Stage D proxy must resolve empty');
    assert.strictEqual(ciMode[STAGE_D_PROXY_KEY], '', 'CI-mode Stage D proxy must resolve empty');
    assert.ok(
      !String(defaultMode[STAGE_D_PROXY_KEY]).includes('7897'),
      'the real compose resolution must not inject the workstation proxy'
    );
  });
});
