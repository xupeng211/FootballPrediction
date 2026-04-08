/**
 * Recon 匹配评估入口薄壳。
 *
 * 复杂实现迁移到 `ReconMatchEvaluatorImpl.js`，该文件仅负责
 * 稳定导出，确保核心入口满足严格门禁策略。
 *
 * @module infrastructure/recon/services/ReconMatchEvaluator
 */

'use strict';

module.exports = require('./ReconMatchEvaluatorImpl');
