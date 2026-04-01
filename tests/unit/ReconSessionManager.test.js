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
