/**
 * WorkerMessenger 单元测试
 * @module tests/core/ipc/WorkerMessenger.test
 */

'use strict';

const assert = require('assert');
const { WorkerMessenger, MessageTypes, createMessage } = require('../../../src/core/ipc');

// ============================================================================
// Mock 环境
// ============================================================================

let originalProcessSend;
let sentMessages = [];

function mockProcessSend() {
    sentMessages = [];
    originalProcessSend = process.send;
    process.send = (msg) => {
        sentMessages.push(msg);
        return true;
    };
}

function restoreProcessSend() {
    process.send = originalProcessSend;
}

function clearProcessSend() {
    process.send = undefined;
}

// ============================================================================
// 测试用例
// ============================================================================

async function testMessageTypes() {
    console.log('测试: MessageTypes 常量定义');

    assert.strictEqual(MessageTypes.READY, 'READY');
    assert.strictEqual(MessageTypes.TASK_START, 'TASK_START');
    assert.strictEqual(MessageTypes.TASK_SUCCESS, 'TASK_SUCCESS');
    assert.strictEqual(MessageTypes.TASK_FAILED, 'TASK_FAILED');
    assert.strictEqual(MessageTypes.TASK_RETRY, 'TASK_RETRY');
    assert.strictEqual(MessageTypes.TASK, 'TASK');
    assert.strictEqual(MessageTypes.SHUTDOWN, 'SHUTDOWN');

    console.log('✅ MessageTypes 测试通过');
}

async function testCreateMessage() {
    console.log('测试: createMessage 函数');

    const msg = createMessage('TEST', { foo: 'bar' });

    assert.strictEqual(msg.type, 'TEST');
    assert.strictEqual(msg.foo, 'bar');
    assert.ok(msg.timestamp > 0);

    console.log('✅ createMessage 测试通过');
}

async function testWorkerMessengerConstructor() {
    console.log('测试: WorkerMessenger 构造函数');

    const messenger = new WorkerMessenger(1, {
        maxRetries: 5,
        retryDelayBase: 50,
        silent: true
    });

    assert.strictEqual(messenger.workerId, 1);
    assert.strictEqual(messenger.maxRetries, 5);
    assert.strictEqual(messenger.retryDelayBase, 50);
    assert.strictEqual(messenger.silent, true);

    console.log('✅ WorkerMessenger 构造函数测试通过');
}

async function testSafeSendSuccess() {
    console.log('测试: safeSend 成功场景');

    mockProcessSend();
    const messenger = new WorkerMessenger(1, { silent: true });

    const result = messenger.safeSend({ type: 'TEST', data: 'hello' });

    assert.strictEqual(result, true);
    assert.strictEqual(sentMessages.length, 1);
    assert.strictEqual(sentMessages[0].type, 'TEST');

    restoreProcessSend();
    console.log('✅ safeSend 成功场景测试通过');
}

async function testSafeSendNoProcessSend() {
    console.log('测试: safeSend 无 process.send 场景');

    clearProcessSend();
    const messenger = new WorkerMessenger(1, { silent: true });

    const result = messenger.safeSend({ type: 'TEST' });

    assert.strictEqual(result, false);

    console.log('✅ safeSend 无 process.send 场景测试通过');
}

async function testNotifyMethods() {
    console.log('测试: notify 系列方法');

    mockProcessSend();
    const messenger = new WorkerMessenger(1, { silent: true });

    // 测试 notifyReady
    messenger.notifyReady();
    assert.strictEqual(sentMessages.pop().type, 'READY');

    // 测试 notifyTaskStart
    messenger.notifyTaskStart('match-123');
    const startMsg = sentMessages.pop();
    assert.strictEqual(startMsg.type, 'TASK_START');
    assert.strictEqual(startMsg.matchId, 'match-123');

    // 测试 notifyTaskSuccess
    messenger.notifyTaskSuccess('match-123', { responseTime: 1000, rawSize: 5000 });
    const successMsg = sentMessages.pop();
    assert.strictEqual(successMsg.type, 'TASK_SUCCESS');
    assert.strictEqual(successMsg.matchId, 'match-123');
    assert.strictEqual(successMsg.responseTime, 1000);

    // 测试 notifyTaskFailed
    messenger.notifyTaskFailed('match-456', 'SOME_ERROR');
    const failMsg = sentMessages.pop();
    assert.strictEqual(failMsg.type, 'TASK_FAILED');
    assert.strictEqual(failMsg.matchId, 'match-456');
    assert.strictEqual(failMsg.error, 'SOME_ERROR');

    restoreProcessSend();
    console.log('✅ notify 系列方法测试通过');
}

async function testIsAvailable() {
    console.log('测试: isAvailable 方法');

    clearProcessSend();
    const messenger = new WorkerMessenger(1, { silent: true });

    assert.strictEqual(messenger.isAvailable(), false);

    mockProcessSend();
    assert.strictEqual(messenger.isAvailable(), true);

    restoreProcessSend();
    console.log('✅ isAvailable 测试通过');
}

// ============================================================================
// 运行测试
// ============================================================================

async function runTests() {
    console.log('\n========================================');
    console.log('WorkerMessenger 单元测试');
    console.log('========================================\n');

    try {
        await testMessageTypes();
        await testCreateMessage();
        await testWorkerMessengerConstructor();
        await testSafeSendSuccess();
        await testSafeSendNoProcessSend();
        await testNotifyMethods();
        await testIsAvailable();

        console.log('\n========================================');
        console.log('✅ 所有 WorkerMessenger 测试通过');
        console.log('========================================\n');

    } catch (error) {
        console.error('\n❌ 测试失败:', error.message);
        console.error(error.stack);
        process.exit(1);
    }
}

// 入口
runTests();
