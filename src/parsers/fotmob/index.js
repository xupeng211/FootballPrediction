/**
 * FotMob 解析器模块入口
 * @module parsers/fotmob
 */

'use strict';

const NextDataParser = require('./NextDataParser');
const XGExtractor = require('./XGExtractor');
const { LeagueParser } = require('./LeagueParser');
const { TeamParser } = require('./TeamParser');
const { MatchParser } = require('./MatchParser');
const { PlayerParser } = require('./PlayerParser');
const { MatchStatsParser } = require('./MatchStatsParser');

function optionalRequire(path) {
    try {
        return require(path);
    } catch (error) {
        if (error.code !== 'MODULE_NOT_FOUND') {
            throw error;
        }
        return {};
    }
}

const CloudflareDetector = optionalRequire('./CloudflareDetector');
const { ApiSniffer } = optionalRequire('./ApiSniffer');
const {
    ResponseInterceptor,
    interceptMatchDetails,
    TARGET_PATTERNS,
    HTML_PATTERNS
} = optionalRequire('./ResponseInterceptor');

module.exports = {
    // Cloudflare 检测
    ...CloudflareDetector,

    // NextData 解析
    ...NextDataParser,

    // xG 提取
    ...XGExtractor,

    LeagueParser,
    TeamParser,
    MatchParser,
    PlayerParser,
    MatchStatsParser,

    // V175: API 流量嗅探
    ApiSniffer,

    // V175: 动态响应拦截
    ResponseInterceptor,
    interceptMatchDetails,
    TARGET_PATTERNS,
    HTML_PATTERNS
};
