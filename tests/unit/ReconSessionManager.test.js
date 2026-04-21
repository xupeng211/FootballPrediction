'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { ReconSessionManager } = require('../../src/infrastructure/recon/services/ReconSessionManager');

test('ReconSessionManager 应解析 Playwright JSON cookies', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-session-json-'));
  const sessionPath = path.join(tempDir, 'session.json');

  fs.writeFileSync(sessionPath, JSON.stringify([
    {
      domain: '.oddsportal.com',
      expirationDate: 1800000000,
      httpOnly: true,
      name: 'oddsportalcom_session',
      path: '/',
      sameSite: 'lax',
      secure: true,
      value: 'session-value'
    }
  ]), 'utf8');

  const manager = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-session-json',
    sessionPath,
    excludeNames: []
  });

  const result = manager.load();

  assert.equal(result.sourceFormat, 'json');
  assert.equal(result.cookies.length, 1);
  assert.equal(result.cookies[0].name, 'oddsportalcom_session');
  assert.equal(result.cookies[0].sameSite, 'Lax');
  assert.equal(result.cookies[0].secure, true);
});

test('ReconSessionManager 默认应排除高风险 session 票据', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-session-default-exclude-'));
  const sessionPath = path.join(tempDir, 'session.json');

  fs.writeFileSync(sessionPath, JSON.stringify([
    {
      domain: '.oddsportal.com',
      name: 'oddsportalcom_session',
      path: '/',
      sameSite: 'lax',
      secure: true,
      value: 'blocked-session'
    },
    {
      domain: '.oddsportal.com',
      name: 'op_user_hash',
      path: '/',
      sameSite: 'lax',
      secure: true,
      value: 'preferred-hash'
    }
  ]), 'utf8');

  const manager = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-session-default-exclude',
    sessionPath
  });

  const result = manager.load();

  assert.equal(result.cookies.length, 1);
  assert.equal(result.cookies[0].name, 'op_user_hash');
  assert.deepEqual(result.excludeNames, ['oddsportalcom_session']);
});

test('ReconSessionManager 应解析标准 header 字符串', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-session-header-'));
  const sessionPath = path.join(tempDir, 'session.txt');

  fs.writeFileSync(sessionPath, [
    'User-Agent: Browser-UA/2.0',
    'Referer: https://www.oddsportal.com/football/japan/j1-league-2026/results/',
    'Cookie: foo=bar; hello=world'
  ].join('\n'), 'utf8');

  const manager = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-session-header',
    sessionPath
  });

  const result = manager.load();

  assert.equal(result.sourceFormat, 'header');
  assert.equal(result.userAgent, 'Browser-UA/2.0');
  assert.equal(result.cookies.length, 2);
  assert.equal(result.cookies[0].domain, '.www.oddsportal.com');
  assert.equal(result.extraHTTPHeaders['user-agent'], 'Browser-UA/2.0');
});

test('ReconSessionManager 应处理 disabled、unavailable 与 empty 场景', () => {
  const warnings = [];
  const disabledManager = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-session-disabled',
    sessionPath: ''
  });
  const unavailableManager = new ReconSessionManager({
    logger: {
      info() {},
      warn(event, payload) {
        warnings.push({ event, payload });
      },
      error() {},
      debug() {}
    },
    traceId: 'trace-session-unavailable',
    sessionPath: path.join(os.tmpdir(), 'missing-session-file.json')
  });
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-session-empty-'));
  const emptyPath = path.join(tempDir, 'empty-session.txt');
  fs.writeFileSync(emptyPath, '   \n', 'utf8');
  const emptyManager = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-session-empty',
    sessionPath: emptyPath
  });

  assert.equal(disabledManager.load().sourceFormat, 'disabled');
  assert.equal(unavailableManager.load().sourceFormat, 'unavailable');
  assert.equal(emptyManager.load().sourceFormat, 'empty');
  assert.ok(warnings.some(({ event }) => event === 'recon_external_session_read_failed'));
});

test('ReconSessionManager 应映射 cwd 中同名会话文件并携带 accept-language 头', () => {
  const infoLogs = [];
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-session-mapped-'));
  const sessionBasename = 'mapped-session.txt';
  const sessionPath = path.join(tempDir, sessionBasename);
  const originalCwd = process.cwd();

  fs.writeFileSync(sessionPath, [
    'Accept-Language: zh-CN,zh;q=0.9',
    'Cookie: keep=1; invalid; skip=2',
    'Origin: https://www.oddsportal.com/'
  ].join('\n'), 'utf8');

  try {
    process.chdir(tempDir);

    const manager = new ReconSessionManager({
      logger: {
        info(event, payload) {
          infoLogs.push({ event, payload });
        },
        warn() {},
        error() {},
        debug() {}
      },
      traceId: 'trace-session-mapped',
      sessionPath: `/definitely-missing/${sessionBasename}`
    });

    const result = manager.load({
      includeNames: ['keep', 'keep', ''],
      excludeNames: ['skip', 'skip']
    });

    assert.equal(result.sourceFormat, 'header');
    assert.equal(result.cookies.length, 1);
    assert.equal(result.cookies[0].name, 'keep');
    assert.equal(result.extraHTTPHeaders['accept-language'], 'zh-CN,zh;q=0.9');
    assert.ok(infoLogs.some(({ event, payload }) =>
      event === 'recon_external_session_path_mapped' &&
      payload.resolvedPath === sessionPath
    ));
  } finally {
    process.chdir(originalCwd);
  }
});

test('ReconSessionManager 内部 helper 应覆盖筛选、规范化与域名回退分支', () => {
  const manager = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-session-helpers',
    defaultDomain: '.fallback.test',
    defaultSourceUrl: 'https://fallback.test/'
  });

  assert.deepEqual(manager._normalizeNames([' keep ', '', 'keep', 'skip ']), ['keep', 'skip']);
  assert.deepEqual(manager._normalizeNames('not-array'), []);
  assert.equal(manager._shouldKeepCookie('', [], []), false);
  assert.equal(manager._shouldKeepCookie('skip', ['keep'], []), false);
  assert.equal(manager._shouldKeepCookie('skip', [], ['skip']), false);
  assert.equal(manager._shouldKeepCookie('keep', ['keep'], ['skip']), true);

  assert.equal(manager._extractJsonUserAgent({ userAgent: ' Browser-UA/9 ' }), 'Browser-UA/9');
  assert.equal(
    manager._extractJsonUserAgent({ origins: [{ userAgent: ' Origin-UA/9 ' }] }),
    'Origin-UA/9'
  );
  assert.equal(manager._extractJsonUserAgent({ origins: [{}] }), '');
  assert.equal(manager._normalizeJsonCookie(null), null);
  assert.equal(manager._normalizeJsonCookie({ name: '   ' }), null);
  assert.deepEqual(manager._normalizeJsonCookie({
    name: 'session_id',
    value: 7,
    domain: '   ',
    path: '',
    expires: 'not-a-number',
    sameSite: 'no_restriction',
    httpOnly: true,
    secure: true
  }), {
    name: 'session_id',
    value: '',
    domain: '.fallback.test',
    path: '/',
    expires: -1,
    httpOnly: true,
    secure: true,
    sameSite: 'None'
  });
  assert.equal(manager._normalizeSameSite('strict'), 'Strict');
  assert.equal(manager._normalizeSameSite('weird'), 'Lax');
  assert.equal(manager._extractDomainFromUrl('https://sub.example.com/path'), '.sub.example.com');
  assert.equal(manager._extractDomainFromUrl('::bad-url::'), '');
});

test('ReconSessionManager 应解析 JSON 包装 payload 并在 header 无效时回退默认域名', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-session-json-wrapper-'));
  const sessionPath = path.join(tempDir, 'session.json');
  fs.writeFileSync(sessionPath, JSON.stringify({
    cookies: [
      {
        name: 'keep',
        value: '1',
        sameSite: 'strict'
      },
      {
        name: 'drop',
        value: '2',
        sameSite: 'lax'
      }
    ],
    origins: [{ userAgent: ' Browser-UA/3 ' }]
  }), 'utf8');

  const manager = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-session-json-wrapper',
    sessionPath,
    defaultDomain: '.fallback.test'
  });

  const jsonResult = manager.load({
    includeNames: ['keep', 'drop', 'keep'],
    excludeNames: ['drop']
  });
  const headerResult = manager._parseHeaderPayload([
    'BrokenLineWithoutSeparator',
    'Cookie: token=1; invalid-entry; blocked=2',
    'Origin: ::bad-url::'
  ].join('\n'), {
    includeNames: ['token', 'blocked'],
    excludeNames: ['blocked']
  });

  assert.equal(jsonResult.sourceFormat, 'json');
  assert.equal(jsonResult.cookies.length, 1);
  assert.equal(jsonResult.cookies[0].name, 'keep');
  assert.equal(jsonResult.cookies[0].sameSite, 'Strict');
  assert.equal(jsonResult.userAgent, 'Browser-UA/3');
  assert.equal(jsonResult.extraHTTPHeaders['user-agent'], 'Browser-UA/3');
  assert.equal(headerResult.cookies.length, 1);
  assert.equal(headerResult.cookies[0].name, 'token');
  assert.equal(headerResult.cookies[0].domain, '.fallback.test');
  assert.deepEqual(headerResult.extraHTTPHeaders, {});
});

test('ReconSessionManager 应合并运行期快照并优先使用最新 cookie/header', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-session-runtime-merge-'));
  const sessionPath = path.join(tempDir, 'session.json');
  fs.writeFileSync(sessionPath, JSON.stringify({
    cookies: [
      {
        name: 'keep',
        value: 'external',
        domain: '.oddsportal.com',
        path: '/'
      },
      {
        name: 'external_only',
        value: '1',
        domain: '.oddsportal.com',
        path: '/'
      }
    ],
    userAgent: 'External-UA/1.0'
  }), 'utf8');

  const manager = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-runtime-merge',
    sessionPath
  });

  manager.setRuntimeSnapshot({
    cookies: [
      {
        name: 'keep',
        value: 'runtime',
        domain: '.oddsportal.com',
        path: '/'
      },
      {
        name: 'runtime_only',
        value: '2',
        domain: '.oddsportal.com',
        path: '/'
      }
    ],
    userAgent: 'Runtime-UA/2.0',
    extraHTTPHeaders: {
      'accept-language': 'en-US,en;q=0.9'
    }
  });

  const result = manager.load();
  const keepCookie = result.cookies.find((cookie) => cookie.name === 'keep');

  assert.equal(result.sourceFormat, 'json+runtime');
  assert.equal(result.userAgent, 'Runtime-UA/2.0');
  assert.equal(result.extraHTTPHeaders['accept-language'], 'en-US,en;q=0.9');
  assert.equal(keepCookie.value, 'runtime');
  assert.ok(result.cookies.some((cookie) => cookie.name === 'external_only'));
  assert.ok(result.cookies.some((cookie) => cookie.name === 'runtime_only'));
});

test('ReconSessionManager 应把 preflight 快照写入 GOLDEN_SNAPSHOT 并供 worker 继承', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-session-buffer-pool-'));
  const bufferPoolPath = path.join(tempDir, 'session-buffer.json');
  const goldenCookie = {
    name: 'op_user_hash',
    value: 'golden-cookie',
    domain: '.oddsportal.com',
    path: '/',
    secure: true,
    sameSite: 'Lax'
  };

  const preflightManager = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-preflight',
    sessionPath: '',
    bufferPoolPath,
    bufferPoolRole: 'preflight',
    proxyPort: 7901
  });
  const writeResult = preflightManager.setRuntimeSnapshot({
    cookies: [goldenCookie],
    userAgent: 'Golden-UA/1.0',
    extraHTTPHeaders: {
      'accept-language': 'en-US,en;q=0.9'
    }
  });

  const workerManager = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-worker',
    sessionPath: '',
    bufferPoolPath,
    proxyPort: 7911
  });
  const result = workerManager.load();
  const bufferState = workerManager.inspectBufferPool();

  assert.equal(writeResult.snapshotKind, 'GOLDEN_SNAPSHOT');
  assert.equal(bufferState.hasGoldenSnapshot, true);
  assert.equal(bufferState.needsRefresh, false);
  assert.match(result.sourceFormat, /session_buffer_golden/);
  assert.equal(result.cookies.length, 1);
  assert.equal(result.cookies[0].value, 'golden-cookie');
  assert.equal(result.userAgent, 'Golden-UA/1.0');
  assert.equal(result.extraHTTPHeaders['accept-language'], 'en-US,en;q=0.9');
});

test('ReconSessionManager ContextTTL 过期时应触发单点 refresh lease，而不是全员重置', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-session-buffer-ttl-'));
  const bufferPoolPath = path.join(tempDir, 'session-buffer.json');
  const manager = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-buffer-ttl',
    sessionPath: '',
    bufferPoolPath,
    bufferPoolRole: 'preflight',
    bufferPoolTtlMs: 1000
  });

  manager.setRuntimeSnapshot({
    cookies: [{
      name: 'seed',
      value: '1',
      domain: '.oddsportal.com',
      path: '/'
    }],
    userAgent: 'Golden-UA/TTL'
  });

  const stored = JSON.parse(fs.readFileSync(bufferPoolPath, 'utf8'));
  stored.goldenSnapshot.updatedAt = new Date(Date.now() - 2000).toISOString();
  fs.writeFileSync(bufferPoolPath, JSON.stringify(stored, null, 2), 'utf8');

  const workerA = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-worker-a',
    sessionPath: '',
    bufferPoolPath,
    bufferPoolTtlMs: 1000
  });
  const workerB = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-worker-b',
    sessionPath: '',
    bufferPoolPath,
    bufferPoolTtlMs: 1000
  });

  assert.equal(workerA.shouldRefreshGoldenSnapshot(), true);
  const leaseA = workerA.acquireGoldenRefreshLease();
  const leaseB = workerB.acquireGoldenRefreshLease();

  assert.equal(leaseA.acquired, true);
  assert.equal(leaseB.acquired, false);
  assert.equal(leaseB.reason, 'busy');
  assert.equal(workerA.releaseGoldenRefreshLease(leaseA.lease), true);
});

test('ReconSessionManager 应为同一代理端口稳定持久化 JA3 节点身份', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-session-ja3-'));
  const bufferPoolPath = path.join(tempDir, 'session-buffer.json');
  const managerA = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-ja3-a',
    sessionPath: '',
    bufferPoolPath,
    proxyPort: 7911
  });
  const managerB = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-ja3-b',
    sessionPath: '',
    bufferPoolPath,
    proxyPort: 7911
  });

  const identityA = managerA.resolveProtocolIdentity({
    proxyPort: 7911,
    ciphersCount: 3,
    sigalgsCount: 2
  });
  const identityB = managerB.resolveProtocolIdentity({
    proxyPort: 7911,
    ciphersCount: 3,
    sigalgsCount: 2
  });

  assert.equal(identityA.lineageKey, 'proxy:7911');
  assert.equal(identityA.cipherIdx, 0);
  assert.equal(identityA.sigalgIdx, 0);
  assert.equal(identityA.ja3ProfileId, identityB.ja3ProfileId);
  assert.equal(identityB.source, 'session_buffer_pool');
});

test('ReconSessionManager 应覆盖 worker lineage 持久化、header 规范化与空 runtime 快照', () => {
  const infoLogs = [];
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-session-lineage-'));
  const bufferPoolPath = path.join(tempDir, 'session-buffer.json');
  const manager = new ReconSessionManager({
    logger: {
      info(event, payload) {
        infoLogs.push({ event, payload });
      },
      warn() {},
      error() {},
      debug() {}
    },
    traceId: 'trace-lineage-worker',
    sessionPath: '',
    bufferPoolPath,
    proxyPort: 7905
  });

  assert.deepStrictEqual(manager.setRuntimeSnapshot({}), {
    applied: false,
    cookies: 0,
    sourceFormat: 'runtime_empty'
  });

  const writeResult = manager.setRuntimeSnapshot({
    cookies: [{
      name: 'keep',
      value: '1',
      domain: '.oddsportal.com',
      path: '/'
    }],
    userAgent: 'Worker-UA/1.0',
    extraHTTPHeaders: {
      'X-Test': ' yes ',
      empty: '   ',
      numeric: 7
    }
  }, {
    snapshotKind: 'lineage_snapshot'
  });

  const pool = JSON.parse(fs.readFileSync(bufferPoolPath, 'utf8'));
  assert.equal(writeResult.snapshotKind, 'LINEAGE_SNAPSHOT');
  assert.equal(writeResult.lineageKey, 'proxy:7905');
  assert.ok(pool.lineages['proxy:7905']);
  assert.ok(pool.nodeIdentities['proxy:7905']);
  assert.equal(pool.lineages['proxy:7905'].kind, 'LINEAGE_SNAPSHOT');
  assert.equal(pool.lineages['proxy:7905'].snapshot.extraHTTPHeaders['x-test'], 'yes');
  assert.equal(pool.lineages['proxy:7905'].snapshot.extraHTTPHeaders.numeric, undefined);

  const loaded = manager.load();
  assert.match(loaded.sourceFormat, /session_buffer_lineage\+runtime/);
  assert.equal(loaded.userAgent, 'Worker-UA/1.0');
  assert.equal(loaded.extraHTTPHeaders['x-test'], 'yes');
  assert.equal(loaded.extraHTTPHeaders['user-agent'], 'Worker-UA/1.0');
  assert.equal(loaded.cookies.length, 1);
  assert.ok(infoLogs.some((entry) => entry.event === 'recon_runtime_session_snapshot_updated'));

  manager.clearRuntimeSnapshot();
  assert.equal(manager.runtimeSnapshot, null);
});

test('ReconSessionManager 应在禁止 stale buffer 时跳过过期 golden 并优先 fresh lineage', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-session-stale-buffer-'));
  const bufferPoolPath = path.join(tempDir, 'session-buffer.json');
  const referenceTime = Date.now();
  const freshIso = new Date(referenceTime).toISOString();
  const staleIso = new Date(referenceTime - 2000).toISOString();

  fs.writeFileSync(bufferPoolPath, JSON.stringify({
    version: 1,
    ttlMs: 1000,
    updatedAt: freshIso,
    goldenSnapshot: {
      kind: 'GOLDEN_SNAPSHOT',
      traceId: 'trace-golden',
      proxyPort: null,
      lineageKey: 'proxy:direct',
      updatedAt: staleIso,
      snapshot: {
        cookies: [{
          name: 'gold',
          value: '1',
          domain: '.oddsportal.com',
          path: '/'
        }],
        userAgent: 'Golden-UA/1.0',
        extraHTTPHeaders: {}
      }
    },
    lineages: {
      'proxy:7906': {
        kind: 'LINEAGE_SNAPSHOT',
        traceId: 'trace-lineage',
        proxyPort: 7906,
        lineageKey: 'proxy:7906',
        updatedAt: freshIso,
        snapshot: {
          cookies: [{
            name: 'lineage',
            value: '2',
            domain: '.oddsportal.com',
            path: '/'
          }],
          userAgent: 'Lineage-UA/1.0',
          extraHTTPHeaders: {
            'x-lineage': '1'
          }
        }
      }
    },
    nodeIdentities: {}
  }, null, 2), 'utf8');

  const manager = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-stale-buffer',
    sessionPath: '',
    bufferPoolPath,
    bufferPoolTtlMs: 1000,
    proxyPort: 7906
  });

  const inspect = manager.inspectBufferPool({ referenceTime });
  assert.equal(inspect.hasGoldenSnapshot, true);
  assert.equal(inspect.hasLineageSnapshot, true);
  assert.equal(inspect.isGoldenStale, true);
  assert.equal(inspect.isLineageStale, false);
  assert.equal(inspect.needsRefresh, true);

  const freshOnly = manager.load({ allowStaleBuffer: false });
  assert.match(freshOnly.sourceFormat, /session_buffer_lineage/);
  assert.equal(freshOnly.userAgent, 'Lineage-UA/1.0');
  assert.ok(freshOnly.cookies.some((cookie) => cookie.name === 'lineage'));
  assert.ok(!freshOnly.cookies.some((cookie) => cookie.name === 'gold'));

  const withStale = manager.load({ allowStaleBuffer: true });
  assert.ok(withStale.cookies.some((cookie) => cookie.name === 'gold'));
  assert.ok(withStale.cookies.some((cookie) => cookie.name === 'lineage'));
});

test('ReconSessionManager 应覆盖 refresh lease 校验、损坏 buffer 读取与 derived identity', () => {
  const warnings = [];
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-session-lock-'));
  const bufferPoolPath = path.join(tempDir, 'session-buffer.json');
  const manager = new ReconSessionManager({
    logger: {
      info() {},
      warn(event, payload) {
        warnings.push({ event, payload });
      },
      error() {},
      debug() {}
    },
    traceId: 'trace-session-lock',
    sessionPath: '',
    bufferPoolPath
  });

  const lease = manager.acquireGoldenRefreshLease();
  assert.equal(lease.acquired, true);
  assert.equal(manager.releaseGoldenRefreshLease({ traceId: 'trace-other' }), false);
  assert.equal(manager.releaseGoldenRefreshLease(lease.lease), true);
  assert.equal(manager.releaseGoldenRefreshLease(lease.lease), false);

  fs.writeFileSync(bufferPoolPath, '{broken-json', 'utf8');
  const inspect = manager.inspectBufferPool();
  assert.equal(inspect.enabled, true);
  assert.equal(inspect.exists, false);
  assert.equal(inspect.hasGoldenSnapshot, false);
  assert.ok(warnings.some((entry) => entry.event === 'recon_session_buffer_pool_read_failed'));
  assert.equal(manager._readJsonFile(bufferPoolPath), null);

  const derivedManager = new ReconSessionManager({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-session-derived',
    sessionPath: '',
    proxyPort: 0
  });
  const derivedIdentity = derivedManager.resolveProtocolIdentity({
    proxyPort: 0,
    ciphersCount: 'bad',
    sigalgsCount: 'bad'
  });

  assert.equal(derivedIdentity.source, 'derived');
  assert.equal(derivedIdentity.lineageKey, 'proxy:direct');
  assert.equal(derivedIdentity.cipherIdx, 0);
  assert.equal(derivedIdentity.sigalgIdx, 0);
  assert.equal(derivedManager._resolveSnapshotKind('unknown-kind'), 'LINEAGE_SNAPSHOT');
});
