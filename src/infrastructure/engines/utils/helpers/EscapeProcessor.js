/**
 * Escape Processor - V168.002 Helper Module
 * =========================================
 *
 * [Genesis.Architect] 转义字符处理工具 - 提取为独立模块
 *
 * 处理 JavaScript 字符串中的各种转义序列。
 *
 * @module utils/helpers/EscapeProcessor
 * @version V168.002
 * @since 2026-02-02
 * @author [Genesis.Architect]
 */

'use strict';

/**
 * V168.002: 转义字符处理器
 *
 * 处理 \x22, \u0022, \n, \t 等转义序列
 */
class EscapeProcessor {
    /**
     * 处理字符串中的转义字符
     * @param {string} text - 包含转义字符的文本
     * @returns {string} 处理后的文本
     */
    static process(text) {
        if (!text || typeof text !== 'string') {
            return text;
        }

        // 按顺序处理各种转义
        let result = text;

        // 1. 十六进制转义: \x22 → "
        result = result.replace(/\\x([0-9a-fA-F]{2})/g, (match, hex) => {
            return String.fromCharCode(parseInt(hex, 16));
        });

        // 2. Unicode 转义: \u0022 → "
        result = result.replace(/\\u([0-9a-fA-F]{4})/g, (match, hex) => {
            return String.fromCharCode(parseInt(hex, 16));
        });

        // 3. 标准转义序列: \n, \t, \r, \b, \f, \v, ', ", \
        result = result.replace(/\\n/g, '\n')
                       .replace(/\\t/g, '\t')
                       .replace(/\\r/g, '\r')
                       .replace(/\\b/g, '\b')
                       .replace(/\\f/g, '\f')
                       .replace(/\\v/g, '\v')
                       .replace(/\\'/g, "'")
                       .replace(/\\"/g, '"')
                       .replace(/\\\\/g, '\\');

        return result;
    }

    /**
     * V168.002: 批量处理转义字符
     * @param {string[]} textArray - 文本数组
     * @returns {string[]} 处理后的文本数组
     */
    static processBatch(textArray) {
        if (!Array.isArray(textArray)) {
            return [];
        }

        return textArray.map(text => EscapeProcessor.process(text));
    }
}

module.exports = { EscapeProcessor };
