'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const { ReconDecryptor } = require('../../src/infrastructure/recon/ReconDecryptor');

const fixturesDir = path.resolve(__dirname, '../fixtures/recon_decryptor');

describe('ReconDecryptor', () => {
  it('样本验证失败时不应接受 app bundle 的未验证候选函数', async () => {
    let evaluateCalls = 0;

    const decryptor = new ReconDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const page = {
      async evaluate(_fn, payload) {
        evaluateCalls++;
        if (evaluateCalls === 1) {
          return 'https://www.oddsportal.com/build/assets/app-test.js';
        }

        if (evaluateCalls === 2) {
          return '';
        }

        assert.strictEqual(payload.allowBestEffort, false);

        return {
          found: false,
          validated: false
        };
      }
    };

    const result = await decryptor._extractFromAppScript(page, 'encrypted-sample');

    assert.strictEqual(result, null);
    assert.strictEqual(decryptor.getAlgorithmVersion(), null);
    assert.strictEqual(evaluateCalls, 3);
  });

  it('启用 best-effort 模式时，应允许回退到 ai 导出函数', async () => {
    let evaluateCalls = 0;

    const decryptor = new ReconDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      allowBestEffortCandidate: true
    });

    const page = {
      async evaluate(_fn, payload) {
        evaluateCalls++;
        if (evaluateCalls === 1) {
          return 'https://www.oddsportal.com/build/assets/app-test.js';
        }

        if (payload?.url && payload?.sample) {
          return {
            found: true,
            name: 'ai',
            type: 'named_export',
            validated: false,
            bestEffort: true
          };
        }

        return '{"d":{"rows":[]}}';
      }
    };

    const result = await decryptor._extractFromAppScript(page, 'encrypted-sample');

    assert.ok(result);
    assert.strictEqual(decryptor.getAlgorithmVersion(), 'app_ai');
    assert.strictEqual(result.__bestEffort, true);
    assert.strictEqual(result.__validated, false);
  });

  it('样本本身是伪 404 payload 时，不应启用 best-effort 回退', async () => {
    let evaluateCalls = 0;
    const invalidPayload = fs.readFileSync(path.join(fixturesDir, 'payload_invalid_404.txt'), 'utf8');

    const decryptor = new ReconDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      allowBestEffortCandidate: true
    });

    const page = {
      async evaluate(_fn, payload) {
        evaluateCalls++;
        if (evaluateCalls === 1) {
          return 'https://www.oddsportal.com/build/assets/app-test.js';
        }

        if (evaluateCalls === 2) {
          assert.strictEqual(payload.allowBestEffort, false);
          assert.ok(Array.isArray(payload.candidateNames));
          assert.ok(payload.candidateNames.includes('ai'));
          return {
            found: false,
            validated: false
          };
        }

        return '';
      }
    };

    const result = await decryptor._extractFromAppScript(page, invalidPayload);

    assert.strictEqual(result, null);
    assert.strictEqual(decryptor.getAlgorithmVersion(), null);
  });

  it('malformed payload 应在调用解密函数前 fail-fast', async () => {
    let decryptCalls = 0;
    const decryptor = new ReconDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    decryptor.decryptFn = async () => {
      decryptCalls++;
      return '{}';
    };
    decryptor.algorithmVersion = 'app_ai';

    await assert.rejects(
      decryptor.decrypt('URL:/ajax-sport-country-tournament-archive_/1//X/2025-2026/1/ Status: 404'),
      (error) => {
        assert.strictEqual(error.code, 'INVALID_ENCRYPTED_PAYLOAD');
        return true;
      }
    );

    assert.strictEqual(decryptCalls, 0);
  });

  it('应优先从 bundle 函数体特征中识别 ai 解密导出', () => {
    const bundleExcerpt = fs.readFileSync(path.join(fixturesDir, 'oddsportal_bundle_excerpt.js'), 'utf8');
    const decryptor = new ReconDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const candidates = decryptor._extractFromBundle(bundleExcerpt);

    assert.ok(Array.isArray(candidates));
    assert.strictEqual(candidates[0], 'ai');
  });
});
