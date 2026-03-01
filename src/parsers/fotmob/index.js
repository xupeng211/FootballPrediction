/**
 * FotMob 解析器模块入口
 * @module parsers/fotmob
 */

'use strict';

const CloudflareDetector = require('./CloudflareDetector');
const NextDataParser = require('./NextDataParser');
const XGExtractor = require('./XGExtractor');
const { ApiSniffer } = require('./ApiSniffer');
const { ResponseInterceptor, interceptMatchDetails, TARGET_PATTERNS, HTML_PATTERNS } = require('./ResponseInterceptor');

module.exports = {
    // Cloudflare 检测
    ...CloudflareDetector,

    // NextData 解析
    ...NextDataParser,

    // xG 提取
    ...XGExtractor,

    // V175: API 流量嗅探
    ApiSniffer,

    // V175: 动态响应拦截
    ResponseInterceptor,
    interceptMatchDetails,
    TARGET_PATTERNS,
    HTML_PATTERNS
};
