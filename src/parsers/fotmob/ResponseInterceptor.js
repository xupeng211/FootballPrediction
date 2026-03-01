/**
 * ResponseInterceptor - V175 动态响应拦截器
 * ============================================
 *
 * 核心战术：在浏览器加载过程中，实时监控并截获 API 响应
 *
 * 特性：
 * - 精准匹配 matchDetails API
 * - 一旦截获 JSON，立即发出完成信号
 * - 支持超时和降级
 * - 零 HTML 解析开销
 *
 * @module parsers/fotmob/ResponseInterceptor
 * @version V175.0.0
 */

'use strict';

/**
 * 拦截结果
 * @typedef {Object} InterceptResult
 * @property {boolean} success - 是否成功
 * @property {Object|null} data - 截获的 JSON 数据
 * @property {string|null} error - 错误信息
 * @property {number} responseTime - 响应时间 (ms)
 * @property {string} url - 截获的 URL
 * @property {number} size - 数据大小 (bytes)
 */

/**
 * 目标 API 模式
 */
const TARGET_PATTERNS = [
    /matchDetails/i,
    /api\/data\/match/i,
    /api\/matchDetails/i,
];

/**
 * HTML 页面模式 (用于混合模式)
 */
const HTML_PATTERNS = [
    /fotmob\.com\/match\/\d+/i,
];

/**
 * ResponseInterceptor - 动态响应拦截器
 */
class ResponseInterceptor {
    /**
     * @param {Object} options - 配置选项
     * @param {number} options.timeout - 超时时间 (ms)
     * @param {string[]} options.targetPatterns - 自定义匹配模式
     * @param {boolean} options.hybridMode - 启用混合模式 (拦截 HTML + 提取 __NEXT_DATA__)
     */
    constructor(options = {}) {
        this.timeout = options.timeout || 15000;
        this.targetPatterns = options.targetPatterns || TARGET_PATTERNS;
        this.htmlPatterns = options.htmlPatterns || HTML_PATTERNS;
        this.hybridMode = options.hybridMode ?? true;  // 默认启用混合模式

        // 拦截状态
        this.capturedData = null;
        this.capturedUrl = null;
        this.startTime = null;
        this.isCompleted = false;
        this.htmlContent = null;

        // Promise 控制器
        this._resolve = null;
        this._reject = null;
        this._timeoutId = null;

        // 统计
        this.stats = {
            totalIntercepted: 0,
            matchedIntercepted: 0,
            jsonParsed: 0,
            jsonFailed: 0,
            htmlExtracted: 0,
            htmlFailed: 0,
        };

        // 日志前缀
        this.logPrefix = '🔪 [ResponseInterceptor]';
    }

    /**
     * 检查 URL 是否匹配目标模式
     * @private
     * @param {string} url - 请求 URL
     * @returns {boolean}
     */
    _isTargetUrl(url) {
        return this.targetPatterns.some(pattern => pattern.test(url));
    }

    /**
     * 检查 URL 是否匹配 HTML 页面模式
     * @private
     * @param {string} url - 请求 URL
     * @returns {boolean}
     */
    _isHtmlPage(url) {
        return this.htmlPatterns.some(pattern => pattern.test(url));
    }

    /**
     * 从 HTML 中提取 __NEXT_DATA__
     * @private
     * @param {string} html - HTML 内容
     * @returns {object|null}
     */
    _extractNextData(html) {
        if (!html || typeof html !== 'string') return null;

        const match = html.match(/<script\s+id="__NEXT_DATA__"\s+type="application\/json"[^>]*>([\s\S]*?)<\/script>/i);
        if (!match || !match[1]) {
            const altMatch = html.match(/<script[^>]*id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/i);
            if (!altMatch || !altMatch[1]) return null;
            try {
                return JSON.parse(altMatch[1].trim());
            } catch (e) {
                return null;
            }
        }

        try {
            return JSON.parse(match[1].trim());
        } catch (e) {
            return null;
        }
    }

    /**
     * 处理响应
     * @private
     * @param {import('playwright').Response} response - 响应对象
     */
    async _handleResponse(response) {
        if (this.isCompleted) return;

        const url = response.url();
        this.stats.totalIntercepted++;

        const status = response.status();

        // 模式 1: 尝试拦截 API 响应 (matchDetails)
        if (this._isTargetUrl(url)) {
            this.stats.matchedIntercepted++;
            console.log(`${this.logPrefix} 捕获 API 响应: ${url.substring(0, 80)}...`);
            console.log(`${this.logPrefix}    状态码: ${status}`);

            if (status !== 200) {
                console.log(`${this.logPrefix}    ⚠️ 非成功状态，继续等待...`);
                return;
            }

            try {
                const data = await response.json();
                this.stats.jsonParsed++;

                const responseTime = Date.now() - this.startTime;
                const size = JSON.stringify(data).length;

                console.log(`${this.logPrefix}    ✅ JSON 提取成功!`);
                console.log(`${this.logPrefix}    大小: ${size} bytes`);
                console.log(`${this.logPrefix}    耗时: ${responseTime}ms`);

                this.capturedData = data;
                this.capturedUrl = url;
                this.isCompleted = true;

                if (this._timeoutId) {
                    clearTimeout(this._timeoutId);
                    this._timeoutId = null;
                }

                if (this._resolve) {
                    this._resolve({
                        success: true,
                        data,
                        error: null,
                        responseTime,
                        url,
                        size,
                        mode: 'api'
                    });
                }
                return;

            } catch (error) {
                this.stats.jsonFailed++;
                console.log(`${this.logPrefix}    ❌ JSON 解析失败: ${error.message}`);
            }
        }

        // 模式 2: 混合模式 - 拦截 HTML 页面并提取 __NEXT_DATA__
        if (this.hybridMode && this._isHtmlPage(url) && status === 200) {
            console.log(`${this.logPrefix} 捕获 HTML 页面: ${url.substring(0, 60)}...`);

            try {
                const html = await response.text();
                const nextData = this._extractNextData(html);

                if (nextData && nextData.props && nextData.props.pageProps) {
                    this.stats.htmlExtracted++;

                    const responseTime = Date.now() - this.startTime;
                    const size = html.length;

                    console.log(`${this.logPrefix}    ✅ __NEXT_DATA__ 提取成功!`);
                    console.log(`${this.logPrefix}    HTML 大小: ${size} bytes`);
                    console.log(`${this.logPrefix}    耗时: ${responseTime}ms`);

                    // 转换为 API 兼容格式
                    const apiData = this._transformNextData(nextData);

                    this.capturedData = apiData;
                    this.capturedUrl = url;
                    this.htmlContent = html;
                    this.isCompleted = true;

                    if (this._timeoutId) {
                        clearTimeout(this._timeoutId);
                        this._timeoutId = null;
                    }

                    if (this._resolve) {
                        this._resolve({
                            success: true,
                            data: apiData,
                            raw: nextData,
                            error: null,
                            responseTime,
                            url,
                            size,
                            mode: 'hybrid'
                        });
                    }
                } else {
                    this.stats.htmlFailed++;
                    console.log(`${this.logPrefix}    ⚠️ HTML 中未找到有效的 __NEXT_DATA__`);
                }
            } catch (error) {
                this.stats.htmlFailed++;
                console.log(`${this.logPrefix}    ❌ HTML 解析失败: ${error.message}`);
            }
        }
    }

    /**
     * 将 __NEXT_DATA__ 转换为 API 兼容格式
     * @private
     */
    _transformNextData(nextData) {
        if (!nextData?.props?.pageProps) return null;

        const pageProps = nextData.props.pageProps;

        return {
            matchId: pageProps.general?.matchId || 'unknown',
            content: pageProps.content || {},
            general: pageProps.general || {},
            header: pageProps.header || {},
            _meta: {
                source: 'hybrid_intercept',
                extractedAt: new Date().toISOString(),
                hasStats: !!(pageProps.content?.stats),
                hasLineup: !!(pageProps.content?.lineup),
                hasShotmap: !!(pageProps.content?.shotmap)
            }
        };
    }

    /**
     * 设置页面拦截
     * @param {import('playwright').Page} page - Playwright 页面对象
     */
    setup(page) {
        this.startTime = Date.now();
        this.isCompleted = false;
        this.capturedData = null;
        this.capturedUrl = null;
        this.htmlContent = null;

        const modeStr = this.hybridMode ? 'API + HTML 混合' : '纯 API';
        console.log(`${this.logPrefix} 启动响应拦截器...`);
        console.log(`${this.logPrefix}    模式: ${modeStr}`);
        console.log(`${this.logPrefix}    超时: ${this.timeout}ms`);
        console.log(`${this.logPrefix}    API 模式: ${this.targetPatterns.length} 个`);
        if (this.hybridMode) {
            console.log(`${this.logPrefix}    HTML 模式: ${this.htmlPatterns.length} 个`);
        }

        // 监听响应事件
        page.on('response', this._handleResponse.bind(this));

        console.log(`${this.logPrefix} ✅ 拦截器已激活`);
    }

    /**
     * 等待拦截完成
     * @returns {Promise<InterceptResult>}
     */
    waitForCapture() {
        return new Promise((resolve, reject) => {
            // 如果已经完成，直接返回
            if (this.isCompleted) {
                resolve({
                    success: true,
                    data: this.capturedData,
                    error: null,
                    responseTime: Date.now() - this.startTime,
                    url: this.capturedUrl,
                    size: JSON.stringify(this.capturedData || {}).length
                });
                return;
            }

            // 保存 resolve/reject
            this._resolve = resolve;
            this._reject = reject;

            // 设置超时
            this._timeoutId = setTimeout(() => {
                if (!this.isCompleted) {
                    console.log(`${this.logPrefix} ⏱️ 拦截超时!`);
                    this.isCompleted = true;
                    resolve({
                        success: false,
                        data: null,
                        error: '拦截超时',
                        responseTime: this.timeout,
                        url: null,
                        size: 0
                    });
                }
            }, this.timeout);
        });
    }

    /**
     * 停止拦截器
     */
    stop() {
        if (this._timeoutId) {
            clearTimeout(this._timeoutId);
            this._timeoutId = null;
        }
        this.isCompleted = true;
    }

    /**
     * 获取统计信息
     * @returns {Object}
     */
    getStats() {
        return {
            ...this.stats,
            captureTime: this.isCompleted ? Date.now() - this.startTime : null
        };
    }
}

/**
 * 创建拦截器并等待捕获
 * 便捷函数：一行代码完成拦截
 *
 * V175 混合模式:
 * 1. 尝试拦截 API 响应 (matchDetails)
 * 2. 如果 API 不可用，等待 DOM 加载后从页面提取 __NEXT_DATA__
 *
 * @param {import('playwright').Page} page - Playwright 页面对象
 * @param {string} url - 要访问的 URL
 * @param {Object} options - 配置选项
 * @returns {Promise<InterceptResult>}
 *
 * @example
 * const result = await interceptMatchDetails(page, 'https://www.fotmob.com/match/12345');
 * if (result.success) {
 *     console.log('截获数据:', result.data);
 * }
 */
async function interceptMatchDetails(page, url, options = {}) {
    const interceptor = new ResponseInterceptor(options);
    interceptor.setup(page);

    const startTime = Date.now();
    const timeout = options.timeout || 15000;

    // 启动页面加载
    const gotoPromise = page.goto(url, {
        waitUntil: 'domcontentloaded',  // 等待 DOM 加载
        timeout
    });

    // 等待 API 拦截或 DOM 加载完成
    const raceResult = await Promise.race([
        // 路径 1: API 拦截成功
        interceptor.waitForCapture().then(result => ({ type: 'intercept', result })),

        // 路径 2: DOM 加载完成
        gotoPromise.then(() => ({ type: 'domloaded' })).catch(e => ({ type: 'error', error: e.message }))
    ]);

    // 停止拦截器（清理超时定时器）
    interceptor.stop();

    // 如果 API 拦截成功，直接返回
    if (raceResult.type === 'intercept' && raceResult.result.success) {
        console.log(`🔪 [ResponseInterceptor] API 拦截成功!`);
        return raceResult.result;
    }

    // 如果 DOM 加载完成，尝试从页面提取 __NEXT_DATA__
    if (raceResult.type === 'domloaded') {
        console.log(`🔪 [ResponseInterceptor] DOM 加载完成，尝试提取 __NEXT_DATA__...`);

        try {
            const nextData = await page.evaluate(() => {
                const el = document.getElementById('__NEXT_DATA__');
                if (!el) return null;
                try {
                    return JSON.parse(el.innerHTML);
                } catch (e) {
                    return null;
                }
            });

            if (nextData && nextData.props && nextData.props.pageProps) {
                const responseTime = Date.now() - startTime;

                // 转换为 API 兼容格式
                const pageProps = nextData.props.pageProps;
                const apiData = {
                    matchId: pageProps.general?.matchId || 'unknown',
                    content: pageProps.content || {},
                    general: pageProps.general || {},
                    header: pageProps.header || {},
                    _meta: {
                        source: 'dom_extraction',
                        extractedAt: new Date().toISOString(),
                        hasStats: !!(pageProps.content?.stats),
                        hasLineup: !!(pageProps.content?.lineup),
                        hasShotmap: !!(pageProps.content?.shotmap)
                    }
                };

                const size = JSON.stringify(apiData).length;

                console.log(`🔪 [ResponseInterceptor] ✅ __NEXT_DATA__ 提取成功!`);
                console.log(`🔪 [ResponseInterceptor]    大小: ${size} bytes`);
                console.log(`🔪 [ResponseInterceptor]    耗时: ${responseTime}ms`);

                return {
                    success: true,
                    data: apiData,
                    raw: nextData,
                    error: null,
                    responseTime,
                    url,
                    size,
                    mode: 'dom_extraction'
                };
            } else {
                console.log(`🔪 [ResponseInterceptor] ❌ 页面中未找到 __NEXT_DATA__`);
                return {
                    success: false,
                    data: null,
                    error: 'NO_NEXT_DATA:页面中未找到有效数据',
                    responseTime: Date.now() - startTime,
                    url,
                    size: 0,
                    mode: 'dom_extraction'
                };
            }
        } catch (e) {
            console.log(`🔪 [ResponseInterceptor] ❌ DOM 提取失败: ${e.message}`);
            return {
                success: false,
                data: null,
                error: `DOM_EXTRACTION_ERROR:${e.message}`,
                responseTime: Date.now() - startTime,
                url,
                size: 0,
                mode: 'dom_extraction'
            };
        }
    }

    // 其他错误情况
    return {
        success: false,
        data: null,
        error: raceResult.error || '未知错误',
        responseTime: Date.now() - startTime,
        url,
        size: 0,
        mode: 'unknown'
    };
}

module.exports = {
    ResponseInterceptor,
    interceptMatchDetails,
    TARGET_PATTERNS,
    HTML_PATTERNS
};
