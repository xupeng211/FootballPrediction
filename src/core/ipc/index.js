/**
 * IPC 模块入口
 * @module core/ipc
 */

'use strict';

const { WorkerMessenger, MessageTypes, createMessage } = require('./WorkerMessenger');
const MessageTypesConst = require('./MessageTypes');
const { MasterGate } = require('./MasterGate');

module.exports = {
    WorkerMessenger,
    MasterGate,
    MessageTypes: MessageTypesConst.MessageTypes,
    createMessage,
    // 便捷函数
    taskStartMessage: MessageTypesConst.taskStartMessage,
    taskSuccessMessage: MessageTypesConst.taskSuccessMessage,
    taskFailedMessage: MessageTypesConst.taskFailedMessage,
    taskRetryMessage: MessageTypesConst.taskRetryMessage
};
