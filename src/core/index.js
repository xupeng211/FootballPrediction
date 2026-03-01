/**
 * 核心模块入口
 * @module core
 */

'use strict';

const ipc = require('./ipc');
const process = require('./process');
const browser = require('./browser');

module.exports = {
    ipc,
    process,
    browser
};
