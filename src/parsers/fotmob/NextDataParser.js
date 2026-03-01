/**
 * NextDataParser - __NEXT_DATA__ 解析器
 * ==============================================
 *
 * 从 FotMob 网页中提取 __NEXT_DATA__ 并转换为 API 兼容格式
 * 纯函数设计，易于测试
 *
 * @module parsers/fotmob/NextDataParser
 * @version V174.0.0
 */

'use strict';

/**
 * 从页面中提取 __NEXT_DATA__ JSON 数据
 *
 * @param {import('playwright').Page} page - Playwright 页面对象
 * @returns {Promise<{ success: boolean, data?: object, error?: string }>}
 */
async function extractNextData(page) {
    try {
        const rawData = await page.evaluate(() => {
            const el = document.getElementById('__NEXT_DATA__');
            if (!el) return null;

            try {
                return JSON.parse(el.innerHTML);
            } catch (e) {
                return { error: `JSON 解析失败: ${e.message}` };
            }
        });

        if (!rawData) {
            return {
                success: false,
                error: 'NO_NEXT_DATA:无法找到 __NEXT_DATA__ 标签'
            };
        }

        if (rawData.error) {
            return {
                success: false,
                error: `PARSE_ERROR:${rawData.error}`
            };
        }

        return {
            success: true,
            data: rawData
        };

    } catch (e) {
        return {
            success: false,
            error: `EXTRACT_ERROR:${e.message}`
        };
    }
}

/**
 * 从 HTML 字符串中提取 __NEXT_DATA__（纯函数版本）
 *
 * @param {string} html - 页面 HTML
 * @returns {{ success: boolean, data?: object, error?: string }}
 */
function extractFromHtml(html) {
    if (!html || typeof html !== 'string') {
        return {
            success: false,
            error: 'INVALID_INPUT:HTML 不是有效字符串'
        };
    }

    // 匹配 __NEXT_DATA__ 标签
    const match = html.match(/<script\s+id="__NEXT_DATA__"\s+type="application\/json"[^>]*>([\s\S]*?)<\/script>/i);

    if (!match || !match[1]) {
        // 尝试另一种匹配方式
        const altMatch = html.match(/<script[^>]*id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/i);

        if (!altMatch || !altMatch[1]) {
            return {
                success: false,
                error: 'NO_NEXT_DATA:无法找到 __NEXT_DATA__ 标签'
            };
        }

        try {
            const data = JSON.parse(altMatch[1].trim());
            return { success: true, data };
        } catch (e) {
            return {
                success: false,
                error: `PARSE_ERROR:JSON 解析失败: ${e.message}`
            };
        }
    }

    try {
        const data = JSON.parse(match[1].trim());
        return { success: true, data };
    } catch (e) {
        return {
            success: false,
            error: `PARSE_ERROR:JSON 解析失败: ${e.message}`
        };
    }
}

/**
 * 将 __NEXT_DATA__ 格式转换为 API 兼容格式
 *
 * FotMob 网页版数据结构:
 *   pageProps.content - 核心数据 (stats, lineup, shotmap 等)
 *   pageProps.general - 比赛基本信息
 *   pageProps.header - 头部信息
 *
 * @param {object} nextData - __NEXT_DATA__ 对象
 * @param {string} matchId - 比赛标识符
 * @returns {object|null} API 兼容格式数据，失败返回 null
 */
function transformToApiFormat(nextData, matchId) {
    if (!nextData || !nextData.props || !nextData.props.pageProps) {
        return null;
    }

    const pageProps = nextData.props.pageProps;

    // 验证核心数据是否存在
    if (!pageProps.content) {
        return null;
    }

    const apiFormat = {
        matchId: matchId,
        content: pageProps.content || {},
        general: pageProps.general || {},
        header: pageProps.header || {},
        // 保留元数据
        _meta: {
            source: 'web_infiltration',
            extractedAt: new Date().toISOString(),
            hasStats: !!(pageProps.content?.stats),
            hasLineup: !!(pageProps.content?.lineup),
            hasShotmap: !!(pageProps.content?.shotmap)
        }
    };

    return apiFormat;
}

/**
 * 验证 __NEXT_DATA__ 结构完整性
 *
 * @param {object} nextData - __NEXT_DATA__ 对象
 * @returns {{ valid: boolean, missing: string[] }}
 */
function validateNextDataStructure(nextData) {
    const missing = [];

    if (!nextData) {
        missing.push('nextData');
        return { valid: false, missing };
    }

    if (!nextData.props) {
        missing.push('props');
    } else if (!nextData.props.pageProps) {
        missing.push('props.pageProps');
    }

    if (nextData?.props?.pageProps && !nextData.props.pageProps.content) {
        missing.push('props.pageProps.content');
    }

    return {
        valid: missing.length === 0,
        missing
    };
}

/**
 * 完整的提取和转换流程
 *
 * @param {import('playwright').Page} page - Playwright 页面对象
 * @param {string} matchId - 比赛标识符
 * @returns {Promise<{ success: boolean, data?: object, error?: string }>}
 */
async function extractAndTransform(page, matchId) {
    // 1. 提取 __NEXT_DATA__
    const extractResult = await extractNextData(page);

    if (!extractResult.success) {
        return extractResult;
    }

    // 2. 验证结构
    const validation = validateNextDataStructure(extractResult.data);
    if (!validation.valid) {
        return {
            success: false,
            error: `INVALID_STRUCTURE:缺少字段 ${validation.missing.join(', ')}`
        };
    }

    // 3. 转换格式
    const apiData = transformToApiFormat(extractResult.data, matchId);

    if (!apiData) {
        return {
            success: false,
            error: 'TRANSFORM_FAILED:数据格式转换失败'
        };
    }

    return {
        success: true,
        data: apiData,
        raw: extractResult.data
    };
}

module.exports = {
    extractNextData,
    extractFromHtml,
    transformToApiFormat,
    validateNextDataStructure,
    extractAndTransform
};
