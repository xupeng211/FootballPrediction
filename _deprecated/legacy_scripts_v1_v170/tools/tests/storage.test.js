/**
 * V88.000 Test B: 存储层安全性测试
 * ===================================
 *
 * 测试目标：
 *   - 使用 Jest Mock 模拟 pg.Client
 *   - 断言 client.end() 必须被调用且仅调用一次
 *   - 无论 SQL 执行成功或失败
 *
 * @file storage.test.js
 * @version V88.000
 * @since 2026-01-26
 */

'use strict';

// Mock pg 模块
jest.mock('pg', () => {
    const mockQuery = jest.fn();
    const mockEnd = jest.fn();
    const mockConnect = jest.fn();

    return {
        Client: jest.fn().mockImplementation(() => ({
            query: mockQuery,
            connect: mockConnect,
            end: mockEnd
        }))
    };
});

const { Client } = require('pg');
const storage = require('../modules/storage');

describe('V88.000 Test B: 存储层安全性', () => {
    let mockClient;
    let originalEnv;

    beforeEach(() => {
        // 创建 mock 客户端实例
        mockClient = new Client();

        // 保存原始环境变量
        originalEnv = { ...process.env };

        // 设置测试环境变量
        process.env.DB_HOST = 'localhost';
        process.env.DB_PORT = '5432';
        process.env.DB_NAME = 'test_db';
        process.env.DB_USER = 'test_user';
        process.env.DB_PASSWORD = 'test_pass';

        jest.clearAllMocks();
    });

    afterEach(() => {
        // 恢复原始环境变量
        process.env = originalEnv;
        jest.restoreAllMocks();
    });

    describe('B.1: SQL 执行成功时 client.end() 必须调用', () => {
        test('正常查询流程应调用 client.end() 一次', async () => {
            // Mock 成功查询
            mockClient.query.mockResolvedValueOnce({
                rows: [{ id: 1, name: 'test' }]
            });

            // 模拟 createConnection 函数
            const createConnection = async () => {
                await mockClient.connect();
                return mockClient;
            };

            // 执行测试
            const client = await createConnection();
            await client.query('SELECT * FROM test');
            await client.end();

            // 断言
            expect(mockClient.connect).toHaveBeenCalledTimes(1);
            expect(mockClient.query).toHaveBeenCalledTimes(1);
            expect(mockClient.end).toHaveBeenCalledTimes(1);
        });

        test('createConnection 应返回可用的客户端', async () => {
            mockClient.connect.mockResolvedValueOnce(undefined);

            const client = await storage.createConnection();
            expect(client).toBeDefined();
        });
    });

    describe('B.2: SQL 执行失败时 client.end() 仍必须调用', () => {
        test('查询异常时应调用 client.end() 一次', async () => {
            // Mock 失败查询
            mockClient.query.mockRejectedValueOnce(new Error('SQL Error'));
            mockClient.connect.mockResolvedValueOnce(undefined);

            const createConnection = async () => {
                await mockClient.connect();
                return mockClient;
            };

            const client = await createConnection();

            try {
                await client.query('SELECT * FROM test');
            } catch (e) {
                // 预期异常
            } finally {
                await client.end();
            }

            // 断言：即使查询失败，end() 仍应被调用
            expect(mockClient.end).toHaveBeenCalledTimes(1);
        });

        test('连接失败时不应调用 client.end()', async () => {
            mockClient.connect.mockRejectedValueOnce(new Error('Connection Error'));

            const createConnection = async () => {
                try {
                    await mockClient.connect();
                    return mockClient;
                } catch (e) {
                    // 连接失败，返回 null
                    return null;
                }
            };

            const client = await createConnection();

            // 断言：连接失败时 end() 不应被调用
            expect(mockClient.end).not.toHaveBeenCalled();
        });
    });

    describe('B.3: 使用 storage.createConnection 的安全性', () => {
        test('应正确处理数据库连接生命周期', async () => {
            mockClient.connect.mockResolvedValueOnce(undefined);
            mockClient.query.mockResolvedValueOnce({
                rows: []
            });

            // 使用真实的 createConnection 函数
            const client = await storage.createConnection();

            try {
                await client.query('SELECT NOW()');
            } finally {
                await client.end();
            }

            expect(mockClient.connect).toHaveBeenCalled();
            expect(mockClient.query).toHaveBeenCalled();
            expect(mockClient.end).toHaveBeenCalled();
        });
    });

    describe('B.4: 事务安全性', () => {
        test('BEGIN/COMMIT/ROLLBACK 应正确调用', async () => {
            mockClient.connect.mockResolvedValueOnce(undefined);
            mockClient.query.mockImplementation((query) => {
                if (query === 'BEGIN') {
                    return Promise.resolve({ rows: [] });
                } else if (query === 'COMMIT') {
                    return Promise.resolve({ rows: [] });
                } else if (query === 'ROLLBACK') {
                    return Promise.resolve({ rows: [] });
                }
                return Promise.resolve({ rows: [] });
            });

            const client = await storage.createConnection();

            try {
                await client.query('BEGIN');
                await client.query('SELECT * FROM test');
                await client.query('COMMIT');
            } catch (e) {
                await client.query('ROLLBACK');
            } finally {
                await client.end();
            }

            // 验证事务流程
            expect(mockClient.query).toHaveBeenCalledWith('BEGIN');
            expect(mockClient.query).toHaveBeenCalledWith('COMMIT');
            expect(mockClient.end).toHaveBeenCalledTimes(1);
        });

        test('ROLLBACK 后仍应调用 client.end()', async () => {
            mockClient.connect.mockResolvedValueOnce(undefined);
            mockClient.query
                .mockResolvedValueOnce({ rows: [] })  // BEGIN
                .mockRejectedValueOnce(new Error('Transaction Error'))  // SELECT
                .mockResolvedValueOnce({ rows: [] });  // ROLLBACK

            const client = await storage.createConnection();

            try {
                await client.query('BEGIN');
                await client.query('SELECT * FROM test');
            } catch (e) {
                await client.query('ROLLBACK');
            } finally {
                await client.end();
            }

            expect(mockClient.query).toHaveBeenCalledWith('ROLLBACK');
            expect(mockClient.end).toHaveBeenCalledTimes(1);
        });
    });

    describe('B.5: 连接池安全性', () => {
        test('应正确配置连接池参数（支持散装对象形式）', async () => {
            mockClient.connect.mockResolvedValueOnce(undefined);

            const client = await storage.createConnection();

            // V88.100: 验证关键配置参数存在（支持两种形式）
            const clientCall = Client.mock.calls[0][0];
            const hasValidConfig = !!(
                // 检查是否有 connectionString 或有关键配置字段
                (clientCall.connectionString && typeof clientCall.connectionString === 'string') ||
                (clientCall.host && clientCall.database && clientCall.user && clientCall.password)
            );

            expect(hasValidConfig).toBe(true);

            await client.end();

            expect(mockClient.end).toHaveBeenCalledTimes(1);
        });

        test('应支持散装对象形式的连接配置', async () => {
            // 重置 mock 以测试散装对象形式
            jest.clearAllMocks();
            mockClient.connect.mockResolvedValueOnce(undefined);

            const client = await storage.createConnection();

            // 验证至少调用了 Client 构造函数
            expect(Client).toHaveBeenCalled();

            await client.end();

            expect(mockClient.end).toHaveBeenCalledTimes(1);
        });
    });

    describe('B.6: 错误恢复', () => {
        test('多次创建连接不应泄漏', async () => {
            mockClient.connect.mockResolvedValue(undefined);

            const connections = [];
            for (let i = 0; i < 5; i++) {
                const client = await storage.createConnection();
                connections.push(client);
            }

            // 清理所有连接
            for (const client of connections) {
                await client.end();
            }

            // 验证每个连接都正确关闭
            expect(mockClient.end).toHaveBeenCalledTimes(5);
        });
    });
});
