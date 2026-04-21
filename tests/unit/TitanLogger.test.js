const { describe, it } = require('node:test');
const assert = require('node:assert');
const { TitanLogger, createTraceId } = require('../../src/infrastructure/utils/TitanLogger');

describe('TitanLogger', () => {
  it('应该创建日志实例', () => {
    const logger = new TitanLogger({ serviceName: 'test' });

    assert.strictEqual(logger.serviceName, 'test');
    assert.ok(logger.logger);
  });

  it('应该生成 traceId', () => {
    const traceId = createTraceId();

    assert.strictEqual(typeof traceId, 'string');
    assert.ok(traceId.length > 0);
  });

  it('应该设置和获取 traceId', () => {
    const logger = new TitanLogger();
    const testTraceId = 'test-trace-123';

    logger.setTraceId(testTraceId);
    assert.strictEqual(logger.getTraceId(), testTraceId);
  });

  it('应该创建子日志器', () => {
    const logger = new TitanLogger({ serviceName: 'parent' });
    const child = logger.child({ component: 'test' });

    assert.ok(child);
    assert.strictEqual(child.serviceName, 'parent');
  });

  it('应该记录不同级别的日志', () => {
    const logger = new TitanLogger({ serviceName: 'test', enableFileLogging: false });

    assert.doesNotThrow(() => {
      logger.debug('debug message');
      logger.info('info message');
      logger.warn('warn message');
      logger.error('error message');
    });
  });
});
