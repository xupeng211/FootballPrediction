/**
 * Bracket Matcher - V168.002 Helper Module
 * ======================================
 *
 * [Genesis.Architect] 括号匹配工具 - 提取为独立模块
 *
 * 处理嵌套对象和数组的括号匹配。
 *
 * @module utils/helpers/BracketMatcher
 * @version V168.002
 * @since 2026-02-02
 * @author [Genesis.Architect]
 */

'use strict';

/**
 * V168.002: 括号匹配器
 *
 * 辅助函数：提取配对括号内的完整内容
 */
class BracketMatcher {
    /**
     * 提取配对括号内的完整内容
     * @param {string} text - 包含括号的文本
     * @param {string} openChar - 开括号字符（默认自动检测）
     * @returns {string|null} 匹配的完整内容，失败返回 null
     */
    static extractPairedBrackets(text, openChar = null) {
        if (!text || typeof text !== 'string') {
            return null;
        }

        const trimmed = text.trim();

        // 自动检测开括号
        const firstChar = openChar || trimmed.charAt(0);

        if (firstChar !== '{' && firstChar !== '[') {
            return trimmed;  // 不是对象或数组开头，直接返回
        }

        const closeChar = firstChar === '{' ? '}' : ']';
        let openCount = 1;
        let closeIndex = -1;

        for (let i = 1; i < trimmed.length; i++) {
            const char = trimmed.charAt(i);
            if (char === firstChar) {
                openCount++;
            } else if (char === closeChar) {
                openCount--;
                if (openCount === 0) {
                    closeIndex = i;
                    break;
                }
            }
        }

        if (closeIndex > 0) {
            return trimmed.substring(0, closeIndex + 1);
        }

        return null;
    }

    /**
     * 检查括号是否配对
     * @param {string} text - 要检查的文本
     * @returns {boolean} 是否配对
     */
    static isBalanced(text) {
        if (!text || typeof text !== 'string') {
            return false;
        }

        let count = 0;
        const openChars = '{[';
        const closeChars = '}]';

        for (const char of text) {
            const openIndex = openChars.indexOf(char);
            const closeIndex = closeChars.indexOf(char);

            if (openIndex !== -1) {
                count++;
            } else if (closeIndex !== -1 && closeIndex === openIndex) {
                count--;
                if (count < 0) {
                    return false;  // 闭合括号多于开括号
                }
            }
        }

        return count === 0;
    }
}

module.exports = { BracketMatcher };
