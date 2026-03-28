'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconDecryptor } = require('../../src/infrastructure/recon/ReconDecryptor');

describe('ReconDecryptor', () => {
  it('样本验证失败时不应接受 app bundle 的未验证候选函数', async () => {
    let evaluateCalls = 0;

    const decryptor = new ReconDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const page = {
      async evaluate() {
        evaluateCalls++;
        if (evaluateCalls === 1) {
          return 'https://www.oddsportal.com/build/assets/app-test.js';
        }

        return {
          found: false,
          validated: false
        };
      }
    };

    const result = await decryptor._extractFromAppScript(page, 'encrypted-sample');

    assert.strictEqual(result, null);
    assert.strictEqual(decryptor.getAlgorithmVersion(), null);
    assert.strictEqual(evaluateCalls, 2);
  });
});
