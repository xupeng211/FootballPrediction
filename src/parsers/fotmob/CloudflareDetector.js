/**
 * CloudflareDetector - Cloudflare 拦截检测器
 * ==============================================
 *
 * 检测页面是否被 Cloudflare 拦截
 * 纯函数设计，易于测试
 *
 * @module parsers/fotmob/CloudflareDetector
 * @version V174.0.0
 */

'use strict';

/**
 * Cloudflare 指示器关键词
 */
const CF_INDICATORS = [
    'Just a moment...',
    'Checking your browser',
    'Please Wait...',
    'Cloudflare',
    'cf-browser-verification',
    'challenge-platform',
    'cf-ray',
    'DDoS protection by Cloudflare'
];

/**
 * 检测页面内容是否包含 Cloudflare 拦截特征
 *
 * @param {string} content - 页面 HTML 内容
 * @param {string} title - 页面标题
 * @returns {{ blocked: boolean, indicators: string[] }}
 */
function detectCloudflareBlock(content, title = '') {
    const indicators = [];
    const combinedText = `${content} ${title}`.toLowerCase();

    for (const indicator of CF_INDICATORS) {
        if (combinedText.includes(indicator.toLowerCase())) {
            indicators.push(indicator);
        }
    }

    return {
        blocked: indicators.length > 0,
        indicators
    };
}

/**
 * 检测页面是否被 Cloudflare 拦截（从 Playwright Page 对象）
 *
 * @param {import('playwright').Page} page - Playwright 页面对象
 * @returns {Promise<{ blocked: boolean, indicators: string[] }>}
 */
async function detectFromPage(page) {
    try {
        const content = await page.content();
        const title = await page.title();

        return detectCloudflareBlock(content, title);
    } catch (e) {
        // 如果无法获取页面内容，假设未被拦截
        return {
            blocked: false,
            indicators: [],
            error: e.message
        };
    }
}

/**
 * 从页面 HTML 中检测 Cloudflare（纯函数版本）
 *
 * @param {string} html - 页面 HTML
 * @returns {{ blocked: boolean, indicators: string[] }}
 */
function detectFromHtml(html) {
    if (!html || typeof html !== 'string') {
        return { blocked: false, indicators: [] };
    }

    // 提取 title
    const titleMatch = html.match(/<title[^>]*>([^<]*)<\/title>/i);
    const title = titleMatch ? titleMatch[1] : '';

    return detectCloudflareBlock(html, title);
}

/**
 * 检查响应状态码是否表示被拦截
 *
 * @param {number} statusCode - HTTP 状态码
 * @returns {boolean}
 */
function isBlockedStatus(statusCode) {
    return statusCode === 403 || statusCode === 503;
}

/**
 * 综合检测结果
 *
 * @param {Object} options - 检测选项
 * @param {string} options.content - 页面内容
 * @param {string} options.title - 页面标题
 * @param {number} options.statusCode - HTTP 状态码
 * @returns {{ blocked: boolean, reason: string, indicators: string[] }}
 */
function comprehensiveCheck(options = {}) {
    const { content = '', title = '', statusCode = 200 } = options;

    // 检查状态码
    if (isBlockedStatus(statusCode)) {
        return {
            blocked: true,
            reason: `HTTP_${statusCode}`,
            indicators: [`Status code ${statusCode}`]
        };
    }

    // 检查内容
    const result = detectCloudflareBlock(content, title);

    if (result.blocked) {
        return {
            blocked: true,
            reason: 'CF_CHALLENGE',
            indicators: result.indicators
        };
    }

    return {
        blocked: false,
        reason: null,
        indicators: []
    };
}

module.exports = {
    CF_INDICATORS,
    detectCloudflareBlock,
    detectFromPage,
    detectFromHtml,
    isBlockedStatus,
    comprehensiveCheck
};
