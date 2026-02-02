/**
 * NetworkInterceptor - V168.002 Network Interception Module
 * =====================================================
 *
 * [Genesis.Architect] 网络拦截器 - 从 SignalRadar.js 提取
 *
 * 负责管理 Playwright page.on('response') 监听器，
 * 支持三种拦截模式：Ajax、Force、Trigger。
 *
 * @module services/intercept/NetworkInterceptor
 * @version V168.002
 * @since 2026-02-02
 * @author [Genesis.Architect]
 */

'use strict';

const { RadarLogger } = require('../logging/RadarLogger');

/**
 * V168.002: 响应缓冲区管理
 */
class ResponseBuffer {
    constructor() {
        this.responses = [];
        this.ajaxData = [];
        this.decompressionResults = [];
    }

    addResponse(response) {
        this.responses.push(response);
    }

    addAjaxData(data) {
        this.ajaxData.push(data);
    }

    addDecompressionResult(result) {
        this.decompressionResults.push(result);
    }

    getCapturedResponses() {
        return this.responses;
    }

    getCapturedAjaxData() {
        return this.ajaxData;
    }

    getDecompressionResults() {
        return this.decompressionResults;
    }

    getCount() {
        return {
            responses: this.responses.length,
            ajax: this.ajaxData.length,
            decompression: this.decompressionResults.length
        };
    }

    clear() {
        this.responses = [];
        this.ajaxData = [];
        this.decompressionResults = [];
    }
}

/**
 * V168.002: 网络拦截器
 *
 * 负责管理 Playwright page.on('response') 监听器
 */
class NetworkInterceptor {
    /**
     * 创建拦截器实例
     * @param {Page} page - Playwright page 对象
     * @param {Object} options - 配置选项
     */
    constructor(page, options = {}) {
        this.page = page;
        this.logger = new RadarLogger({ prefix: '[NetworkInterceptor]' });
        this.buffer = new ResponseBuffer();
        this.isInterceptionEnabled = false;

        // 配置
        this.config = {
            maxResponseSize: options.maxResponseSize || (200 * 1024),  // 200KB
            minResponseSize: options.minResponseSize || 100,
            pollingInterval: options.pollingInterval || 100,
            interceptWindow: options.interceptWindow || 12000,
            matchEventPattern: options.matchEventPattern || '/match-event/',
            matchAjaxPattern: options.matchAjaxPattern || 'ajax-user-data'
        };
    }

    /**
     * V164.1: Enable force interception mode
     * MUST be called BEFORE page.goto()
     *
     * @returns {Object} 返回 cleanup 函数
     */
    enableForceIntercept() {
        if (this.isInterceptionEnabled) {
            this.logger.warn('Force intercept already enabled');
            return { cleanup: () => {} };
        }

        this.logger.info('🎯 ENABLING FORCE INTERCEPTION MODE');
        this.buffer.clear();

        // V168.001: Store handler for cleanup
        const forceResponseHandler = async (response) => {
            const url = response.url();

            // Intercept /match-event/*.dat URLs
            if (url.includes(this.config.matchEventPattern) && url.includes('.dat')) {
                try {
                    const text = await response.text();

                    // Memory overflow protection
                    if (text.length >= this.config.minResponseSize &&
                        text.length <= this.config.maxResponseSize) {
                        this.buffer.addResponse({
                            url,
                            text,
                            size: text.length,
                            timestamp: Date.now()
                        });

                        this.logger.info(`✅ CAPTURED: ${url.substring(0, 80)} (${text.length} bytes)`);
                    }
                } catch (e) {
                    this.logger.error(`Response capture error: ${e.message}`);
                }
            }
        };

        // Register the listener
        this.page.on('response', forceResponseHandler);
        this.isInterceptionEnabled = true;

        this.logger.info('✅ FORCE INTERCEPTION ENABLED - Network listener ACTIVE');

        // V168.001: Return cleanup function
        return {
            cleanup: () => {
                this.page.off('response', forceResponseHandler);
                this.logger.info('✅ Force intercept response handler cleaned up');
            }
        };
    }

    /**
     * [Genesis.TextSurgical] Enable extended response interception
     * 同时拦截 /match-event/*.dat 和 ajax-user-data
     *
     * @returns {Object} 返回 cleanup 函数
     */
    enableAjaxDataIntercept() {
        if (this.isInterceptionEnabled) {
            this.logger.warn('Ajax intercept already enabled');
            return { cleanup: () => {} };
        }

        this.logger.info('🎯 ENABLING AJAX DATA INTERCEPTION');
        this.buffer.clear();

        // V168.001: Store handler for cleanup
        const ajaxResponseHandler = async (response) => {
            const url = response.url();

            // 拦截 /match-event/*.dat URLs (原有逻辑)
            if (url.includes(this.config.matchEventPattern) && url.includes('.dat')) {
                try {
                    const text = await response.text();

                    if (text.length >= this.config.minResponseSize &&
                        text.length <= this.config.maxResponseSize) {
                        this.buffer.addResponse({
                            url,
                            text,
                            size: text.length,
                            timestamp: Date.now(),
                            type: 'match-event'
                        });

                        this.logger.info(`✅ CAPTURED match-event: ${url.substring(0, 80)}`);
                    }
                } catch (e) {
                    this.logger.error(`Response capture error: ${e.message}`);
                }
            }

            // [NEW] 拦截 ajax-user-data URLs
            if (url.includes(this.config.matchAjaxPattern)) {
                try {
                    const rawText = await response.text();

                    this.buffer.addAjaxData({
                        url,
                        rawText,
                        size: rawText.length,
                        timestamp: Date.now(),
                        type: 'ajax-user-data'
                    });

                    this.logger.info(`✅ CAPTURED ajax-user-data: ${url.substring(0, 80)}`);
                } catch (e) {
                    this.logger.error(`Ajax capture error: ${e.message}`);
                }
            }
        };

        // Register the listener
        this.page.on('response', ajaxResponseHandler);

        // Initialize browser context
        this.page.evaluate(() => {
            window._TITAN_ARTERY_DATA = [];
            window._V164_1_FORCE_INTERCEPT = true;
            window._GENESIS_TEXT_SURGICAL = true;
        }).catch(() => {});

        this.isInterceptionEnabled = true;
        this.logger.info('✅ AJAX INTERCEPTION ENABLED');

        // V168.001: Return cleanup function
        return {
            cleanup: () => {
                this.page.off('response', ajaxResponseHandler);
                this.logger.info('✅ Ajax response handler cleaned up');
            }
        };
    }

    /**
     * 获取捕获的数据
     */
    getCapturedData() {
        return {
            responses: this.buffer.getCapturedResponses(),
            ajaxData: this.buffer.getCapturedAjaxData(),
            decompression: this.buffer.getDecompressionResults()
        };
    }

    /**
     * 获取捕获数据统计
     */
    getCapturedDataCount() {
        return this.buffer.getCount();
    }

    /**
     * 清空缓冲区
     */
    clear() {
        this.buffer.clear();
        this.logger.info('Response buffer cleared');
    }

    /**
     * 关闭拦截器
     */
    shutdown() {
        if (this.isInterceptionEnabled) {
            this.logger.info('Shutting down network interceptor');
            // Note: cleanup should be called via the returned cleanup function
            this.isInterceptionEnabled = false;
        }
        this.buffer.clear();
    }
}

module.exports = { NetworkInterceptor, ResponseBuffer };
