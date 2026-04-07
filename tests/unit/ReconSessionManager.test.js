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
