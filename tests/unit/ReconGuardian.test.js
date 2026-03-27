'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconGuardian } = require('../../src/infrastructure/recon/ReconGuardian');

describe('ReconGuardian - Resource Hog Safety', () => {
  it('默认不应把高资源活跃进程当作僵尸清理', () => {
    const guardian = new ReconGuardian({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    assert.strictEqual(
      guardian._shouldCollectProcess({
        isZombie: false,
        isOrphan: false,
        isResourceHog: true
      }),
      false
    );
  });

  it('开启 killResourceHogs 后才应接管高资源活跃进程', () => {
    const guardian = new ReconGuardian({
      killResourceHogs: true,
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    assert.strictEqual(
      guardian._shouldCollectProcess({
        isZombie: false,
        isOrphan: false,
        isResourceHog: true
      }),
      true
    );
  });

  it('真正的僵尸或孤儿进程应始终进入清理列表', () => {
    const guardian = new ReconGuardian({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    assert.strictEqual(
      guardian._shouldCollectProcess({
        isZombie: true,
        isOrphan: false,
        isResourceHog: false
      }),
      true
    );

    assert.strictEqual(
      guardian._shouldCollectProcess({
        isZombie: false,
        isOrphan: true,
        isResourceHog: false
      }),
      true
    );
  });
});
