'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const { ReconHealthServer } = require('../../src/infrastructure/recon/ReconHealthServer');

test('ReconHealthServer.registerDatabaseCheck 在查询异常时也必须释放 client，避免池耗尽', async () => {
  let activeClients = 0;
  let releaseCalls = 0;

  const healthServer = new ReconHealthServer({
    logger: { info() {}, warn() {}, error() {}, debug() {} }
  });

  const repository = {
    dbPool: {
      async connect() {
        if (activeClients >= 2) {
          throw new Error('pool_exhausted');
        }

        activeClients++;

        return {
          async query() {
            throw new Error('db_query_failed');
          },
          release() {
            activeClients--;
            releaseCalls++;
          }
        };
      }
    }
  };

  healthServer.registerDatabaseCheck(repository);
  const databaseCheck = healthServer.checks.get('database');

  const results = [];
  for (let index = 0; index < 5; index++) {
    results.push(await databaseCheck());
  }

  assert.equal(activeClients, 0);
  assert.equal(releaseCalls, 5);
  assert.ok(results.every((result) => result.ready === false));
  assert.ok(results.every((result) => result.error === 'db_query_failed'));
});
