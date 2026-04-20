'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const { ReconBookmakerUnlocker } = require('../../src/infrastructure/recon/services/ReconBookmakerUnlocker');

describe('ReconBookmakerUnlocker', () => {
  it('菜单缺失时应使用短超时快速返回 false', async () => {
    const visibilityTimeouts = [];
    let evaluateCalls = 0;
    const page = {
      getByRole() {
        return {
          first() {
            return {
              async getAttribute() {
                return null;
              },
              async isVisible(options = {}) {
                visibilityTimeouts.push(Number(options.timeout || 0));
                return false;
              }
            };
          }
        };
      },
      async evaluate() {
        evaluateCalls += 1;
        return false;
      }
    };

    const unlocker = new ReconBookmakerUnlocker({
      forceUnlockJ1: {
        enabled: true,
        menu_labels: ['BOOKMAKERS', 'Bookmakers']
      }
    });

    const opened = await unlocker.openBookmakerMenu(page);

    assert.equal(opened, false);
    assert.equal(evaluateCalls, 1);
    assert.deepEqual(visibilityTimeouts, [250, 250, 250, 250]);
  });
});
