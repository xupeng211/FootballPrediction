/**
 * 浏览器管理模块入口
 * @module core/browser
 */

'use strict';

const { BrowserManager } = require('./BrowserManager');
const { StealthInjector, getDefaultStealthScript } = require('./StealthInjector');

module.exports = {
    BrowserManager,
    StealthInjector,
    getDefaultStealthScript
};
