/**
 * TextSurgicalExtractor - V168.002 Data Extraction Module
 * ===================================================
 *
 * [Genesis.Architect] JS 文本提取器 - 从 SignalRadar.js 提取
 *
 * 从原始 JavaScript 文本中提取数据，纯文本解析不执行代码。
 *
 * @module services/extractors/TextSurgicalExtractor
 * @version V168.002
 * @since 2026-02-02
 * @author [Genesis.Architect]
 */

'use strict';

const { EXTRACTION_PATTERNS } = require('../../utils/constants/ExtractionPatterns');
const { TITAN_ID_SIGNATURES } = require('../../utils/constants/TitanIds');
const { EscapeProcessor } = require('../../utils/helpers/EscapeProcessor');
const { BracketMatcher } = require('../../utils/helpers/BracketMatcher');

/**
 * V168.002: TextSurgicalExtractor - JS 文本数据提取器
 *
 * 核心功能:
 * - 纯文本解析，不执行任何代码
 * - 支持变量赋值模式 (var/let/const/window.prop = ...)
 * - 处理字符转义 (\x22, \u0022, \n, \t, etc.)
 * - 智能边界检测 (配对括号匹配)
 */
class TextSurgicalExtractor {
    /**
     * 创建提取器实例
     * @param {Object} options - 配置选项
     * @param {Function} options.logger - 日志函数 (可选)
     */
    constructor(options = {}) {
        this.logger = options.logger || console;
        this.debug = options.debug || false;
    }

    /**
     * [Genesis.TextSurgical] 从原始 JavaScript 文本中提取数据
     *
     * 核心功能:
     * - 纯文本解析，不执行任何代码
     * - 支持变量赋值模式 (var/let/const/window.prop = ...)
     * - 处理字符转义 (\x22, \u0022, \n, \t, etc.)
     * - 智能边界检测 (配对括号匹配)
     *
     * @param {string} rawJsText - 原始 JavaScript 响应文本
     * @returns {Object|null} 提取的 JSON 数据，失败返回 null
     */
    extract(rawJsText) {
        this._log('info', '[Genesis.TextSurgical] 📜 Extracting from raw JS text');

        let extractedString = null;
        let extractionMethod = null;

        // 修剪空白字符
        const trimmed = rawJsText.trim();

        // 策略 1: 检测直接 JSON (以 { 或 [ 开头)
        if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
            this._log('debug', '[Genesis.TextSurgical] Strategy 1: Direct JSON detected');
            extractedString = this._extractDirectJson(trimmed);
            extractionMethod = 'Direct JSON';
        }

        // 策略 2: JavaScript 变量赋值 (var/let/const)
        if (!extractedString && trimmed.match(/\b(var|let|const)\s/)) {
            this._log('debug', '[Genesis.TextSurgical] Strategy 2: JS Variable assignment');
            extractedString = this._extractJsVariable(trimmed);
            extractionMethod = 'JS Variable';
        }

        // 策略 3: Window 属性赋值
        if (!extractedString && trimmed.includes('window.')) {
            this._log('debug', '[Genesis.TextSurgical] Strategy 3: Window property');
            extractedString = this._extractWindowProperty(trimmed);
            extractionMethod = 'Window Property';
        }

        // 策略 4: 搜索包含 Titan ID 的片段
        if (!extractedString) {
            this._log('debug', '[Genesis.TextSurgical] Strategy 4: Titan ID search');
            extractedString = this._extractByTitanId(trimmed);
            extractionMethod = 'Titan ID Search';
        }

        if (!extractedString) {
            this._log('warn', '[Genesis.TextSurgical] ❌ No extraction strategy succeeded');
            return null;
        }

        // 处理转义字符
        const deescaped = EscapeProcessor.process(extractedString);
        this._log('info', '[Genesis.TextSurgical] ✅ Escape sequences processed');

        // 尝试解析 JSON
        try {
            const jsonData = JSON.parse(deescaped);
            this._log('info', `[Genesis.TextSurgical] ✅ JSON parse success via ${extractionMethod}`);
            return jsonData;
        } catch (e) {
            this._log('error', `[Genesis.TextSurgical] ❌ JSON parse failed: ${e.message}`);
            this._log('debug', `[Genesis.TextSurgical] Extracted string (first 200 chars): ${deescaped.substring(0, 200)}`);
            return null;
        }
    }

    /**
     * 策略 1: 提取直接 JSON (从开头到结尾配对括号)
     * @private
     */
    _extractDirectJson(text) {
        this._log('debug', '[Genesis.TextSurgical] Attempting direct JSON extraction');

        const result = BracketMatcher.extractPairedBrackets(text);
        return result || null;
    }

    /**
     * 策略 2: 提取 JavaScript 变量赋值
     * @private
     */
    _extractJsVariable(text) {
        this._log('debug', '[Genesis.TextSurgical] Attempting JS variable extraction');

        const match = text.match(EXTRACTION_PATTERNS.JS_VARIABLE);
        if (match && match[1]) {
            this._log('debug', '[Genesis.TextSurgical] JS variable pattern matched');
            return BracketMatcher.extractPairedBrackets(match[1]);
        }

        // 尝试更宽松的模式 (允许跨行)
        const looseMatch = text.match(/\b(?:var|let|const)\s+\w+\s*=\s*([\s\S]*?)(?:;|$)/);
        if (looseMatch && looseMatch[1]) {
            this._log('debug', '[Genesis.TextSurgical] Loose JS variable pattern matched');
            return BracketMatcher.extractPairedBrackets(looseMatch[1].trim());
        }

        return null;
    }

    /**
     * 策略 3: 提取 Window 属性赋值
     * @private
     */
    _extractWindowProperty(text) {
        this._log('debug', '[Genesis.TextSurgical] Attempting window property extraction');

        const match = text.match(EXTRACTION_PATTERNS.WINDOW_PROPERTY);
        if (match && match[1]) {
            this._log('debug', '[Genesis.TextSurgical] Window property pattern matched');
            return BracketMatcher.extractPairedBrackets(match[1]);
        }

        // 尝试更宽松的模式
        const looseMatch = text.match(/window\.\w+\s*=\s*([\s\S]*?)(?:;|$)/);
        if (looseMatch && looseMatch[1]) {
            this._log('debug', '[Genesis.TextSurgical] Loose window property pattern matched');
            return BracketMatcher.extractPairedBrackets(looseMatch[1].trim());
        }

        return null;
    }

    /**
     * 策略 4: 通过 Titan ID 搜索提取
     * @private
     */
    _extractByTitanId(text) {
        this._log('debug', '[Genesis.TextSurgical] Searching for Titan ID signatures');

        for (const titanId of TITAN_ID_SIGNATURES) {
            const patterns = [
                new RegExp(`\\{[^}]*"${titanId}"[^}]*\\}`, 'g'),  // 对象
                new RegExp(`\\[[^\\]]*"${titanId}"[^\\]]*\\]`, 'g')  // 数组
            ];

            for (const pattern of patterns) {
                const matches = text.match(pattern);
                if (matches && matches.length > 0) {
                    this._log('debug', `[Genesis.TextSurgical] Found Titan ID "${titanId}" in pattern`);
                    return matches[0];
                }
            }
        }

        return null;
    }

    /**
     * 内部日志方法
     * @private
     */
    _log(level, ...args) {
        if (this.logger && typeof this.logger[level] === 'function') {
            this.logger[level](...args);
        } else if (level === 'error' || level === 'warn') {
            console[level](...args);
        } else if (this.debug) {
            console[level](...args);
        }
    }
}

module.exports = { TextSurgicalExtractor };
