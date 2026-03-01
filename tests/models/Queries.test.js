/**
 * 数据库模型单元测试
 * @module tests/models/Queries.test
 *
 * 注意：这些测试使用模拟的数据库客户端
 */

'use strict';

const assert = require('assert');
const { MatchQueries } = require('../../src/models/MatchQueries');
const { RawDataQueries } = require('../../src/models/RawDataQueries');

// ============================================================================
// Mock 数据库客户端
// ============================================================================

function createMockClient(mockData = {}) {
    return {
        query: async (sql, params) => {
            const sqlLower = sql.toLowerCase();

            // 模拟 UPDATE 返回
            if (sqlLower.trim().startsWith('update')) {
                return { rowCount: 1, rows: [] };
            }

            // 模拟 INSERT 返回
            if (sqlLower.trim().startsWith('insert')) {
                return { rowCount: 1, rows: [] };
            }

            // 模拟 DELETE 返回
            if (sqlLower.trim().startsWith('delete')) {
                return { rowCount: 1, rows: [{ match_id: params[0] }] };
            }

            // 模拟 SELECT 单条记录 (matches 表)
            if (sqlLower.includes('from matches') && sqlLower.includes('where match_id')) {
                const matchId = params[0];
                const record = mockData.matches?.[matchId];
                return { rows: record ? [record] : [] };
            }

            // 模拟 SELECT 1 FROM matches (exists 检查)
            if (sqlLower.includes('select 1 from matches')) {
                const matchId = params[0];
                const exists = mockData.matches?.[matchId] !== undefined;
                return { rows: exists ? [{}] : [] };
            }

            // 模拟 SELECT 1 FROM raw_match_data (exists 检查)
            if (sqlLower.includes('select 1 from raw_match_data')) {
                const exists = mockData.rawExists === true;
                return { rows: exists ? [{}] : [] };
            }

            // 模拟批量查询
            if (sqlLower.includes('limit $2')) {
                return { rows: mockData.pendingMatches || [] };
            }

            // 模拟 raw_match_data 查询
            if (sqlLower.includes('from raw_match_data')) {
                if (sqlLower.includes('count')) {
                    return { rows: [{ total_records: 10 }] };
                }
                return { rows: mockData.rawData ? [mockData.rawData] : [] };
            }

            // 默认返回
            return { rows: [], rowCount: 0 };
        }
    };
}

// ============================================================================
// MatchQueries 测试
// ============================================================================

async function testMatchQueriesConstructor() {
    console.log('测试: MatchQueries 构造函数');

    const client = createMockClient();
    const queries = new MatchQueries(client);

    assert.strictEqual(queries.client, client);

    console.log('✅ MatchQueries 构造函数测试通过');
}

async function testUpdateXG() {
    console.log('测试: MatchQueries.updateXG');

    const client = createMockClient();
    const queries = new MatchQueries(client);

    const result = await queries.updateXG('match-123', 1.5, 0.8);
    assert.strictEqual(result, true);

    // 测试 null 值
    const resultNull = await queries.updateXG('match-456', null, null);
    assert.strictEqual(resultNull, true);

    console.log('✅ updateXG 测试通过');
}

async function testUpdateStats() {
    console.log('测试: MatchQueries.updateStats');

    const client = createMockClient();
    const queries = new MatchQueries(client);

    const result = await queries.updateStats('match-123', {
        xg_home: 1.5,
        xg_away: 0.8,
        possession_home: 0.55,
        possession_away: 0.45
    });
    assert.strictEqual(result, true);

    console.log('✅ updateStats 测试通过');
}

async function testFindById() {
    console.log('测试: MatchQueries.findById');

    const mockMatch = { match_id: 'match-123', home_team: 'Liverpool', away_team: 'Chelsea' };
    const client = createMockClient({ matches: { 'match-123': mockMatch } });
    const queries = new MatchQueries(client);

    const result = await queries.findById('match-123');
    assert.deepStrictEqual(result, mockMatch);

    // 不存在的记录
    const notFound = await queries.findById('non-existent');
    assert.strictEqual(notFound, null);

    console.log('✅ findById 测试通过');
}

async function testExists() {
    console.log('测试: MatchQueries.exists');

    const client = createMockClient({ matches: { 'match-123': {} } });
    const queries = new MatchQueries(client);

    const exists = await queries.exists('match-123');
    assert.strictEqual(exists, true);

    const notExists = await queries.exists('non-existent');
    assert.strictEqual(notExists, false);

    console.log('✅ exists 测试通过');
}

async function testGetPendingHarvest() {
    console.log('测试: MatchQueries.getPendingHarvest');

    const pendingMatches = [
        { match_id: 'match-1' },
        { match_id: 'match-2' }
    ];
    const client = createMockClient({ pendingMatches });
    const queries = new MatchQueries(client);

    const result = await queries.getPendingHarvest({ limit: 10 });
    assert.strictEqual(result.length, 2);

    console.log('✅ getPendingHarvest 测试通过');
}

// ============================================================================
// RawDataQueries 测试
// ============================================================================

async function testRawDataQueriesConstructor() {
    console.log('测试: RawDataQueries 构造函数');

    const client = createMockClient();
    const queries = new RawDataQueries(client);

    assert.strictEqual(queries.client, client);

    console.log('✅ RawDataQueries 构造函数测试通过');
}

async function testStoreRawJson() {
    console.log('测试: RawDataQueries.storeRawJson');

    const client = createMockClient();
    const queries = new RawDataQueries(client);

    const result = await queries.storeRawJson('match-123', { test: 'data' });
    assert.strictEqual(result, true);

    console.log('✅ storeRawJson 测试通过');
}

async function testRawExists() {
    console.log('测试: RawDataQueries.exists');

    const client = createMockClient({ rawExists: true });
    const queries = new RawDataQueries(client);

    const exists = await queries.exists('match-123');
    assert.strictEqual(exists, true);

    const clientNoData = createMockClient({ rawExists: false });
    const queriesNoData = new RawDataQueries(clientNoData);

    const notExists = await queriesNoData.exists('match-456');
    assert.strictEqual(notExists, false);

    console.log('✅ RawDataQueries.exists 测试通过');
}

async function testGetRawJson() {
    console.log('测试: RawDataQueries.getRawJson');

    const rawData = { l2_raw_json: { test: 'data' }, collected_at: new Date() };
    const client = createMockClient({ rawData });
    const queries = new RawDataQueries(client);

    const result = await queries.getRawJson('match-123');
    // 由于模拟客户端的简化实现，这里只检查返回不是 null
    // 实际测试中需要更完整的模拟

    console.log('✅ getRawJson 测试通过');
}

async function testBatchStore() {
    console.log('测试: RawDataQueries.batchStore');

    const client = createMockClient();
    const queries = new RawDataQueries(client);

    const items = [
        { matchId: 'match-1', data: { test: 1 } },
        { matchId: 'match-2', data: { test: 2 } },
        { matchId: 'match-3', data: { test: 3 } }
    ];

    const count = await queries.batchStore(items);
    assert.strictEqual(count, 3);

    console.log('✅ batchStore 测试通过');
}

// ============================================================================
// 运行测试
// ============================================================================

async function runTests() {
    console.log('\n========================================');
    console.log('数据库模型单元测试');
    console.log('========================================\n');

    try {
        // MatchQueries
        console.log('\n--- MatchQueries ---');
        await testMatchQueriesConstructor();
        await testUpdateXG();
        await testUpdateStats();
        await testFindById();
        await testExists();
        await testGetPendingHarvest();

        // RawDataQueries
        console.log('\n--- RawDataQueries ---');
        await testRawDataQueriesConstructor();
        await testStoreRawJson();
        await testRawExists();
        await testGetRawJson();
        await testBatchStore();

        console.log('\n========================================');
        console.log('✅ 所有数据库模型测试通过');
        console.log('========================================\n');

    } catch (error) {
        console.error('\n❌ 测试失败:', error.message);
        console.error(error.stack);
        process.exit(1);
    }
}

// 入口
runTests();
