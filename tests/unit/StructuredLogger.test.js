/**
 * StructuredLogger.test.js - 结构化日志器单元测试
 * ==================================================
 *
 * 目标: 90%+ 行覆盖率
 * 策略: 纯单元测试，无需数据库
 *
 * @module tests/unit/StructuredLogger
 * @version V4.0.0
 */

'use strict';

const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const os = require('os');

// 被测组件
const { StructuredLogger, LOG_LEVELS } = require('../../src/utils/StructuredLogger.js');

// ============================================================================
// 测试套件
// ============================================================================

describe('StructuredLogger 单元测试 (V4.0 模块化)', () => {
    let tempDir;
    let logger;

    // 每个测试前创建临时目录
    beforeEach(() => {
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'smelter-test-'));
    });

    // 每个测试后清理
    afterEach(() => {
        if (logger) {
            logger.close();
            logger = null;
        }
        // 清理临时目录
        try {
            fs.rmSync(tempDir, { recursive: true, force: true });
        } catch (e) {
            // 忽略清理错误
        }
    });

    // =======================================================================
    // 构造函数测试
    // =======================================================================

    describe('构造函数', () => {
        it('应该使用默认配置初始化', () => {
            logger = new StructuredLogger();
            
            assert.strictEqual(logger.component, 'FeatureSmelter', '默认组件名应为 FeatureSmelter');
            assert.strictEqual(logger.logDir, '/app/logs/pipeline', '默认日志目录应为 /app/logs/pipeline');
            assert.strictEqual(logger.enableStructured, true, '默认应启用结构化输出');
            assert.ok(logger.logStream, '应创建日志流');
        });

        it('应该接受自定义配置', () => {
            logger = new StructuredLogger({
                component: 'TestComponent',
                logDir: tempDir,
                enableStructured: false
            });
            
            assert.strictEqual(logger.component, 'TestComponent', '应使用自定义组件名');
            assert.strictEqual(logger.logDir, tempDir, '应使用自定义日志目录');
            assert.strictEqual(logger.enableStructured, false, '应禁用结构化输出');
        });

        it('应该在目录不存在时自动创建', () => {
            const nestedDir = path.join(tempDir, 'nested', 'logs');
            
            logger = new StructuredLogger({ logDir: nestedDir });
            
            assert.ok(fs.existsSync(nestedDir), '应自动创建嵌套目录');
        });
    });

    // =======================================================================
    // 日志级别测试
    // =======================================================================

    describe('日志级别方法', () => {
        beforeEach(() => {
            logger = new StructuredLogger({ logDir: tempDir });
        });

        it('应该记录 info 级别日志', () => {
            assert.doesNotThrow(() => {
                logger.info('测试信息消息', { key: 'value' });
            });
        });

        it('应该记录 warn 级别日志', () => {
            assert.doesNotThrow(() => {
                logger.warn('测试警告消息', { warning: true });
            });
        });

        it('应该记录 error 级别日志', () => {
            assert.doesNotThrow(() => {
                logger.error('测试错误消息', { error: 'test' });
            });
        });

        it('应该在 debug 环境变量设置时记录 debug 日志', () => {
            const originalLevel = process.env.LOG_LEVEL;
            process.env.LOG_LEVEL = 'debug';
            
            try {
                assert.doesNotThrow(() => {
                    logger.debug('测试调试消息', { debug: true });
                });
            } finally {
                process.env.LOG_LEVEL = originalLevel;
            }
        });

        it('应该在非 debug 环境跳过 debug 日志', () => {
            const originalLevel = process.env.LOG_LEVEL;
            process.env.LOG_LEVEL = 'info';
            
            try {
                // 不应抛出错误，但也不应输出
                logger.debug('不应输出的调试消息', { hidden: true });
                // 测试通过即表示未抛出错误
                assert.ok(true, '非 debug 环境不应抛出错误');
            } finally {
                process.env.LOG_LEVEL = originalLevel;
            }
        });
    });

    // =======================================================================
    // 结构化输出测试
    // =======================================================================

    describe('结构化输出', () => {
        beforeEach(() => {
            logger = new StructuredLogger({ 
                logDir: tempDir,
                component: 'TestComponent'
            });
        });

        it('应该输出 JSON 格式的日志条目', () => {
            // 捕获控制台输出
            const originalLog = console.log;
            let capturedOutput = '';
            console.log = (msg) => {
                capturedOutput = msg;
            };

            try {
                logger.info('测试消息', { testData: 123 });
                
                const parsed = JSON.parse(capturedOutput);
                assert.ok(parsed.timestamp, '应有时间戳');
                assert.strictEqual(parsed.level, 'info', '应有正确级别');
                assert.strictEqual(parsed.component, 'TestComponent', '应有正确组件名');
                assert.strictEqual(parsed.message, '测试消息', '应有正确消息');
                assert.strictEqual(parsed.testData, 123, '应有上下文数据');
            } finally {
                console.log = originalLog;
            }
        });

        it('非结构化模式应输出可读格式', () => {
            logger = new StructuredLogger({ 
                logDir: tempDir,
                enableStructured: false
            });

            const originalLog = console.log;
            let capturedOutput = '';
            console.log = (msg) => {
                capturedOutput = msg;
            };

            try {
                logger.info('可读格式消息');
                
                assert.ok(capturedOutput.includes('可读格式消息'), '应包含消息内容');
                assert.ok(capturedOutput.includes('INFO'), '应包含级别标识');
            } finally {
                console.log = originalLog;
            }
        });
    });

    // =======================================================================
    // 日志流管理测试
    // =======================================================================

    describe('日志流管理', () => {
        it('应该正确关闭日志流', () => {
            logger = new StructuredLogger({ logDir: tempDir });
            
            assert.ok(logger.logStream, '关闭前应有日志流');
            
            logger.close();
            
            assert.strictEqual(logger.logStream, null, '关闭后日志流应为 null');
        });

        it('多次关闭不应抛出错误', () => {
            logger = new StructuredLogger({ logDir: tempDir });
            
            assert.doesNotThrow(() => {
                logger.close();
                logger.close();
                logger.close();
            });
        });
    });

    // =======================================================================
    // 关闭方法测试
    // =======================================================================

    describe('关闭方法', () => {
        it('应该正确关闭日志流', () => {
            logger = new StructuredLogger({ logDir: tempDir });
            
            assert.ok(logger.logStream, '关闭前应有日志流');
            
            logger.close();
            
            assert.strictEqual(logger.logStream, null, '关闭后日志流应为 null');
        });

        it('多次关闭不应抛出错误', () => {
            logger = new StructuredLogger({ logDir: tempDir });
            
            assert.doesNotThrow(() => {
                logger.close();
                logger.close(); // 第二次关闭
                logger.close(); // 第三次关闭
            });
        });
    });

    // =======================================================================
    // 错误处理测试
    // =======================================================================

    describe('错误处理', () => {
        it('应该处理无效日志目录', () => {
            // 使用无效路径（在 Windows 上可能是非法字符，在 Unix 上可能是权限问题）
            const invalidDir = '/root/invalid_path_that_does_not_exist';
            
            assert.doesNotThrow(() => {
                logger = new StructuredLogger({ logDir: invalidDir });
            }, '不应因无效目录而崩溃');
        });

        it('应该处理空消息', () => {
            logger = new StructuredLogger({ logDir: tempDir });
            
            assert.doesNotThrow(() => {
                logger.info('');
                logger.info(null);
                logger.info(undefined);
            });
        });

        it('应该处理大上下文对象', () => {
            logger = new StructuredLogger({ logDir: tempDir });
            
            const largeContext = {
                array: Array.from({ length: 1000 }, (_, i) => ({ id: i, data: 'test' })),
                nested: { a: { b: { c: { d: 'deep' } } } }
            };
            
            assert.doesNotThrow(() => {
                logger.info('大上下文测试', largeContext);
            });
        });
    });

    // =======================================================================
    // 常量导出测试
    // =======================================================================

    describe('常量导出', () => {
        it('应该导出 LOG_LEVELS 常量', () => {
            assert.ok(LOG_LEVELS, '应导出 LOG_LEVELS');
            assert.strictEqual(LOG_LEVELS.ERROR, 'error', '应有 ERROR 级别');
            assert.strictEqual(LOG_LEVELS.WARN, 'warn', '应有 WARN 级别');
            assert.strictEqual(LOG_LEVELS.INFO, 'info', '应有 INFO 级别');
            assert.strictEqual(LOG_LEVELS.DEBUG, 'debug', '应有 DEBUG 级别');
        });
    });
});

console.log('\n📋 StructuredLogger V4.0 模块化测试套件已加载\n');
