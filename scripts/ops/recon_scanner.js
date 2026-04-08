/**
 * Recon 扫描入口薄壳。
 *
 * 该文件只负责对外暴露稳定入口，具体实现已下沉到
 * `recon_scanner_impl.js`，用于隔离复杂业务逻辑与门禁规则。
 *
 * @module scripts/ops/recon_scanner
 */

'use strict';

module.exports = require('./recon_scanner_impl');
