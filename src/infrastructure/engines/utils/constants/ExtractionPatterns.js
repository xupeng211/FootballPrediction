/**
 * Extraction Patterns - V168.002 Constants Module
 * ===============================================
 *
 * [Genesis.Architect] 正则模式集合 - 提取为独立常量模块
 *
 * 用于从 JavaScript 响应中提取数据而不执行代码。
 *
 * @module utils/constants/ExtractionPatterns
 * @version V168.002
 * @since 2026-02-02
 * @author [Genesis.Architect]
 */

'use strict';

/**
 * [Genesis.TextSurgical] 正则模式集合
 * 用于从 JavaScript 响应中提取数据而不执行代码
 */
const EXTRACTION_PATTERNS = {
    // JavaScript 变量赋值: var name = {...}; 或 let name = [...];
    JS_VARIABLE: /\b(?:var|let|const)\s+\w+\s*=\s*(\[[\s\S]*?\]|\{[\s\S]*?\})\s*;?$/,

    // Window 属性赋值: window.name = {...};
    WINDOW_PROPERTY: /window\.\w+\s*=\s*(\[[\s\S]*?\]|\{[\s\S]*?\})\s*;?$/,

    // 直接包含 Titan ID 的 JSON 对象/数组
    TITAN_JSON: /(\{[\s\S]*?"18"[\s\S]*?\}|\[[\s\S]*?"18"[\s\S]*?\])/,

    // 十六进制转义: \x22 → "
    HEX_ESCAPE: /\\x([0-9a-fA-F]{2})/g,

    // Unicode 转义: \u0022 → "
    UNICODE_ESCAPE: /\\u([0-9a-fA-F]{4})/g,

    // 标准转义序列
    STANDARD_ESCAPE: /\\([nrtbfv'"\\])/g
};

module.exports = { EXTRACTION_PATTERNS };
