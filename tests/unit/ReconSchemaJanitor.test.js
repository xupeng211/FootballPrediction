'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const { ReconSchemaJanitor } = require('../../src/infrastructure/services/recon/ReconSchemaJanitor');

class RepositoryError extends Error {}

function createJanitor(overrides = {}) {
  return new ReconSchemaJanitor({
    getDbPool() {
      return {
        async query() {
          return { rows: [] };
        }
      };
    },
    async executeWithRetry(fn) {
      return fn();
    },
    mappingMigration: {
      async findDuplicateSeasonHashGroups() {
        return [{ season: '2025/2026', oddsportal_hash: 'default-hash' }];
      },
      async dedupeMappings() {
        return {
          deletedCount: 1,
          groupCount: 1,
          repairedCount: 0,
          groups: [{ season: '2025/2026', oddsportal_hash: 'default-hash' }]
        };
      },
      async repairLinkedStatusesWithoutMapping() {
        return { repairedCount: 0, matchIds: [] };
      }
    },
    RepositoryError,
    ...overrides
  });
}

describe('ReconSchemaJanitor', () => {
  it('constructor 应在 mappingMigration 缺失时抛出 object 依赖错误', () => {
    assert.throws(
      () => createJanitor({ mappingMigration: null }),
      /ReconSchemaJanitor.*mappingMigration/
    );
  });

  it('isCreateIndexDuplicateConflict 应正确识别与忽略重复索引冲突', async () => {
    const janitor = createJanitor();

    assert.equal(janitor.isCreateIndexDuplicateConflict(null), false);
    assert.equal(
      janitor.isCreateIndexDuplicateConflict({
        code: '99999',
        message: 'other error',
        detail: ''
      }),
      false
    );
    assert.equal(
      janitor.isCreateIndexDuplicateConflict({
        code: '23505',
        message: 'could not create unique index "idx_mapping_season_hash_unique"',
        detail: ''
      }),
      true
    );
    assert.equal(
      janitor.isCreateIndexDuplicateConflict({
        code: '23505',
        message: 'duplicate key',
        detail: 'Key (season, oddsportal_hash)=(2025/2026, abc) already exists.'
      }),
      true
    );

    await janitor.ensureOddsPortalMappingSchema();
  });

  it('ensureOddsPortalMappingSchema 应执行 schema、索引与 orphan repair 流程', async () => {
    const queryCalls = [];
    const janitor = createJanitor({
      getDbPool() {
        return {
          async query(sql) {
            queryCalls.push(String(sql));
            return { rows: [] };
          }
        };
      },
      async executeWithRetry(fn) {
        return fn();
      },
      mappingMigration: {
        async findDuplicateSeasonHashGroups() {
          return [{ season: '2025/2026', oddsportal_hash: 'hash-1' }];
        },
        async dedupeMappings() {
          return { deletedCount: 0, groupCount: 0, repairedCount: 0, groups: [] };
        },
        async repairLinkedStatusesWithoutMapping() {
          return { repairedCount: 0, matchIds: [] };
        }
      }
    });

    await janitor.ensureOddsPortalMappingSchema();

    assert.equal(janitor.mappingSchemaEnsured, true);
    assert.equal(janitor.mappingHashUniquenessEnsured, true);
    assert.equal(janitor.leagueDictionarySchemaEnsured, true);
    assert.equal(queryCalls.some((sql) => sql.includes('matches_oddsportal_mapping')), true);
    assert.equal(queryCalls.some((sql) => sql.includes('recon_league_dictionary')), true);
    assert.equal(queryCalls.some((sql) => sql.includes('idx_mapping_season_hash_unique')), true);
  });
});
