'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { reconMatrixFlow } = require('../../src/infrastructure/recon/services/ReconMatrixFlow');

describe('ReconMatrixFlow', () => {
  it('应将 season_mirror 与 pure_protocol source 归一化为 protocol_extract', () => {
    const flow = { ...reconMatrixFlow };

    assert.strictEqual(
      flow._normalizeMappingMethod({
        method: 'season_mirror',
        candidate: { source: 'pure_protocol_archive:xbsqV0go' }
      }),
      'protocol_extract'
    );
  });

  it('应保留数据库白名单中的 mapping_method', () => {
    const flow = { ...reconMatrixFlow };

    assert.strictEqual(
      flow._normalizeMappingMethod({
        method: 'exact',
        candidate: { source: 'pure_protocol_archive:xbsqV0go' }
      }),
      'exact'
    );
  });
});
