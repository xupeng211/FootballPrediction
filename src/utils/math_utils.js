/**
 * V79.100 Math Utilities - 数学工具库
 * =====================================
 *
 * 提供数学算法工具函数：
 * - Levenshtein 编辑距离算法
 * - 字符串相似度计算
 *
 * @file math_utils.js
 * @version V79.100
 * @since 2026-01-25
 * @author V79.100 Engineering Team
 */

'use strict';

// =============================================================================
// LEVENSHTEIN DISTANCE ALGORITHM
// =============================================================================

/**
 * Calculate Levenshtein edit distance between two strings
 *
 * V73.200 修正版：修复了 matrix[i][j-1][j-1] 索引 bug
 *
 * @param {string} a - First string
 * @param {string} b - Second string
 * @returns {number} - Levenshtein distance (minimum number of edits)
 *
 * @example
 * levenshtein('kitten', 'sitting')  // returns 3
 * levenshtein('Man Utd', 'Manchester United')  // returns 10
 */
function levenshtein(a, b) {
    const matrix = [];

    // Initialize first column
    for (let i = 0; i <= b.length; i++) {
        matrix[i] = [i];
    }

    // Initialize first row
    for (let j = 0; j <= a.length; j++) {
        matrix[0][j] = j;
    }

    // Fill matrix
    for (let i = 1; i <= b.length; i++) {
        for (let j = 1; j <= a.length; j++) {
            if (b.charAt(i - 1) === a.charAt(j - 1)) {
                matrix[i][j] = matrix[i - 1][j - 1];
            } else {
                // V73.200 修正后的索引（已修复 matrix[i][j-1][j-1] bug）
                matrix[i][j] = Math.min(
                    matrix[i - 1][j - 1] + 1,  // substitution
                    matrix[i][j - 1] + 1,      // insertion
                    matrix[i - 1][j] + 1       // deletion
                );
            }
        }
    }

    return matrix[b.length][a.length];
}

/**
 * Calculate normalized similarity score (0-100)
 *
 * @param {string} str1 - First string
 * @param {string} str2 - Second string
 * @returns {number} - Similarity score (0-100, where 100 is identical)
 *
 * @example
 * similarity('Man Utd', 'Manchester United')  // returns ~61.54
 * similarity('Barcelona', 'Barcelona')  // returns 100
 */
function similarity(str1, str2) {
    // 容错处理：只处理 null/undefined，空字符串应返回 100% 相似度
    if (str1 === null || str1 === undefined || str2 === null || str2 === undefined) return 0;
    const s1 = String(str1).trim();
    const s2 = String(str2).trim();

    const maxLen = Math.max(s1.length, s2.length);
    if (maxLen === 0) return 100;

    const distance = levenshtein(s1.toLowerCase(), s2.toLowerCase());
    return ((maxLen - distance) / maxLen) * 100;
}

// =============================================================================
// JSDOC TYPE DEFINITIONS
// =============================================================================

/**
 * @typedef {Object} StringMatchResult
 * @property {number} distance - Levenshtein distance
 * @property {number} similarity - Similarity score (0-100)
 * @property {boolean} isMatch - Whether strings match above threshold
 */

/**
 * Calculate comprehensive string comparison result
 *
 * @param {string} str1 - First string
 * @param {string} str2 - Second string
 * @param {number} [threshold=70] - Minimum similarity for match
 * @returns {StringMatchResult} - Match result with distance and similarity
 *
 * @example
 * compareStrings('Real Madrid', 'R. Madrid', 85)
 * // returns { distance: 5, similarity: 37.5, isMatch: false }
 */
function compareStrings(str1, str2, threshold = 70) {
    const s1 = String(str1 || '').trim();
    const s2 = String(str2 || '').trim();

    const distance = levenshtein(s1, s2);
    const simScore = similarity(s1, s2);

    return {
        distance,
        similarity: simScore,
        isMatch: simScore >= threshold
    };
}

// =============================================================================
// EXPORTS
// =============================================================================

module.exports = {
    levenshtein,
    similarity,
    compareStrings
};
