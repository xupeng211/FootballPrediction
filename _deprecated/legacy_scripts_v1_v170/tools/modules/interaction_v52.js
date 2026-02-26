/**
 * V87.500 Interaction Module - Vue.js Event Injection Protocol
 * ================================================================
 *
 * 核心功能：
 *   - 弃用传统 .click() 方法
 *   - 像素偏移网格点击：3x3 矩阵采样
 *   - Vue.js 事件穿透：内存级事件注入
 *   - 状态轮询：waitForFunction 监测弹窗
 *
 * V87.202 增强：
 *   - 修正 A: page.evaluate 参数封装
 *   - 逻辑增强: Escape + scroll 重试机制
 *   - 金丝雀自检: DOM dump 保存功能
 *
 * V87.300 增强：
 *   - OneTrust Cookie Consent 检测与移除
 *   - 强制穿透点击策略
 *   - 双策略移除机制（Accept 优先，Force 备选）
 *
 * V87.500 增强：
 *   - Vue.js 事件穿透：composed: true (穿透 Shadow DOM)
 *   - 状态轮询：waitForFunction 替代固定延迟
 *   - 自动熔断：连续 3 场 0 记录自动重启 Context
 *
 * @module interaction_v52
 * @version V87.500
 * @since 2026-01-26
 */

'use strict';

const logger = require('./logger');
const log = logger.createLogger('interaction_v52');
const fs = require('fs');
const path = require('path');

// ============================================================================
// CONFIGURATION
// ============================================================================

const V52_CONFIG = {
    // 像素矩阵配置
    matrixSize: 3,              // 3x3 矩阵
    pixelOffset: 5,             // 中心点周边 5 像素范围

    // 坐标计算配置
    boundingBoxPadding: 10,     // 边界框内边距
    minClickArea: 10,           // 最小点击区域 (像素)
    maxRetries: 9,              // 最大重试次数 (3x3 矩阵)

    // Trusted Event 配置
    trustedEvents: true,        // 启用 Trusted Event 模拟
    eventSequence: [
        'mouseover',
        'mouseenter',
        'mousemove',
        'mousedown',
        'mouseup',
        'click'
    ],

    // 坐标校准配置
    coordinateCalibration: {
        enabled: true,
        scrollIntoView: true,
        viewportCheck: true,
        elementStabilityCheck: true,
        stabilityWaitTime: 100   // 等待元素稳定的毫秒数
    },

    // V87.202: 逻辑增强配置
    retryMechanism: {
        enabled: true,
        escapeKey: true,         // 触发 Escape 清理遮罩
        scrollOffset: 100,       // 滚动像素
        waitAfterScroll: 500     // 滚动后等待时间
    },

    // V87.202: 金丝雀自检配置
    canaryCheck: {
        enabled: true,
        dumpOnFailure: true,     // 失败时保存 DOM dump
        dumpDir: path.join(__dirname, '../../logs/debug')
    },

    // V87.300: OneTrust Cookie Consent 处理配置
    oneTrustHandling: {
        enabled: true,              // 启用 OneTrust 检测与移除
        waitForBanner: 3000,        // 等待横幅出现的最长时间
        strategy: 'accept_first',   // 策略: 'accept_first' | 'force_remove'
        removeOverlay: true,        // 强制移除遮罩层
        disableStyles: true         // 禁用 OneTrust 样式标签
    },

    // V87.500: 自动熔断配置（针对 9900X 高并发环境）
    autoCircuitBreaker: {
        enabled: true,              // 启用自动熔断
        emptyRecordThreshold: 3,    // 连续 3 场 0 记录触发熔断
        maxRetryAttempts: 1,        // 最大重试次数
        cooldownTime: 5000,         // 熔断后的冷却时间（ms）
        autoReloadContext: true     // 自动重新加载 Context
    },

    // V87.500: Vue.js 事件注入配置
    eventInjection: {
        enabled: true,              // 启用事件注入协议
        composed: true,             // 穿透 Shadow DOM
        bubbles: true,              // 事件冒泡
        cancelable: true,           // 可取消
        vueEventNamespace: ['odds-click', 'modal-open', 'popup-show'],  // Vue.js 事件命名空间
        maxEventRetries: 3          // 事件注入最大重试次数
    },

    // V87.500: 状态轮询配置
    statePolling: {
        enabled: true,              // 启用状态轮询
        pollInterval: 100,          // 轮询间隔（ms）
        maxPollTime: 5000,           // 最大轮询时间（ms）
        modalSelectors: [           // 弹窗选择器
            '.modal',
            '.popup',
            '.dialog',
            '[role="dialog"]',
            '.vue-modal',
            '.odds-modal',
            '[data-v-*][class*="modal"]'
        ]
    },

    // 调试模式
    debug: false,
    logClickCoordinates: true,
    exportClickTrace: false
};

// ============================================================================
// PIXEL MATRIX CLICKER CLASS
// ============================================================================

class PixelMatrixClicker {
    constructor(page, config = {}) {
        this.page = page;
        this.config = { ...V52_CONFIG, ...config };
        this.clickTrace = [];
        this.retryAttempted = false;  // V87.202: 标记是否已执行重试

        // V87.500: 自动熔断状态
        this.emptyRecordCount = 0;
        this.totalRecordsProcessed = 0;
        this.circuitBreakerTripped = false;
        this.lastCircuitBreakTime = 0;
    }

    /**
     * 步骤 B: 执行像素偏移网格点击
     *
     * @param {ElementHandle} element - 目标元素
     * @param {Object} [options={}] - 配置选项
     * @returns {Promise<{success: boolean, attempts: number, finalCoords: Object, method: string}>}
     */
    async executeMatrixClick(element, options = {}) {
        const finalOptions = { ...this.config, ...options };
        this.retryAttempted = false;  // 重置重试标记

        log.info('[步骤 B] === 像素偏移网格点击启动 ===');
        log.debug(`矩阵大小: ${finalOptions.matrixSize}x${finalOptions.matrixSize}`);
        log.debug(`像素偏移: ±${finalOptions.pixelOffset}px`);

        // V87.300: OneTrust Cookie Consent 检测与移除
        if (finalOptions.oneTrustHandling?.enabled) {
            const oneTrustResult = await this._handleOneTrustConsent();
            if (!oneTrustResult.success) {
                log.warn('[V87.300] OneTrust 处理失败，继续执行矩阵点击');
            }
        }

        // B.1: 坐标校准与预处理
        const calibrationResult = await this._calibrateCoordinates(element, finalOptions);
        if (!calibrationResult.success) {
            // V87.202: 金丝雀自检 - 失败时保存 DOM dump
            if (finalOptions.canaryCheck?.enabled && finalOptions.canaryCheck?.dumpOnFailure) {
                await this._dumpDomForDebug('calibration_failed');
            }

            return {
                success: false,
                attempts: 0,
                finalCoords: null,
                method: 'calibration_failed',
                error: calibrationResult.error
            };
        }

        const baseBox = calibrationResult.boundingBox;

        // B.2: 生成 3x3 矩阵坐标
        const clickCoordinates = this._generateMatrixCoordinates(
            baseBox,
            finalOptions.matrixSize,
            finalOptions.pixelOffset
        );

        log.debug(`生成 ${clickCoordinates.length} 个点击坐标`);

        // B.3: 执行矩阵点击序列
        for (let i = 0; i < clickCoordinates.length; i++) {
            const coords = clickCoordinates[i];

            try {
                log.debug(`[尝试 ${i + 1}/${clickCoordinates.length}] 坐标: (${coords.x}, ${coords.y})`);

                // B.4: 注入 Trusted Event
                const clickResult = await this._injectTrustedClickSequence(
                    element,
                    coords,
                    finalOptions
                );

                // 记录点击轨迹
                this._recordClickTrace(coords, clickResult);

                if (clickResult.success) {
                    log.success(`[步骤 B] 矩阵点击成功 (尝试 ${i + 1}, 坐标: ${coords.x}, ${coords.y})`);

                    // B.5: 验证交互效果
                    const validationResult = await this._validateInteraction(element, finalOptions);

                    // V87.202: 检查 New Layers Count
                    const newLayersCount = validationResult.success ? 1 : 0;

                    if (newLayersCount > 0) {
                        return {
                            success: true,
                            attempts: i + 1,
                            finalCoords: coords,
                            method: `matrix_click_${i}`,
                            validation: validationResult,
                            newLayersCount: newLayersCount,
                            clickTrace: this.clickTrace
                        };
                    } else {
                        log.debug(`[步骤 B] 点击成功但未检测到新层 (尝试 ${i + 1})`);
                    }
                }

            } catch (error) {
                log.debug(`[尝试 ${i + 1}] 失败: ${error.message}`);
            }

            // 点击间短暂延迟
            await this.page.waitForTimeout(50);
        }

        // V87.202 逻辑增强: 所有矩阵点击尝试均失败或 New Layers Count = 0
        if (finalOptions.retryMechanism?.enabled && !this.retryAttempted) {
            log.warn('[步骤 B] 所有矩阵点击尝试均未产生新层，触发 Escape + scroll 重试...');

            this.retryAttempted = true;

            // 执行 Escape + scroll 重试
            const retryResult = await this._executeEscapeScrollRetry(element, baseBox, finalOptions);

            if (retryResult.success) {
                return retryResult;
            }
        }

        log.warn('[步骤 B] 所有矩阵点击尝试均失败');

        // V87.202: 金丝雀自检 - 失败时保存 DOM dump
        if (finalOptions.canaryCheck?.enabled && finalOptions.canaryCheck?.dumpOnFailure) {
            await this._dumpDomForDebug('matrix_click_failed');
        }

        return {
            success: false,
            attempts: clickCoordinates.length,
            finalCoords: null,
            method: 'matrix_click_failed',
            newLayersCount: 0,
            clickTrace: this.clickTrace
        };
    }

    /**
     * V87.202: Escape + scroll 重试机制
     * @private
     */
    async _executeEscapeScrollRetry(element, baseBox, config) {
        try {
            const retryConfig = config.retryMechanism;

            // 1. 触发 Escape 键（清理可能的遮罩）
            if (retryConfig.escapeKey) {
                log.debug('[重试] 按 Escape 键清理遮罩...');
                await this.page.keyboard.press('Escape');
                await this.page.waitForTimeout(200);
            }

            // 2. 执行页面滚动
            log.debug(`[重试] 滚动页面 ${retryConfig.scrollOffset}px...`);
            await this.page.evaluate((params) => {
                window.scrollBy(0, params.offset);
            }, { offset: retryConfig.scrollOffset });

            // 3. 等待滚动完成
            await this.page.waitForTimeout(retryConfig.waitAfterScroll);

            // 4. 重新校准坐标（元素位置可能已变化）
            const recalibrationResult = await this._calibrateCoordinates(element, config);
            if (!recalibrationResult.success) {
                log.warn('[重试] 重新校准失败');
                return { success: false };
            }

            // 5. 生成新的点击坐标（使用中心点）
            const newBox = recalibrationResult.boundingBox;
            const centerX = newBox.x + newBox.width / 2;
            const centerY = newBox.y + newBox.height / 2;

            log.debug(`[重试] 新坐标: (${centerX}, ${centerY})`);

            // 6. 执行单次点击
            const clickResult = await this._injectTrustedClickSequence(
                element,
                { x: centerX, y: centerY },
                config
            );

            // 7. 验证交互效果
            if (clickResult.success) {
                const validationResult = await this._validateInteraction(element, config);

                if (validationResult.success) {
                    log.success('[重试] Escape + scroll 重试成功!');
                    return {
                        success: true,
                        attempts: this.clickTrace.length + 1,
                        finalCoords: { x: centerX, y: centerY },
                        method: 'escape_scroll_retry',
                        validation: validationResult,
                        newLayersCount: 1,
                        clickTrace: this.clickTrace
                    };
                }
            }

            log.warn('[重试] Escape + scroll 重试未产生新层');
            return { success: false };

        } catch (error) {
            log.error(`[重试] Escape + scroll 重试异常: ${error.message}`);
            return { success: false };
        }
    }

    /**
     * V87.202: DOM dump 保存功能（用于调试）
     * @private
     */
    async _dumpDomForDebug(reason) {
        try {
            const dumpDir = this.config.canaryCheck.dumpDir;

            // 确保目录存在
            if (!fs.existsSync(dumpDir)) {
                fs.mkdirSync(dumpDir, { recursive: true });
            }

            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const filename = `dom_dump_${reason}_${timestamp}.html`;
            const filepath = path.join(dumpDir, filename);

            // 获取完整 HTML
            const htmlContent = await this.page.content();
            fs.writeFileSync(filepath, htmlContent, 'utf8');

            log.info(`[金丝雀自检] DOM dump 已保存: ${filepath}`);

        } catch (error) {
            log.error(`[金丝雀自检] DOM dump 保存失败: ${error.message}`);
        }
    }

    /**
     * B.1: 坐标校准与预处理
     * @private
     */
    async _calibrateCoordinates(element, config) {
        log.debug('[B.1] 坐标校准启动...');

        try {
            // 1. 滚动到视图
            if (config.coordinateCalibration.scrollIntoView) {
                await element.scrollIntoViewIfNeeded({ block: 'center' });
                await this.page.waitForTimeout(config.coordinateCalibration.stabilityWaitTime);
            }

            // 2. 获取边界框
            const box = await element.boundingBox();
            if (!box) {
                return {
                    success: false,
                    error: '无法获取元素边界框'
                };
            }

            // 3. 验证边界框有效性
            if (box.width < config.minClickArea || box.height < config.minClickArea) {
                return {
                    success: false,
                    error: `元素过小: ${box.width}x${box.height}`
                };
            }

            // 4. 视口检查
            // V87.202 修正 A: 参数封装为单个对象
            if (config.coordinateCalibration.viewportCheck) {
                const viewportCheck = await this.page.evaluate((params) => {
                    const { box } = params;
                    return (
                        box.x >= 0 &&
                        box.y >= 0 &&
                        box.x + box.width <= window.innerWidth &&
                        box.y + box.height <= window.innerHeight
                    );
                }, { box });

                if (!viewportCheck) {
                    log.warn('[B.1] 元素不在可视区域内，可能影响点击效果');
                }
            }

            // 5. 元素稳定性检查
            if (config.coordinateCalibration.elementStabilityCheck) {
                const stable = await this._checkElementStability(element, box);
                if (!stable) {
                    log.warn('[B.1] 元素位置不稳定');
                }
            }

            log.debug(`[B.1] 坐标校准完成: ${JSON.stringify(box)}`);

            return {
                success: true,
                boundingBox: {
                    x: box.x + config.boundingBoxPadding,
                    y: box.y + config.boundingBoxPadding,
                    width: box.width - 2 * config.boundingBoxPadding,
                    height: box.height - 2 * config.boundingBoxPadding
                }
            };

        } catch (error) {
            return {
                success: false,
                error: `坐标校准失败: ${error.message}`
            };
        }
    }

    /**
     * 检查元素稳定性
     * @private
     */
    async _checkElementStability(element, box) {
        try {
            const startTime = Date.now();
            const sampleCount = 3;
            const positions = [];

            for (let i = 0; i < sampleCount; i++) {
                const currentBox = await element.boundingBox();
                positions.push({
                    x: currentBox.x,
                    y: currentBox.y,
                    timestamp: Date.now()
                });
                await this.page.waitForTimeout(50);
            }

            // 检查位置变化
            const maxDelta = 2; // 最大允许 2 像素偏移
            for (let i = 1; i < positions.length; i++) {
                const deltaX = Math.abs(positions[i].x - positions[0].x);
                const deltaY = Math.abs(positions[i].y - positions[0].y);

                if (deltaX > maxDelta || deltaY > maxDelta) {
                    return false;
                }
            }

            return true;

        } catch (error) {
            return false;
        }
    }

    /**
     * B.2: 生成 3x3 矩阵坐标
     * @private
     */
    _generateMatrixCoordinates(boundingBox, matrixSize, pixelOffset) {
        const coordinates = [];

        // 计算中心点
        const centerX = boundingBox.x + boundingBox.width / 2;
        const centerY = boundingBox.y + boundingBox.height / 2;

        // V88.100 修复: 计算边界偏移的最大安全值
        const maxOffsetX = Math.min(pixelOffset, boundingBox.width / 3);
        const maxOffsetY = Math.min(pixelOffset, boundingBox.height / 3);

        // 使用安全的偏移步长
        const offsetStepX = Math.floor(maxOffsetX / 2);
        const offsetStepY = Math.floor(maxOffsetY / 2);

        // 生成矩阵偏移
        const offsets = [];

        for (let row = 0; row < matrixSize; row++) {
            for (let col = 0; col < matrixSize; col++) {
                // 计算相对偏移（使用不同的步长）
                const relX = (col - 1) * offsetStepX;
                const relY = (row - 1) * offsetStepY;

                offsets.push({ x: relX, y: relY });
            }
        }

        // 按距离中心点排序（最近优先）
        offsets.sort((a, b) => {
            const distA = Math.sqrt(a.x * a.x + a.y * a.y);
            const distB = Math.sqrt(b.x * b.x + b.y * b.y);
            return distA - distB;
        });

        // 生成绝对坐标（确保在边界内）
        offsets.forEach(offset => {
            let x = Math.round(centerX + offset.x);
            let y = Math.round(centerY + offset.y);

            // V88.100: 确保坐标不会超出 boundingBox 范围
            x = Math.max(boundingBox.x, Math.min(boundingBox.x + boundingBox.width, x));
            y = Math.max(boundingBox.y, Math.min(boundingBox.y + boundingBox.height, y));

            coordinates.push({
                x: x,
                y: y,
                offsetX: offset.x,
                offsetY: offset.y
            });
        });

        return coordinates;
    }

    /**
     * B.4: 注入 Trusted Event 序列
     * @private
     */
    async _injectTrustedClickSequence(element, coords, config) {
        if (config.trustedEvents) {
            return await this._injectPageLevelTrustedEvents(coords, config);
        } else {
            return await this._usePlaywrightClick(element, coords);
        }
    }

    /**
     * V87.500: 页面级 Vue.js 事件注入（内存级事件穿透）
     * @private
     */
    async _injectPageLevelTrustedEvents(coords, config) {
        const eventSequence = config.eventSequence;
        const timestamp = Date.now();
        const eventInjection = config.eventInjection || {};

        log.debug(`[V87.500] 执行 Vue.js 事件注入协议 (composed: ${eventInjection.composed})`);

        // V87.500: 增强的事件注入脚本
        const injectScript = (params) => {
            const { x, y, events, ts, injectionConfig } = params;
            const results = [];
            let target = document.elementFromPoint(x, y);

            if (!target) {
                return { success: false, error: 'no_target_at_coords', x, y };
            }

            // 尝试找到真正的可交互元素（向上遍历 5 层）
            let interactiveTarget = target;
            let depth = 0;
            while (depth < 5 && interactiveTarget) {
                const style = window.getComputedStyle(interactiveTarget);
                if (style.cursor === 'pointer' || interactiveTarget.tagName === 'BUTTON' || interactiveTarget.tagName === 'A') {
                    break;
                }
                interactiveTarget = interactiveTarget.parentElement;
                depth++;
            }

            if (!interactiveTarget) {
                interactiveTarget = target;
            }

            const targetInfo = {
                tagName: interactiveTarget.tagName,
                id: interactiveTarget.id || '',
                className: interactiveTarget.className || '',
                depth: depth
            };

            // V87.500: 事件注入循环
            for (const eventType of events) {
                try {
                    // A. 创建标准 MouseEvent（V87.500: 添加 composed: true）
                    const mouseEvent = new MouseEvent(eventType, {
                        bubbles: injectionConfig.bubbles !== false,
                        cancelable: injectionConfig.cancelable !== false,
                        composed: injectionConfig.composed === true,  // V87.500: 穿透 Shadow DOM
                        view: window,
                        detail: 1,
                        screenX: x,
                        screenY: y,
                        clientX: x,
                        clientY: y,
                        button: 0,
                        buttons: 1,
                        relatedTarget: null,
                        isTrusted: true,
                        timeStamp: ts + events.indexOf(eventType)
                    });

                    // 分发标准事件
                    const mouseDispatched = interactiveTarget.dispatchEvent(mouseEvent);
                    results.push({
                        type: `mouse_${eventType}`,
                        dispatched: mouseDispatched,
                        method: 'MouseEvent'
                    });

                    // B. V87.500: Vue.js 事件命名空间注入
                    if (injectionConfig.vueEventNamespace && injectionConfig.vueEventNamespace.length > 0) {
                        for (const vueEventName of injectionConfig.vueEventNamespace) {
                            try {
                                const vueEvent = new CustomEvent(vueEventName, {
                                    bubbles: injectionConfig.bubbles !== false,
                                    cancelable: injectionConfig.cancelable !== false,
                                    composed: injectionConfig.composed === true,
                                    detail: {
                                        x: x,
                                        y: y,
                                        originalEvent: eventType,
                                        timestamp: ts
                                    }
                                });

                                const vueDispatched = interactiveTarget.dispatchEvent(vueEvent);
                                results.push({
                                    type: `vue_${vueEventName}`,
                                    dispatched: vueDispatched,
                                    method: 'CustomEvent'
                                });

                                if (vueDispatched) {
                                    log.debug(`[V87.500] Vue.js 事件 '${vueEventName}' 触发成功`);
                                }
                            } catch (vueError) {
                                results.push({
                                    type: `vue_${vueEventName}`,
                                    dispatched: false,
                                    error: vueError.message,
                                    method: 'CustomEvent'
                                });
                            }
                        }
                    }

                    // C. 尝试直接调用 Vue.js 方法（如果存在）
                    const vueInstance = interactiveTarget.__vue__ || interactiveTarget._vnode;
                    if (vueInstance) {
                        try {
                            if (typeof vueInstance.$emit === 'function') {
                                vueInstance.$emit('click', { x, y, clientX: x, clientY: y });
                                results.push({
                                    type: 'vue_$emit',
                                    dispatched: true,
                                    method: '$emit'
                                });
                            }

                            if (typeof vueInstance.handleClick === 'function') {
                                vueInstance.handleClick({ x, y, clientX: x, clientY: y });
                                results.push({
                                    type: 'vue_handleClick',
                                    dispatched: true,
                                    method: 'handleClick'
                                });
                            }

                            if (typeof vueInstance.onClick === 'function') {
                                vueInstance.onClick({ x, y, clientX: x, clientY: y });
                                results.push({
                                    type: 'vue_onClick',
                                    dispatched: true,
                                    method: 'onClick'
                                });
                            }
                        } catch (vueMethodError) {
                            results.push({
                                type: 'vue_method',
                                dispatched: false,
                                error: vueMethodError.message,
                                method: 'vue_method'
                            });
                        }
                    }

                } catch (e) {
                    results.push({
                        type: eventType,
                        dispatched: false,
                        error: e.message,
                        method: 'unknown'
                    });
                }
            }

            return {
                success: results.some(r => r.dispatched),
                events: results,
                target: targetInfo,
                interactiveTarget: {
                    tagName: interactiveTarget.tagName,
                    id: interactiveTarget.id || '',
                    className: interactiveTarget.className || ''
                }
            };
        };

        try {
            // V87.500: 传递增强的参数对象
            const result = await this.page.evaluate(injectScript, {
                x: coords.x,
                y: coords.y,
                events: eventSequence,
                ts: timestamp,
                injectionConfig: {
                    bubbles: eventInjection.bubbles,
                    cancelable: eventInjection.cancelable,
                    composed: eventInjection.composed,
                    vueEventNamespace: eventInjection.vueEventNamespace
                }
            });

            return {
                success: result.success,
                method: 'vue_event_injection',
                eventResults: result.events,
                targetFound: result.target,
                interactiveTarget: result.interactiveTarget
            };

        } catch (error) {
            return {
                success: false,
                method: 'vue_event_injection',
                error: error.message
            };
        }
    }

    /**
     * Playwright 原生点击回退
     * @private
     */
    async _usePlaywrightClick(element, coords) {
        try {
            await this.page.mouse.click(coords.x, coords.y);
            return {
                success: true,
                method: 'playwright_click'
            };
        } catch (error) {
            return {
                success: false,
                method: 'playwright_click',
                error: error.message
            };
        }
    }

    /**
     * V87.500: 验证交互效果（状态轮询模式）
     * @private
     */
    async _validateInteraction(element, config) {
        const statePolling = config.statePolling || {};

        if (!statePolling.enabled) {
            // 回退到固定延迟模式
            await this.page.waitForTimeout(100);

            const validationResult = await this.page.evaluate(() => {
                const selectors = [
                    '[role="tooltip"]',
                    '[role="dialog"]',
                    '[role="menu"]',
                    'div[class*="modal"]',
                    'div[class*="dropdown"]',
                    'div[class*="popup"]'
                ];

                for (const selector of selectors) {
                    const elements = document.querySelectorAll(selector);
                    for (const el of elements) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            return {
                                success: true,
                                selector: selector,
                                element: el.tagName + (el.id ? '#' + el.id : ''),
                                rect: {
                                    x: rect.x,
                                    y: rect.y,
                                    width: rect.width,
                                    height: rect.height
                                }
                            };
                        }
                    }
                }

                return { success: false };
            });

            return validationResult;
        }

        // V87.500: 状态轮询模式
        log.debug(`[V87.500] 启用状态轮询模式 (maxPollTime: ${statePolling.maxPollTime}ms)`);

        try {
            const result = await this.page.waitForFunction((pollSelectors) => {
                // 检查是否有新的高 z-index 元素出现
                for (const selector of pollSelectors) {
                    const elements = document.querySelectorAll(selector);

                    for (const el of elements) {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);

                        // V87.500: 检查 z-index > 1000 的元素
                        const zIndex = parseInt(style.zIndex) || 0;

                        if (rect.width > 0 && rect.height > 0 && zIndex > 1000) {
                            return {
                                success: true,
                                selector: selector,
                                element: el.tagName + (el.id ? '#' + el.id : ''),
                                className: el.className || '',
                                zIndex: zIndex,
                                rect: {
                                    x: rect.x,
                                    y: rect.y,
                                    width: rect.width,
                                    height: rect.height
                                }
                            };
                        }
                    }
                }

                return null;  // 未找到符合条件的元素
            }, statePolling.modalSelectors, {
                timeout: statePolling.maxPollTime,
                polling: statePolling.pollInterval
            });

            if (result) {
                log.success(`[V87.500] 状态轮询检测到新层: selector=${result.selector}, z-index=${result.zIndex}`);
                return {
                    success: true,
                    method: 'state_polling',
                    ...result
                };
            } else {
                log.debug(`[V87.500] 状态轮询未检测到新层 (超时: ${statePolling.maxPollTime}ms)`);
                return {
                    success: false,
                    method: 'state_polling_timeout'
                };
            }

        } catch (error) {
            // V87.500: 处理 timeout 错误（这是正常的，表示未检测到新层）
            if (error.name === 'TimeoutError' || error.message?.includes('timeout')) {
                log.debug(`[V87.500] 状态轮询超时（未检测到新层）`);
                return {
                    success: false,
                    method: 'state_polling_timeout'
                };
            }

            return {
                success: false,
                error: error.message,
                method: 'state_polling_error'
            };
        }
    }

    /**
     * 记录点击轨迹
     * @private
     */
    _recordClickTrace(coords, result) {
        this.clickTrace.push({
            timestamp: Date.now(),
            coordinates: coords,
            result: result
        });

        if (this.config.logClickCoordinates) {
            log.debug(`[点击轨迹] 坐标: (${coords.x}, ${coords.y}), 结果: ${result.success ? '成功' : '失败'}`);
        }
    }

    /**
     * 导出点击轨迹
     */
    exportClickTrace() {
        return {
            config: this.config,
            trace: this.clickTrace,
            summary: {
                totalClicks: this.clickTrace.length,
                successfulClicks: this.clickTrace.filter(t => t.result.success).length
            }
        };
    }

    /**
     * V87.500: 自动熔断检测（针对 9900X 高并发环境）
     *
     * 检测是否触发自动熔断（连续 3 场 0 记录）
     *
     * @param {number} recordCount - 本次处理的记录数
     * @returns {Object} - 熔断状态和建议操作
     */
    checkCircuitBreaker(recordCount) {
        if (!this.config.autoCircuitBreaker?.enabled) {
            return { shouldTrip: false, reason: 'disabled' };
        }

        this.totalRecordsProcessed++;

        // 检测是否为空记录
        const isEmptyRecord = recordCount === 0;

        if (isEmptyRecord) {
            this.emptyRecordCount++;
        } else {
            // 有数据，重置计数器
            if (this.emptyRecordCount > 0) {
                log.info(`[V87.500] 空记录计数重置: ${this.emptyRecordCount} → 0 (记录数: ${recordCount})`);
            }
            this.emptyRecordCount = 0;
            this.circuitBreakerTripped = false;
        }

        const threshold = this.config.autoCircuitBreaker.emptyRecordThreshold;
        const percentage = (this.emptyRecordCount / threshold * 100).toFixed(1);

        // 检查是否触发熔断
        if (this.emptyRecordCount >= threshold && !this.circuitBreakerTripped) {
            log.warn(`[V87.500] 🚨 自动熔断触发！连续 ${this.emptyRecordCount} 场空记录 (阈值: ${threshold})`);
            log.warn(`[V87.500] 总处理记录数: ${this.totalRecordsProcessed}`);
            log.warn(`[V87.500] 建议: Context 自动重新加载或 Worker 重启`);

            this.circuitBreakerTripped = true;
            this.lastCircuitBreakTime = Date.now();

            return {
                shouldTrip: true,
                reason: 'empty_record_threshold_exceeded',
                emptyRecordCount: this.emptyRecordCount,
                threshold: threshold,
                totalProcessed: this.totalRecordsProcessed,
                suggestion: this.config.autoCircuitBreaker.autoReloadContext ?
                    'reload_context' : 'manual_restart'
            };
        } else if (this.emptyRecordCount > 0) {
            log.warn(`[V87.500] ⚠ 空记录计数: ${this.emptyRecordCount}/${threshold} (${percentage}%)`);
        }

        return {
            shouldTrip: false,
            emptyRecordCount: this.emptyRecordCount,
            threshold: threshold,
            percentage: percentage,
            totalProcessed: this.totalRecordsProcessed
        };
    }

    /**
     * V87.500: 执行 Context 重新加载（自动熔断恢复）
     *
     * @returns {Promise<boolean>} - 重新加载是否成功
     */
    async reloadContext() {
        if (!this.config.autoCircuitBreaker?.autoReloadContext) {
            log.warn('[V87.500] Context 自动重新加载未启用');
            return false;
        }

        log.info('[V87.500] 执行 Context 重新加载...');

        try {
            // 重新加载页面
            await this.page.reload({ waitUntil: 'networkidle', timeout: 30000 });

            // 重置熔断状态
            this.emptyRecordCount = 0;
            this.circuitBreakerTripped = false;

            log.success('[V87.500] Context 重新加载成功，熔断器已重置');

            return true;

        } catch (error) {
            log.error(`[V87.500] Context 重新加载失败: ${error.message}`);
            return false;
        }
    }

    /**
     * V87.500: 获取熔断器状态
     */
    getCircuitBreakerStatus() {
        return {
            emptyRecordCount: this.emptyRecordCount,
            threshold: this.config.autoCircuitBreaker.emptyRecordThreshold,
            totalProcessed: this.totalRecordsProcessed,
            isTripped: this.circuitBreakerTripped,
            lastTripTime: this.lastCircuitBreakTime ?
                new Date(this.lastCircuitBreakTime).toISOString() : null,
            percentage: this.emptyRecordCount > 0 ?
                (this.emptyRecordCount / this.config.autoCircuitBreaker.emptyRecordThreshold * 100).toFixed(1) + '%' : '0%'
        };
    }

    /**
     * V88.600: 供应商特征码识别
     *
     * 通过 SVG 路径指纹、img src 哈希值、CSS 类名、data-v-* 属性识别供应商
     * 支持 6 种主流数据源的特征码映射
     *
     * @param {ElementHandle} element - 目标元素
     * @returns {Promise<{vendorId: string, confidence: number, method: string, details: Object}>}
     */
    async identifyVendor(element) {
        // V88.600: 6 种主流数据源特征码映射表
        const VENDOR_FINGERPRINTS = {
            // Identifier_Pinnacle: 匹配 Pinnacle 特有的 SVG 路径和样式
            Pinnacle: {
                svgPathPatterns: [
                    'M453.3 193.3',           // Pinnacle 特有路径片段
                    'm126.6',
                    'd="M12 2L2 7l10 5 10-5-10-5'
                ],
                imgSrcPatterns: [
                    'pinnacle',
                    'pinnacle-sports',
                    'logo-pinnacle'
                ],
                classPatterns: [
                    'bg-vendor-gold',
                    'logo-pinnacle',
                    'provider-pinnacle',
                    'pinnacle-logo'
                ],
                dataVPatterns: [
                    'pinnacle-',
                    'vendor-pinnacle'
                ]
            },
            // Identifier_bet365: 匹配 bet365 特有特征
            bet365: {
                svgPathPatterns: [
                    'M11 2L2 7v10c0',         // bet365 特有路径
                    'M20 12l-1.41-1.41',
                    'd="M21 16.5c0'
                ],
                imgSrcPatterns: [
                    'bet365',
                    'b3-6-5',
                    'logo-bet365'
                ],
                classPatterns: [
                    'bg-vendor-yellow',
                    'logo-bet365',
                    'provider-bet365',
                    'bet365-logo'
                ],
                dataVPatterns: [
                    'bet365-',
                    'vendor-bet365'
                ]
            },
            // Identifier_Bwin: 匹配 Bwin 特有特征
            Bwin: {
                svgPathPatterns: [
                    'M17.5 14.5L',
                    'd="M3 3h18v18H3z',
                    'circle cx="12" cy="12"'
                ],
                imgSrcPatterns: [
                    'bwin',
                    'logo-bwin',
                    'bwin-party'
                ],
                classPatterns: [
                    'bg-vendor-blue',
                    'logo-bwin',
                    'provider-bwin',
                    'bwin-logo'
                ],
                dataVPatterns: [
                    'bwin-',
                    'vendor-bwin'
                ]
            },
            // Identifier_WilliamHill: 匹配 William Hill 特有特征
            WilliamHill: {
                svgPathPatterns: [
                    'M453.3 193.3',
                    'd="M22 12l-1.5-1.5',
                    'rect width="24" height="24"'
                ],
                imgSrcPatterns: [
                    'william-hill',
                    'williamhill',
                    'logo-wh'
                ],
                classPatterns: [
                    'bg-vendor-green',
                    'logo-william-hill',
                    'provider-william-hill',
                    'wh-logo'
                ],
                dataVPatterns: [
                    'william-hill-',
                    'vendor-william-hill',
                    'wh-'
                ]
            },
            // Identifier_1xBet: 匹配 1xBet 特有特征
            x1xBet: {
                svgPathPatterns: [
                    'M126.6',
                    'd="M12 2C6.48 2 2 6.48',
                    'path d="M19 3H5c'
                ],
                imgSrcPatterns: [
                    '1xbet',
                    '1x-bet',
                    'logo-1xbet'
                ],
                classPatterns: [
                    'bg-vendor-red',
                    'logo-1xbet',
                    'provider-1xbet',
                    'xbet-logo'
                ],
                dataVPatterns: [
                    '1xbet-',
                    'vendor-1xbet',
                    'xbet-'
                ]
            },
            // Identifier_Unibet: 匹配 Unibet 特有特征
            Unibet: {
                svgPathPatterns: [
                    'M21 16.5c0',
                    'd="M7 2v11h3v9',
                    'polygon points="12,2 22'
                ],
                imgSrcPatterns: [
                    'unibet',
                    'logo-unibet',
                    'uni-bet'
                ],
                classPatterns: [
                    'bg-vendor-purple',
                    'logo-unibet',
                    'provider-unibet',
                    'unibet-logo'
                ],
                dataVPatterns: [
                    'unibet-',
                    'vendor-unibet'
                ]
            }
        };

        const result = await this.page.evaluate((params) => {
            const { el, fingerprints } = params;
            const result = {
                vendorId: 'Unknown',
                confidence: 0,
                method: 'none',
                details: {}
            };

            if (!el) {
                return result;
            }

            // V88.600 方法 1: SVG 路径指纹匹配（最高置信度）
            const svgElements = el.querySelectorAll('svg path, svg');
            for (const [vendorName, vendorData] of Object.entries(fingerprints)) {
                if (vendorData.svgPathPatterns) {
                    for (const pattern of vendorData.svgPathPatterns) {
                        for (const svg of svgElements) {
                            const d = svg.getAttribute('d') || '';
                            const pathData = svg.getAttribute('path') || '';

                            if (d.includes(pattern) || pathData.includes(pattern)) {
                                result.vendorId = vendorName;
                                result.confidence = 0.98;
                                result.method = 'svg_path_fingerprint';
                                result.details.patternMatched = pattern;
                                result.details.svgFingerprint = d.substring(0, 50);
                                return result;
                            }
                        }
                    }
                }
            }

            // V88.600 方法 2: img src 哈希值匹配
            const imgElements = el.querySelectorAll('img');
            for (const [vendorName, vendorData] of Object.entries(fingerprints)) {
                if (vendorData.imgSrcPatterns) {
                    for (const img of imgElements) {
                        const src = img.src || img.getAttribute('src') || '';
                        for (const pattern of vendorData.imgSrcPatterns) {
                            if (src.toLowerCase().includes(pattern.toLowerCase())) {
                                result.vendorId = vendorName;
                                result.confidence = 0.95;
                                result.method = 'img_src_hash';
                                result.details.srcPattern = pattern;
                                result.details.imgSrc = src.substring(0, 100);
                                return result;
                            }
                        }
                    }
                }
            }

            // V88.600 方法 3: CSS 类名匹配
            const className = el.className || '';
            for (const [vendorName, vendorData] of Object.entries(fingerprints)) {
                if (vendorData.classPatterns) {
                    for (const classPattern of vendorData.classPatterns) {
                        if (className.toLowerCase().includes(classPattern.toLowerCase())) {
                            result.vendorId = vendorName;
                            result.confidence = 0.88;
                            result.method = 'css_class_match';
                            result.details.classMatched = classPattern;
                            result.details.elementClass = className;
                            return result;
                        }
                    }
                }
            }

            // V88.600 方法 4: data-v-* 属性匹配（Vue.js 组件标识）
            let parent = el.parentElement;
            let depth = 0;
            while (parent && depth < 5) {
                // 收集所有 data-v-* 属性
                const allAttributes = parent.attributes || [];
                for (const attr of allAttributes) {
                    if (attr.name && attr.name.startsWith('data-v-')) {
                        const attrValue = attr.value || '';
                        for (const [vendorName, vendorData] of Object.entries(fingerprints)) {
                            if (vendorData.dataVPatterns) {
                                for (const dataVPattern of vendorData.dataVPatterns) {
                                    if (attrValue.toLowerCase().includes(dataVPattern.toLowerCase())) {
                                        result.vendorId = vendorName;
                                        result.confidence = 0.85;
                                        result.method = 'data_v_attribute';
                                        result.details.dataVAttribute = attr.name;
                                        result.details.dataVPattern = dataVPattern;
                                        return result;
                                    }
                                }
                            }
                        }
                    }
                }
                parent = parent.parentElement;
                depth++;
            }

            // V88.600 方法 5: Parent Container 回退
            parent = el.parentElement;
            depth = 0;
            while (parent && depth < 5) {
                const parentId = parent.id || '';
                const parentClass = parent.className || '';

                // 检查常见容器 ID
                const containerPatterns = ['provider', 'vendor', 'odds'];
                for (const pattern of containerPatterns) {
                    if (parentId.toLowerCase().includes(pattern) ||
                        parentClass.toLowerCase().includes(pattern)) {
                        result.vendorId = `Container_${pattern}`;
                        result.confidence = 0.60;
                        result.method = 'parent_container_fallback';
                        result.details.containerId = parentId;
                        result.details.containerClass = parentClass;
                        return result;
                    }
                }

                parent = parent.parentElement;
                depth++;
            }

            // V88.600 方法 6: 最后回退 - 尝试从 alt/title 文本提取
            const altText = el.getAttribute('alt') || el.getAttribute('title') || el.textContent || '';
            const knownProviders = ['Pinnacle', 'bet365', 'Bwin', 'William Hill', '1xBet', 'Unibet', 'Betway'];

            for (const provider of knownProviders) {
                if (altText.toLowerCase().includes(provider.toLowerCase())) {
                    result.vendorId = provider;
                    result.confidence = 0.50;
                    result.method = 'text_fallback';
                    result.details.textMatched = provider;
                    result.details.altText = altText.substring(0, 100);
                    return result;
                }
            }

            return result;
        }, { el: element, fingerprints: VENDOR_FINGERPRINTS });

        log.info(`[V88.600] Vendor Identified: ${result.vendorId} (confidence: ${result.confidence}, method: ${result.method})`);
        return result;
    }

    /**
     * V87.300: OneTrust Cookie Consent 处理
     *
     * 检测并移除 OneTrust 横幅遮罩，解除点击阻挡
     *
     * @private
     * @returns {Promise<{success: boolean, action: string}>}
     */
    async _handleOneTrustConsent() {
        log.info('[V87.300] 检测 OneTrust Cookie Consent 横幅...');

        try {
            // 等待 OneTrust 横幅出现（最多 3 秒）
            const bannerExists = await this.page.evaluate(() => {
                const banner = document.querySelector('#onetrust-banner-sdk');
                const pcSdk = document.querySelector('#onetrust-pc-sdk');
                const overlay = document.querySelector('.ot-pc-overlay');

                return {
                    banner: !!banner,
                    pcSdk: !!pcSdk,
                    overlay: !!overlay,
                    bannerVisible: banner ? banner.style.display !== 'none' : false,
                    overlayVisible: overlay ? overlay.style.display !== 'none' : false
                };
            });

            if (!bannerExists.banner && !bannerExists.pcSdk && !bannerExists.overlay) {
                log.info('[V87.300] ✓ 未检测到 OneTrust 横幅');
                return { success: true, action: 'no_banner' };
            }

            log.warn(`[V87.300] ⚠ 检测到 OneTrust 元素: banner=${bannerExists.bannerVisible}, overlay=${bannerExists.overlayVisible}`);

            // 策略 A: 尝试点击 "Accept All" 按钮
            const acceptClicked = await this._clickOneTrustAccept();
            if (acceptClicked) {
                log.info('[V87.300] ✓ 已点击 "Accept All" 按钮');
                await this.page.waitForTimeout(500);  // 等待横幅淡出

                // 验证横幅是否移除
                const bannerRemoved = await this.page.evaluate(() => {
                    const banner = document.querySelector('#onetrust-banner-sdk');
                    return !banner || banner.style.display === 'none' || banner.style.visibility === 'hidden';
                });

                if (bannerRemoved) {
                    log.info('[V87.300] ✓ OneTrust 横幅已成功移除');
                    return { success: true, action: 'accept_clicked' };
                }
            }

            // 策略 B: 强制移除 OneTrust DOM 元素
            log.warn('[V87.300] ⚠ 尝试强制移除 OneTrust 遮罩...');
            const forceRemoved = await this.page.evaluate(() => {
                const selectors = [
                    '#onetrust-banner-sdk',
                    '#onetrust-pc-sdk',
                    '.ot-pc-overlay',
                    '.ot-floating-button'
                ];

                let removedCount = 0;
                selectors.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                        el.style.pointerEvents = 'none';
                        el.remove();
                        removedCount++;
                    });
                });

                // 移除 OneTrust 遮罩层的 z-index 样式
                const styleTags = document.querySelectorAll('style');
                styleTags.forEach(tag => {
                    if (tag.innerHTML.includes('onetrust-consent-sdk')) {
                        tag.disabled = true;
                    }
                });

                return removedCount;
            });

            if (forceRemoved > 0) {
                log.info(`[V87.300] ✓ 已强制移除 ${forceRemoved} 个 OneTrust 元素`);
                await this.page.waitForTimeout(300);  // 等待 DOM 更新
                return { success: true, action: 'force_removed', count: forceRemoved };
            }

            log.error('[V87.300] ✗ 无法移除 OneTrust 横幅');
            return { success: false, action: 'failed' };

        } catch (error) {
            log.error(`[V87.300] OneTrust 处理异常: ${error.message}`);
            return { success: false, action: 'error', error: error.message };
        }
    }

    /**
     * V87.300: 点击 OneTrust "Accept All" 按钮
     *
     * @private
     * @returns {Promise<boolean>}
     */
    async _clickOneTrustAccept() {
        try {
            // 常见的 Accept 按钮选择器
            const acceptSelectors = [
                '#onetrust-accept-btn-handler',
                '.accept-consent',
                'button:has-text("Accept")',
                'button:has-text("Accept All")',
                'button:has-text("Accept Cookies")',
                '#accept-recommended-btn-handler'
            ];

            for (const selector of acceptSelectors) {
                try {
                    const element = await this.page.$(selector);
                    if (element) {
                        await element.click({ timeout: 2000 });
                        log.info(`[V87.300] 点击按钮: ${selector}`);
                        return true;
                    }
                } catch (e) {
                    // 选择器不存在，尝试下一个
                    continue;
                }
            }

            return false;
        } catch (error) {
            log.debug(`[V87.300] 点击 Accept 按钮失败: ${error.message}`);
            return false;
        }
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * 创建矩阵点击器实例
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @param {Object} [config={}] - 配置选项
 * @returns {PixelMatrixClicker}
 */
function createMatrixClicker(page, config = {}) {
    return new PixelMatrixClicker(page, config);
}

/**
 * 快速矩阵点击
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @param {ElementHandle} element - 目标元素
 * @param {Object} [options={}] - 配置选项
 * @returns {Promise<Object>}
 */
async function quickMatrixClick(page, element, options = {}) {
    const clicker = createMatrixClicker(page, options);
    return await clicker.executeMatrixClick(element, options);
}

/**
 * V88.310: 创建供应商指纹识别器
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @returns {PixelMatrixClicker} - 返回包含供应商识别能力的点击器实例
 */
function createVendorFingerprinter(page) {
    const clicker = new PixelMatrixClicker(page);
    return clicker;
}

// ============================================================================
// BATCH PROCESSING
// ============================================================================

/**
 * 批量矩阵点击处理器
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @param {ElementHandle[]} elements - 目标元素数组
 * @param {Object} [options={}] - 配置选项
 * @returns {Promise<Object>}
 */
async function batchMatrixClick(page, elements, options = {}) {
    log.info(`[批量处理] 开始处理 ${elements.length} 个元素`);

    const results = {
        total: elements.length,
        successful: 0,
        failed: 0,
        details: []
    };

    const clicker = createMatrixClicker(page, options);

    for (let i = 0; i < elements.length; i++) {
        try {
            const result = await clicker.executeMatrixClick(elements[i], options);

            if (result.success) {
                results.successful++;
                log.success(`[批量处理] 元素 ${i + 1}/${elements.length} 成功`);
            } else {
                results.failed++;
                log.warn(`[批量处理] 元素 ${i + 1}/${elements.length} 失败`);
            }

            results.details.push({
                index: i,
                success: result.success,
                attempts: result.attempts,
                method: result.method,
                newLayersCount: result.newLayersCount || 0
            });

        } catch (error) {
            results.failed++;
            results.details.push({
                index: i,
                success: false,
                error: error.message
            });
        }
    }

    log.info(`[批量处理] 完成: ${results.successful}/${results.total} 成功`);
    return results;
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    PixelMatrixClicker,
    createMatrixClicker,
    quickMatrixClick,
    batchMatrixClick,
    V52_CONFIG,
    // V88.310: Vendor Fingerprinting exports
    createVendorFingerprinter
};
