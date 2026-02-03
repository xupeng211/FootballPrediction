/**
 * SignalRadar - V168.002 Modular Edition
 * ==========================================
 *
 * [Genesis.Architect] 网络雷达调度中心 - 模块化重构
 *
 * 核心变更:
 * - 网络拦截逻辑已移至 intercept/NetworkInterceptor.js
 * - 文本提取逻辑已移至 extractors/TextSurgicalExtractor.js
 * - 日志工具已移至 logging/RadarLogger.js
 * - 常量已移至 utils/constants/
 * - 本文件只保留流程编排和向后兼容适配
 *
 * @module services/SignalRadar
 * @version V168.002
 * @since 2026-02-02
 * @author [Genesis.Architect]
 */

'use strict';

// V168.002: 从独立模块导入
const { NetworkInterceptor, ResponseBuffer } = require('./intercept/NetworkInterceptor');
const { TextSurgicalExtractor } = require('./extractors/TextSurgicalExtractor');
const { RadarLogger } = require('./logging/RadarLogger');
const { TITAN_ID_SIGNATURES } = require('../utils/constants/TitanIds');
const { EXTRACTION_PATTERNS } = require('../utils/constants/ExtractionPatterns');

/**
 * 信号雷达服务 - V164.1 ForceIntercept Edition
 *
 * 数据流: /match-event/*.dat → Base64 → atob() → JXG.decompress → JSON → window._TITAN_ARTERY_DATA
 */
class SignalRadar {
    /**
     * V168.002: 构造函数 - 使用模块化组件
     * @param {Page} page - Playwright page instance
     * @param {Object} options - Configuration options
     */
    constructor(page, options = {}) {
        this.page = page;

        // V168.002: 使用模块化组件
        this.logger = new RadarLogger({
            prefix: '[SignalRadar.V168.002]',
            level: options.logLevel || 'info'
        });

        this.interceptor = new NetworkInterceptor(page, {
            maxResponseSize: options.maxResponseSize,
            minResponseSize: options.minResponseSize,
            pollingInterval: options.pollingInterval,
            interceptWindow: options.interceptWindow
        });

        this.extractor = new TextSurgicalExtractor({
            logger: this.logger,
            debug: options.debug || false
        });

        // V168.002: 保留向后兼容的数据存储
        this.capturedResponses = [];
        this.isInterceptionEnabled = false;
        this.decompressionResults = [];
        this.capturedAjaxData = [];

        // 配置
        this.config = {
            memoryHookTimeout: options.memoryHookTimeout || 12000,
            domFallbackTimeout: options.domFallbackTimeout || 5000,
            // V168.002 Fix: 响应大小限制配置 (用于 enableTriggerMode)
            minResponseSize: options.minResponseSize || 100,
            maxResponseSize: options.maxResponseSize || (200 * 1024)  // 200KB
        };
    }

    /**
     * V168.002: 日志方法委托
     */
    debug(...args) { this.logger.debug(...args); }
    info(...args) { this.logger.info(...args); }
    warn(...args) { this.logger.warn(...args); }
    error(...args) { this.logger.error(...args); }

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
    _extractFromRawJs(rawJsText) {
        this.info('[Genesis.TextSurgical] 📜 Extracting from raw JS text');

        let extractedString = null;
        let extractionMethod = null;

        // 修剪空白字符
        const trimmed = rawJsText.trim();

        // 策略 1: 检测直接 JSON (以 { 或 [ 开头)
        if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
            this.debug('[Genesis.TextSurgical] Strategy 1: Direct JSON detected');
            extractedString = this._extractDirectJson(trimmed);
            extractionMethod = 'Direct JSON';
        }

        // 策略 2: JavaScript 变量赋值 (var/let/const)
        if (!extractedString && trimmed.match(/\b(var|let|const)\s/)) {
            this.debug('[Genesis.TextSurgical] Strategy 2: JS Variable assignment');
            extractedString = this._extractJsVariable(trimmed);
            extractionMethod = 'JS Variable';
        }

        // 策略 3: Window 属性赋值
        if (!extractedString && trimmed.includes('window.')) {
            this.debug('[Genesis.TextSurgical] Strategy 3: Window property');
            extractedString = this._extractWindowProperty(trimmed);
            extractionMethod = 'Window Property';
        }

        // 策略 4: 搜索包含 Titan ID 的片段
        if (!extractedString) {
            this.debug('[Genesis.TextSurgical] Strategy 4: Titan ID search');
            extractedString = this._extractByTitanId(trimmed);
            extractionMethod = 'Titan ID Search';
        }

        if (!extractedString) {
            this.warn('[Genesis.TextSurgical] ❌ No extraction strategy succeeded');
            return null;
        }

        // 处理转义字符
        const deescaped = this._processEscapeSequences(extractedString);
        this.info('[Genesis.TextSurgical] ✅ Escape sequences processed');

        // 尝试解析 JSON
        try {
            const jsonData = JSON.parse(deescaped);
            this.info('[Genesis.TextSurgical] ✅ JSON parse success via', extractionMethod);
            return jsonData;
        } catch (e) {
            this.error('[Genesis.TextSurgical] ❌ JSON parse failed:', e.message);
            this.debug('[Genesis.TextSurgical] Extracted string (first 200 chars):', deescaped.substring(0, 200));
            return null;
        }
    }

    /**
     * 策略 1: 提取直接 JSON (从开头到结尾配对括号)
     */
    _extractDirectJson(text) {
        this.debug('[Genesis.TextSurgical] Attempting direct JSON extraction');

        const firstChar = text.charAt(0);
        let openCount = 0;
        let closeIndex = -1;

        for (let i = 0; i < text.length; i++) {
            const char = text.charAt(i);
            if (char === firstChar) {
                openCount++;
            } else if ((firstChar === '{' && char === '}') || (firstChar === '[' && char === ']')) {
                openCount--;
                if (openCount === 0) {
                    closeIndex = i;
                    break;
                }
            }
        }

        if (closeIndex > 0) {
            return text.substring(0, closeIndex + 1);
        }

        return null;
    }

    /**
     * 策略 2: 提取 JavaScript 变量赋值
     * 匹配: var name = {...}; 或 let name = [...];
     */
    _extractJsVariable(text) {
        this.debug('[Genesis.TextSurgical] Attempting JS variable extraction');

        const match = text.match(EXTRACTION_PATTERNS.JS_VARIABLE);
        if (match && match[1]) {
            this.debug('[Genesis.TextSurgical] JS variable pattern matched');
            // 使用配对括号匹配确保完整性
            return this._extractPairedBrackets(match[1]);
        }

        // 尝试更宽松的模式 (允许跨行)
        const looseMatch = text.match(/\b(?:var|let|const)\s+\w+\s*=\s*([\s\S]*?)(?:;|$)/);
        if (looseMatch && looseMatch[1]) {
            this.debug('[Genesis.TextSurgical] Loose JS variable pattern matched');
            return this._extractPairedBrackets(looseMatch[1].trim());
        }

        return null;
    }

    /**
     * 策略 3: 提取 Window 属性赋值
     * 匹配: window.name = {...};
     */
    _extractWindowProperty(text) {
        this.debug('[Genesis.TextSurgical] Attempting window property extraction');

        const match = text.match(EXTRACTION_PATTERNS.WINDOW_PROPERTY);
        if (match && match[1]) {
            this.debug('[Genesis.TextSurgical] Window property pattern matched');
            return this._extractPairedBrackets(match[1]);
        }

        // 尝试更宽松的模式
        const looseMatch = text.match(/window\.\w+\s*=\s*([\s\S]*?)(?:;|$)/);
        if (looseMatch && looseMatch[1]) {
            this.debug('[Genesis.TextSurgical] Loose window property pattern matched');
            return this._extractPairedBrackets(looseMatch[1].trim());
        }

        return null;
    }

    /**
     * 策略 4: 通过 Titan ID 搜索提取
     * 查找包含 "18", "32", "2" 等签名周围的 JSON 对象
     */
    _extractByTitanId(text) {
        this.debug('[Genesis.TextSurgical] Searching for Titan ID signatures');

        for (const titanId of TITAN_ID_SIGNATURES) {
            const patterns = [
                new RegExp(`\\{[^}]*"${titanId}"[^}]*\\}`, 'g'),  // 对象
                new RegExp(`\\[[^\\]]*"${titanId}"[^\\]]*\\]`, 'g')  // 数组
            ];

            for (const pattern of patterns) {
                const matches = text.match(pattern);
                if (matches && matches.length > 0) {
                    this.debug(`[Genesis.TextSurgical] Found Titan ID "${titanId}" in pattern`);
                    return matches[0];
                }
            }
        }

        return null;
    }

    /**
     * 辅助函数: 提取配对括号内的完整内容
     * 处理嵌套对象和数组
     */
    _extractPairedBrackets(text) {
        const firstChar = text.charAt(0);

        if (firstChar !== '{' && firstChar !== '[') {
            return text;  // 不是对象或数组开头，直接返回
        }

        const closeChar = firstChar === '{' ? '}' : ']';
        let openCount = 1;
        let closeIndex = -1;

        for (let i = 1; i < text.length; i++) {
            const char = text.charAt(i);
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
            return text.substring(0, closeIndex + 1);
        }

        return text;  // 无法配对，返回原文本
    }

    /**
     * 处理转义字符序列
     * 支持:
     * - 十六进制: \x22 → "
     * - Unicode: \u0022 → "
     * - 标准转义: \n → newline, \t → tab, etc.
     */
    _processEscapeSequences(text) {
        let processed = text;
        let replacements = 0;

        // 1. 处理十六进制转义 \x22
        processed = processed.replace(EXTRACTION_PATTERNS.HEX_ESCAPE, (match, hex) => {
            replacements++;
            return String.fromCharCode(parseInt(hex, 16));
        });

        // 2. 处理 Unicode 转义 \u0022
        processed = processed.replace(EXTRACTION_PATTERNS.UNICODE_ESCAPE, (match, unicode) => {
            replacements++;
            return String.fromCharCode(parseInt(unicode, 16));
        });

        // 3. 处理标准转义序列
        const escapeMap = {
            'n': '\n',
            'r': '\r',
            't': '\t',
            'b': '\b',
            'f': '\f',
            'v': '\v',
            '"': '"',
            "'": "'",
            '\\': '\\'
        };

        processed = processed.replace(EXTRACTION_PATTERNS.STANDARD_ESCAPE, (match, char) => {
            replacements++;
            return escapeMap[char] || match;
        });

        this.debug('[Genesis.TextSurgical] Escape replacements:', replacements);

        return processed;
    }

    /**
     * [Genesis.TextSurgical] 扩展响应拦截
     * 同时拦截 /match-event/*.dat 和 ajax-user-data
     *
     * V168.001: 返回 cleanup 函数用于资源清理
     */
    async enableAjaxDataIntercept() {
        if (this.isInterceptionEnabled) {
            this.warn('[Genesis.TextSurgical] Ajax intercept already enabled');
            return { cleanup: () => {} };
        }

        this.info('[Genesis.TextSurgical] 🎯 ENABLING AJAX DATA INTERCEPTION');

        // Clear previous captures
        this.capturedResponses = [];
        this.decompressionResults = [];
        this.capturedAjaxData = [];  // V165.1: Clear ajax captures (V169.100: Removed duplicate)

        // V168.001: Store handler for cleanup
        const ajaxResponseHandler = async (response) => {
            const url = response.url();

            // 拦截 /match-event/*.dat URLs (原有逻辑)
            if (url.includes('/match-event/') && url.includes('.dat')) {
                try {
                    const text = await response.text();

                    if (text.length >= this.config.minResponseSize &&
                        text.length <= this.config.maxResponseSize) {
                        this.capturedResponses.push({
                            url,
                            text,
                            size: text.length,
                            timestamp: Date.now(),
                            type: 'match-event'
                        });
                        this.info('[V164.1] ✅ CAPTURED match-event:', url.substring(0, 80));
                    }
                } catch (e) {
                    this.error('[V164.1] Response capture error:', e.message);
                }
            }

            // [NEW] 拦截 ajax-user-data URLs
            if (url.includes('ajax-user-data')) {
                try {
                    const rawText = await response.text();

                    this.capturedAjaxData.push({
                        url,
                        rawText,
                        size: rawText.length,
                        timestamp: Date.now(),
                        type: 'ajax-user-data'
                    });

                    this.info('[Genesis.TextSurgical] ✅ CAPTURED ajax-user-data:', url.substring(0, 80));

                    // 立即尝试提取
                    const extracted = this._extractFromRawJs(rawText);
                    if (extracted) {
                        this.info('[Genesis.TextSurgical] ✅ EXTRACTION SUCCESS');
                        // 存储到解压结果列表
                        this.decompressionResults.push({
                            source: 'ajax-user-data',
                            data: extracted,
                            method: 'TextSurgical'
                        });
                    }
                } catch (e) {
                    this.error('[Genesis.TextSurgical] Ajax capture error:', e.message);
                }
            }
        };

        // Register the listener
        this.page.on('response', ajaxResponseHandler);

        // Initialize browser context
        await this.page.evaluate(() => {
            window._TITAN_ARTERY_DATA = [];
            window._V164_1_FORCE_INTERCEPT = true;
            window._GENESIS_TEXT_SURGICAL = true;  // New flag
        });

        this.isInterceptionEnabled = true;
        this.info('[Genesis.TextSurgical] ✅ AJAX INTERCEPTION ENABLED');

        // V168.001: Return cleanup function
        return {
            cleanup: () => {
                this.page.off('response', ajaxResponseHandler);
                this.info('[V168.001] ✅ Ajax response handler cleaned up');
            }
        };
    }

    /**
     * V164.1: Enable force interception mode
     * This MUST be called BEFORE page.goto()
     *
     * V168.001: 返回 cleanup 函数用于资源清理
     *
     * Sets up page.on('response') handler to intercept /match-event/*.dat URLs
     */
    async enableForceIntercept() {
        if (this.isInterceptionEnabled) {
            this.warn('[V164.1] Force intercept already enabled');
            return { cleanup: () => {} };
        }

        this.info('[V164.1] 🎯 ENABLING FORCE INTERCEPTION MODE');

        // Clear previous captures
        this.capturedResponses = [];
        this.decompressionResults = [];
        this.capturedAjaxData = [];  // V165.1: Clear ajax captures

        // V164.1: Active network interception
        // V168.001: Store handler for cleanup
        const forceResponseHandler = async (response) => {
            const url = response.url();

            // Intercept /match-event/*.dat URLs
            if (url.includes('/match-event/') && url.includes('.dat')) {
                try {
                    const text = await response.text();

                    // Memory overflow protection
                    if (text.length < this.config.minResponseSize ||
                        text.length > this.config.maxResponseSize) {
                        this.debug('[V164.1] Response size out of range:', text.length, 'bytes');
                        return;
                    }

                    // Store captured response
                    this.capturedResponses.push({
                        url,
                        text,
                        size: text.length,
                        timestamp: Date.now()
                    });

                    this.info('[V164.1] ✅ CAPTURED:', url.substring(0, 80), '(' + text.length + ' bytes)');

                } catch (e) {
                    this.error('[V164.1] Response capture error:', e.message);
                }
            }
        };

        // Register the listener
        this.page.on('response', forceResponseHandler);

        // Initialize window._TITAN_ARTERY_DATA in browser context
        await this.page.evaluate(() => {
            window._TITAN_ARTERY_DATA = [];
            window._V164_1_FORCE_INTERCEPT = true;
        });

        this.isInterceptionEnabled = true;
        this.info('[V164.1] ✅ FORCE INTERCEPTION ENABLED - Network listener ACTIVE');

        // V168.001: Return cleanup function
        return {
            cleanup: () => {
                this.page.off('response', forceResponseHandler);
                this.info('[V168.001] ✅ Force intercept response handler cleaned up');
            }
        };
    }

    /**
     * V164.1: Process captured responses (manual decompression)
     * This is called AFTER page navigation completes
     *
     * Decompression pipeline: Base64 → atob() → JXG.decompress → JSON
     */
    async processCapturedResponses() {
        if (!this.isInterceptionEnabled) {
            this.warn('[V164.1] Force intercept not enabled, call enableForceIntercept() first');
            return { success: false, error: 'Interception not enabled' };
        }

        this.info('[V164.1] 🔬 PROCESSING CAPTURED RESPONSES:', this.capturedResponses.length);

        if (this.capturedResponses.length === 0) {
            this.warn('[V164.1] ⚠️  No responses captured');
            return { success: false, captured: 0 };
        }

        let decompressedCount = 0;

        for (const captured of this.capturedResponses) {
            try {
                // Step 1: Base64 decode using atob()
                const decoded = await this.page.evaluate((text) => {
                    try {
                        return window.atob(text);
                    } catch (e) {
                        return null;
                    }
                }, captured.text);

                if (!decoded) {
                    this.warn('[V164.1] Base64 decode failed');
                    continue;
                }

                this.info('[V164.1] ✅ Base64 decoded:', decoded.length, 'bytes');

                // Step 2: Manual JXG.decompress
                const decompressed = await this.page.evaluate((data) => {
                    try {
                        // Check if JXG is available
                        if (typeof window.JXG === 'undefined' || !window.JXG.decompress) {
                            console.error('[V164.1] JXG.decompress not available');
                            return null;
                        }

                        // Force decompress
                        const result = window.JXG.decompress(data);
                        return result;
                    } catch (e) {
                        console.error('[V164.1] JXG.decompress error:', e.message);
                        return null;
                    }
                }, decoded);

                if (!decompressed) {
                    this.warn('[V164.1] JXG decompress failed');
                    continue;
                }

                this.info('[V164.1] ✅ JXG decompressed:', decompressed.length, 'bytes');

                // Step 3: Parse JSON
                const jsonData = await this.page.evaluate((jsonString) => {
                    try {
                        return JSON.parse(jsonString);
                    } catch (e) {
                        return null;
                    }
                }, decompressed);

                if (!jsonData) {
                    this.warn('[V164.1] JSON parse failed');
                    continue;
                }

                // Step 4: Store in window._TITAN_ARTERY_DATA
                const stored = await this.page.evaluate((data, titanIds) => {
                    // Check if data contains Titan ID signatures
                    const dataStr = JSON.stringify(data);
                    const hasTitanSignature = titanIds.some(id => dataStr.includes('"' + id + '"'));

                    if (hasTitanSignature) {
                        window._TITAN_ARTERY_DATA.push({
                            source: 'V164.1_ForceIntercept',
                            timestamp: Date.now(),
                            data: data
                        });
                        return true;
                    }
                    return false;
                }, jsonData, TITAN_ID_SIGNATURES);

                if (stored) {
                    decompressedCount++;
                    this.info('[V164.1] ✅ STORED IN MEMORY - Titan signatures detected');
                }

            } catch (e) {
                this.error('[V164.1] Processing error:', e.message);
            }
        }

        this.info('[V164.1] 📊 DECOMPRESSION SUMMARY:', decompressedCount, '/', this.capturedResponses.length);

        return {
            success: decompressedCount > 0,
            captured: this.capturedResponses.length,
            decompressed: decompressedCount
        };
    }

    /**
     * V164.1: Wait for trajectory signal in memory
     *
     * Polls window._TITAN_ARTERY_DATA for captured data
     * Timeout: 12s (strong intercept window)
     */
    async waitForTrajectorySignal() {
        const startTime = Date.now();
        this.info('[V164.1] 👁️  Waiting for trajectory signal (12s intercept window)...');

        const result = {
            success: false,
            method: 'UNKNOWN',
            capturedData: null,
            elapsedMs: 0
        };

        // V164.1: Polling loop with 100ms interval
        while (Date.now() - startTime < this.config.interceptWindow) {
            const captured = await this.page.evaluate(() => {
                return window._TITAN_ARTERY_DATA || [];
            });

            if (captured.length > 0) {
                this.info('[V164.1] ✅ SIGNAL DETECTED -', captured.length, 'streams in memory');
                result.success = true;
                result.method = 'MEMORY_HOOK';
                result.capturedData = captured;
                result.elapsedMs = Date.now() - startTime;
                return result;
            }

            // Wait before next poll
            await new Promise(resolve => setTimeout(resolve, this.config.pollingInterval));
        }

        // Timeout - try DOM fallback
        this.warn('[V164.1] ⏱️  Memory hook timeout - trying DOM fallback...');
        result.method = 'DOM_FALLBACK';
        result.elapsedMs = Date.now() - startTime;

        return result;
    }

    /**
     * V165.1: Clear captured data from memory
     */
    async clearCapturedData() {
        await this.page.evaluate(() => {
            window._TITAN_ARTERY_DATA = [];
        });
        this.capturedResponses = [];
        this.decompressionResults = [];
        this.capturedAjaxData = [];  // V165.1: Clear ajax captures
        this.info('[V165.1] 🧹 Captured data cleared');
    }

    /**
     * V164.1: Get captured data count
     */
    async getCapturedDataCount() {
        const count = await this.page.evaluate(() => {
            return (window._TITAN_ARTERY_DATA || []).length;
        });
        return count;
    }

    /**
     * V164.1: Legacy DOM fallback scan
     * Used when memory hook fails
     */
    async performDOMFallbackScan() {
        this.info('[V164.1] 🔍 DOM FALLBACK SCAN - Scanning for odds cells...');

        try {
            const cellCount = await this.page.evaluate(() => {
                // Look for odds cells
                const cells = document.querySelectorAll('.odds-cell, .odds-text, [data-odd]');
                return cells.length;
            });

            this.info('[V164.1] ✅ DOM FALLBACK:', cellCount, 'odds cells visible');

            // Try to trigger data load
            await this.page.evaluate(() => {
                const keywords = ['show all', 'more', 'comparison', 'all bookmakers', 'bookmakers'];
                const allElements = Array.from(document.querySelectorAll('a, button, span, li, div[role="tab"]'));

                allElements.forEach(el => {
                    const text = (el.innerText || '').toLowerCase();
                    if (keywords.some(kw => text.includes(kw))) {
                        if (el.offsetParent !== null) {
                            el.click();
                        }
                    }
                });
            });

            await this.page.waitForTimeout(2000);

            return {
                success: cellCount > 0,
                cellCount
            };

        } catch (e) {
            this.error('[V164.1] DOM fallback error:', e.message);
            return { success: false, error: e.message };
        }
    }

    /**
     * V164.1: Legacy compatibility method - injectMemoryHook
     * Maps to enableForceIntercept for backward compatibility
     */
    async injectMemoryHook() {
        this.info('[V164.1] injectMemoryHook() → enableForceIntercept() [Legacy compatibility]');
        return await this.enableForceIntercept();
    }

    /**
     * V164.1: Legacy compatibility method - getCapturedData
     * Returns captured data from memory
     */
    async getCapturedData() {
        const data = await this.page.evaluate(() => {
            return (window._TITAN_ARTERY_DATA || []).map(item => item.data);
        });
        this.info('[V164.1] Retrieved', data.length, 'streams from memory');
        return data;
    }

    /**
     * V164.1: Get hook statistics (legacy compatibility)
     */
    async getHookStats() {
        return await this.page.evaluate(() => ({
            interceptCount: (window._TITAN_ARTERY_DATA || []).length,
            decompressCalls: this.capturedResponses.length,
            forceInterceptEnabled: window._V164_1_FORCE_INTERCEPT || false
        }));
    }

    /**
     * V164.1: Legacy compatibility - waitForOddsContent
     * @deprecated Use waitForTrajectorySignal() instead
     */
    async waitForOddsContent(maxAttempts = 30) {
        const result = await this.waitForTrajectorySignal();
        return result.success;
    }

    /**
     * V166.000: [Genesis.FinalWall] Enable Trigger Mode
     * ===============================================
     * 发令枪模式：网络拦截仅作为"到货通知"，触发 DOM 语义收割
     *
     * 工作流程:
     * 1. 启用网络拦截，监听 /match-event/*.dat
     * 2. 一旦拦截到响应（无需解密），立即触发 DOM 语义提取
     * 3. 等待最大 15 秒的渲染窗口
     * 4. 返回触发结果（包含 cleanup 函数）
     *
     * @param {Object} surgicalInteraction - SurgicalInteraction 实例
     * @param {Object} options - 配置选项
     * @param {number} options.renderWindow - 渲染等待窗口 (ms, default: 15000)
     * @param {boolean} options.enableTrajectoryCapture - 是否捕获轨迹数据 (default: true)
     * @returns {Promise<Object>} 触发结果 {success, method, extractedData, cleanup}
     */
    /**
     * V169.300 [Genesis.FallbackRevolution] 双模提取模式
     * =====================================================
     *
     * 核心改进:
     * - 快速降级: 20秒内未捕获 match-event 立即触发 DOM fallback
     * - 不再死等完整的 renderWindow
     * - DOM fallback 模式直接从页面提取 Opening/Closing 数据
     *
     * @param {SurgicalInteraction} surgicalInteraction - 外科手术式交互服务
     * @param {Object} options - 配置选项
     * @param {number} options.renderWindow - 渲染等待窗口 (ms, default: 15000)
     * @param {boolean} options.enableTrajectoryCapture - 是否捕获轨迹数据 (default: true)
     * @param {number} options.fallbackTimeout - 快速降级超时 (ms, default: 20000)
     * @returns {Promise<Object>} 触发结果 {success, method, extractedData, cleanup}
     */
    async enableTriggerMode(surgicalInteraction, options = {}) {
        const config = {
            renderWindow: options.renderWindow || 15000,
            enableTrajectoryCapture: options.enableTrajectoryCapture !== false,
            fallbackTimeout: options.fallbackTimeout || 20000, // V169.300: 快速降级超时
            ...options
        };

        this.info('[V169.300] [Genesis.FallbackRevolution] 🎯 DUAL-MODE EXTRACTION ENABLED');
        this.info('[V169.300] Network interception → 20s fallback → DOM semantic extraction');
        this.info('[V169.300] Fallback timeout:', config.fallbackTimeout, 'ms, Render window:', config.renderWindow, 'ms');

        // Step 1: Enable network interception (as delivery notification)
        let matchEventCaptured = false;
        let captureUrl = null;

        // V168.001: Store response handler for cleanup
        const responseHandler = async (response) => {
            const url = response.url();

            // Intercept /match-event/*.dat URLs
            if (url.includes('/match-event/') && url.includes('.dat') && !url.includes('postmatch')) {
                try {
                    const text = await response.text();

                    // Size validation (basic check)
                    if (text.length >= this.config.minResponseSize &&
                        text.length <= this.config.maxResponseSize) {
                        matchEventCaptured = true;
                        captureUrl = url;

                        this.info('[V169.300] 📬 DELIVERY NOTIFICATION:', url.substring(0, 80));
                        this.info('[V169.300] Data size:', text.length, 'bytes (no decryption needed)');
                    }
                } catch (e) {
                    this.error('[V169.300] Response capture error:', e.message);
                }
            }
        };

        // Register the listener
        this.page.on('response', responseHandler);

        // Step 2: V169.300 快速降级策略 - 20秒内未捕获立即触发 DOM fallback
        const startTime = Date.now();
        const quickFallbackTimeout = config.fallbackTimeout;

        this.info('[V169.300] Waiting for match-event delivery (', quickFallbackTimeout, 'ms fallback )...');

        while (!matchEventCaptured && (Date.now() - startTime < quickFallbackTimeout)) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        // V169.300: 快速降级逻辑 - 如果 20 秒内未捕获，直接触发 DOM fallback
        if (!matchEventCaptured) {
            this.warn('[V169.300] ⚡ FAST FALLBACK - No match-event in', quickFallbackTimeout, 'ms, activating DOM scraping mode');

            // Cleanup listener before fallback
            this.page.off('response', responseHandler);

            // Step 3: V169.300 DOM Fallback - 直接从页面提取数据
            this.info('[V169.300] 🔧 DOM SCRAPE FALLBACK - Extracting static odds from page table');

            try {
                // 等待页面渲染完成
                await new Promise(resolve => setTimeout(resolve, 3000));

                // 使用 SurgicalInteraction 的 DOM 提取能力
                const extractResult = await surgicalInteraction.harvestBySemanticPatterns({
                    enableTrajectoryCapture: false, // Fallback 模式不需要轨迹
                    titanIdSignatures: TITAN_ID_SIGNATURES,
                    maxWaitTime: 10000,
                    forceDOMExtraction: true, // V169.300: 强制 DOM 提取
                    matchId: config.matchId // [V169.600] Pass matchId
                });

                this.info('[V169.300] 📊 DOM fallback extraction result:', extractResult.success ? 'SUCCESS' : 'FAILED');

                return {
                    success: extractResult.success,
                    method: 'DOM_SCRAPE_FALLBACK',
                    extractedData: extractResult.data,
                    providerCount: extractResult.providerCount,
                    trajectoryCount: 0, // Fallback 模式无轨迹
                    renderWindowElapsed: Date.now() - startTime,
                    fallback: true,
                    cleanup: () => this.page.off('response', responseHandler)
                };
            } catch (fallbackError) {
                this.error('[V169.300] ❌ DOM fallback failed:', fallbackError.message);
                return {
                    success: false,
                    method: 'DOM_SCRAPE_FALLBACK',
                    error: fallbackError.message,
                    renderWindowElapsed: Date.now() - startTime,
                    fallback: true,
                    cleanup: () => this.page.off('response', responseHandler)
                };
            }
        }

        this.info('[V169.300] ✅ MATCH-EVENT CAPTURED - Triggering DOM semantic extraction...');

        // Step 4: Wait for page rendering (with buffer)
        this.info('[V169.300] ⏳ Waiting for page rendering (15s window)...');
        await new Promise(resolve => setTimeout(resolve, 2000)); // Initial buffer

        // Step 5: Trigger semantic extraction
        const extractResult = await surgicalInteraction.harvestBySemanticPatterns({
            enableTrajectoryCapture: config.enableTrajectoryCapture,
            titanIdSignatures: TITAN_ID_SIGNATURES,
            maxWaitTime: config.renderWindow - 2000, // Remaining time
            matchId: config.matchId // [V169.600] Pass matchId
        });

        this.info('[V169.300] 📊 Semantic extraction result:', extractResult.success ? 'SUCCESS' : 'FAILED');

        // V168.001: Cleanup listener after extraction
        this.page.off('response', responseHandler);

        return {
            success: extractResult.success,
            method: 'SEMANTIC_DOM_EXTRACTION',
            extractedData: extractResult.data,
            providerCount: extractResult.providerCount,
            trajectoryCount: extractResult.trajectoryCount,
            renderWindowElapsed: Date.now() - startTime,
            fallback: false,
            cleanup: () => this.page.off('response', responseHandler)
        };
    }

    /**
     * V166.000: [Genesis.FinalWall] Quick Trigger Check
     * ============================================
     * 快速检查是否已捕获 match-event（用于轮询模式）
     *
     * @returns {Promise<boolean>} 是否已捕获 match-event
     */
    async hasMatchEventCaptured() {
        return await this.page.evaluate(() => {
            return window._V166_0_MATCH_EVENT_CAPTURERED || false;
        });
    }

    /**
     * V165.1: Shutdown cleanup
     */
    async shutdown() {
        this.info('[V165.1] 🔌 Shutting down SignalRadar...');
        this.isInterceptionEnabled = false;
        this.capturedResponses = [];
        this.decompressionResults = [];
        this.capturedAjaxData = [];  // Clear ajax captures
    }
}

module.exports = { SignalRadar };
