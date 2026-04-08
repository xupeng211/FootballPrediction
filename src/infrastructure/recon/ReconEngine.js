/**
 * ReconEngine 对外入口薄壳。
 *
 * 该模块仅负责稳定导出，复杂实现迁移到 `ReconEngineImpl.js`，
 * 便于把核心入口维持在低复杂度并接受严格门禁。
 *
 * @module infrastructure/recon/ReconEngine
 */

'use strict';

module.exports = require('./ReconEngineImpl');
