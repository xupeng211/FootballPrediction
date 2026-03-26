'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { Persistence } = require('../../src/infrastructure/harvesters/components/Persistence');

function createClient(options = {}) {
  const events = [];
  const query = async (sql, params = []) => {
    const normalized = sql.trim().replace(/\s+/g, ' ');
    events.push({ sql: normalized, params });

    if (normalized.startsWith('SELECT column_name FROM information_schema.columns')) {
      return {
        rows: options.columns || [{ column_name: 'pipeline_status' }]
      };
    }

    if (normalized.startsWith('INSERT INTO raw_match_data')) {
      return { rowCount: 1, rows: [] };
    }

    if (normalized.startsWith('UPDATE matches')) {
      return { rowCount: 1, rows: [] };
    }

    if (normalized.startsWith('ALTER TABLE matches ADD COLUMN IF NOT EXISTS pipeline_status')) {
      return { rowCount: 0, rows: [] };
    }

    if (normalized.startsWith('CREATE INDEX IF NOT EXISTS idx_matches_pipeline_status')) {
      return { rowCount: 0, rows: [] };
    }

    if (normalized.startsWith('BEGIN') || normalized.startsWith('COMMIT') || normalized.startsWith('ROLLBACK')) {
      return { rowCount: 0, rows: [] };
    }

    return { rowCount: 0, rows: [] };
  };

  return {
    events,
    client: {
      query,
      release() {
        events.push({ sql: 'RELEASE', params: [] });
      }
    }
  };
}

describe('Persistence - State Sync', () => {
  it('dualSave 成功后应在同一事务中回写 pipeline_status', async () => {
    const persistence = new Persistence({ dataPath: 'data/matches' });
    persistence.saveToFile = async () => '/tmp/fake.json';

    const { client, events } = createClient();
    const pool = {
      async connect() {
        return client;
      }
    };

    const result = await persistence.dualSave(
      pool,
      '47',
      '2024/2025',
      '4506263',
      { foo: 'bar' },
      { source: 'unit-test' }
    );

    assert.strictEqual(result.dbSuccess, true);
    assert.strictEqual(result.matchId, '47_20242025_4506263');

    const statements = events.map(entry => entry.sql);
    assert.deepStrictEqual(
      statements,
      [
        'BEGIN',
        'INSERT INTO raw_match_data (match_id, raw_data, collected_at, data_version, external_id) VALUES ($1, $2, NOW(), $3, $4) ON CONFLICT (match_id) DO UPDATE SET raw_data = EXCLUDED.raw_data, collected_at = NOW(), data_version = EXCLUDED.data_version',
        'SELECT column_name FROM information_schema.columns WHERE table_name = $1 AND column_name = ANY($2) ORDER BY column_name',
        'UPDATE matches SET pipeline_status = $2, updated_at = NOW() WHERE match_id = $1',
        'COMMIT',
        'RELEASE'
      ]
    );
  });

  it('缺少 pipeline_status 时应自动补齐列后再回写状态', async () => {
    const persistence = new Persistence({ dataPath: 'data/matches' });
    persistence.saveToFile = async () => '/tmp/fake.json';

    let infoSchemaCallCount = 0;
    const events = [];
    const client = {
      async query(sql, params = []) {
        const normalized = sql.trim().replace(/\s+/g, ' ');
        events.push({ sql: normalized, params });

        if (normalized.startsWith('SELECT column_name FROM information_schema.columns')) {
          infoSchemaCallCount++;
          if (infoSchemaCallCount === 1) {
            return { rows: [] };
          }
          return { rows: [{ column_name: 'pipeline_status' }] };
        }

        return { rowCount: 1, rows: [] };
      },
      release() {
        events.push({ sql: 'RELEASE', params: [] });
      }
    };

    const pool = {
      async connect() {
        return client;
      }
    };

    await persistence.dualSave(
      pool,
      '47',
      '2024/2025',
      '4506264',
      { foo: 'bar' },
      { source: 'unit-test' }
    );

    const statements = events.map(entry => entry.sql);
    assert.ok(statements.includes('ALTER TABLE matches ADD COLUMN IF NOT EXISTS pipeline_status VARCHAR(20) DEFAULT \'pending\''));
    assert.ok(statements.includes('CREATE INDEX IF NOT EXISTS idx_matches_pipeline_status ON matches(pipeline_status)'));
    assert.ok(statements.includes('UPDATE matches SET pipeline_status = $2, updated_at = NOW() WHERE match_id = $1'));
  });

  it('事务中途失败时应回滚并释放连接', async () => {
    const persistence = new Persistence({ dataPath: 'data/matches' });
    persistence.saveToFile = async () => '/tmp/fake.json';

    const events = [];
    const client = {
      async query(sql) {
        const normalized = sql.trim().replace(/\s+/g, ' ');
        events.push(normalized);

        if (normalized.startsWith('SELECT column_name FROM information_schema.columns')) {
          return { rows: [{ column_name: 'pipeline_status' }] };
        }

        if (normalized.startsWith('UPDATE matches')) {
          throw new Error('update failed');
        }

        return { rowCount: 1, rows: [] };
      },
      release() {
        events.push('RELEASE');
      }
    };

    const pool = {
      async connect() {
        return client;
      }
    };

    await assert.rejects(
      () => persistence.dualSave(pool, '47', '2024/2025', '4506265', { foo: 'bar' }),
      /update failed/
    );

    assert.ok(events.includes('ROLLBACK'));
    assert.strictEqual(events.at(-1), 'RELEASE');
  });
});
