/**
 * V87.202 Shadow DOM Scanner Module - DOM Deep Scan
 * =====================================================
 *
 * 核心功能：
 *   - 深度扫描 DOM 结构，检测隐藏的 iframe 或 ShadowRoot
 *   - 完整 HTML 结构导出（停用资源拦截）
 *   - 边界组件可见性分析
 *
 * V87.202 修复：
 *   - 修正 A: 所有 page.evaluate 调用参数封装为单个对象
 *   - 修正 B: className 类型兼容性（SVG 元素支持）
 *
 * @module shadow_dom_scanner
 * @version V87.202
 * @since 2026-01-26
 */

'use strict';

const logger = require('./logger');
const log = logger.createLogger('shadow_scanner');
const fs = require('fs');
const path = require('path');

// ============================================================================
// CONFIGURATION
// ============================================================================

const SCAN_CONFIG = {
    // 目标容器选择器
    targetContainerSelector: 'div.border-black-borders',

    // 深度扫描配置
    maxDepth: 10,              // 最大遍历深度
    maxNodes: 5000,            // 最大节点数（防止内存溢出）

    // 隐藏元素检测
    hiddenElementChecks: {
        displayNone: true,
        visibilityHidden: true,
        opacityZero: true,
        sizeZero: true,
        offScreen: true
    },

    // 输出配置
    outputDir: path.join(__dirname, '../../logs/v87_201_scans'),
    exportHTML: true,
    exportJSON: true
};

// ============================================================================
// DOM SCANNER CLASS
// ============================================================================

class ShadowDomScanner {
    constructor(page) {
        this.page = page;
        this.scanResults = {
            timestamp: new Date().toISOString(),
            containerInfo: null,
            hiddenElements: [],
            shadowRoots: [],
            iframes: [],
            componentStates: []
        };
    }

    /**
     * 步骤 A: 执行完整 DOM 深度扫描
     *
     * @returns {Promise<Object>} 扫描结果
     */
    async performDeepScan() {
        log.info('[步骤 A] === DOM 深度扫描启动 ===');

        try {
            // A.1: 定位目标容器
            await this._locateTargetContainer();

            // A.2: 深度遍历 DOM 树
            await this._deepTraverseDOM();

            // A.3: 检测 Shadow Root
            await this._detectShadowRoots();

            // A.4: 检测 iframe
            await this._detectIframes();

            // A.5: 分析组件可见性
            await this._analyzeComponentVisibility();

            // A.6: 导出结果
            await this._exportScanResults();

            log.success('[步骤 A] DOM 深度扫描完成');
            return this.scanResults;

        } catch (error) {
            log.error(`[步骤 A] 扫描失败: ${error.message}`);
            throw error;
        }
    }

    /**
     * A.1: 定位目标容器
     * @private
     */
    async _locateTargetContainer() {
        log.debug('[A.1] 定位目标容器...');

        const containers = await this.page.$$(SCAN_CONFIG.targetContainerSelector);

        if (containers.length === 0) {
            log.warn(`[A.1] 未找到目标容器: ${SCAN_CONFIG.targetContainerSelector}`);
            this.scanResults.containerInfo = {
                found: false,
                count: 0,
                selector: SCAN_CONFIG.targetContainerSelector
            };
            return;
        }

        log.success(`[A.1] 找到 ${containers.length} 个目标容器`);

        this.scanResults.containerInfo = {
            found: true,
            count: containers.length,
            selector: SCAN_CONFIG.targetContainerSelector,
            boundingBoxes: []
        };

        // 获取每个容器的边界框
        for (let i = 0; i < Math.min(containers.length, 10); i++) {
            try {
                const box = await containers[i].boundingBox();
                if (box) {
                    this.scanResults.containerInfo.boundingBoxes.push({
                        index: i,
                        x: box.x,
                        y: box.y,
                        width: box.width,
                        height: box.height,
                        area: box.width * box.height
                    });
                }
            } catch (e) {
                // 忽略单个容器的错误
            }
        }
    }

    /**
     * A.2: 深度遍历 DOM 树
     * @private
     */
    async _deepTraverseDOM() {
        log.debug('[A.2] 深度遍历 DOM 树...');

        // V87.202 修正 A: 参数封装为单个对象
        const traversalScript = (params) => {
            const { selector, maxDepth, maxNodes } = params;
            const results = {
                nodes: [],
                hiddenElements: [],
                totalNodes: 0
            };

            function traverse(node, depth = 0) {
                if (depth > maxDepth || results.totalNodes > maxNodes) {
                    return;
                }

                // V87.203 修复: 只有真正的 Element 节点才能调用 getComputedStyle
                if (node.nodeType !== Node.ELEMENT_NODE) {
                    // 对于非 Element 节点（如 Text 节点），仍然递归处理其子节点
                    for (const child of node.childNodes) {
                        traverse(child, depth + 1);
                    }
                    return;
                }

                results.totalNodes++;

                // 获取节点信息
                const nodeInfo = {
                    tagName: node.tagName,
                    id: node.id || '',
                    className: node.className || '',
                    depth: depth
                };

                // 检查是否为隐藏元素
                const computedStyle = window.getComputedStyle(node);
                const isHidden = (
                    computedStyle.display === 'none' ||
                    computedStyle.visibility === 'hidden' ||
                    computedStyle.opacity === '0' ||
                    (node.offsetWidth === 0 && node.offsetHeight === 0)
                );

                if (isHidden) {
                    results.hiddenElements.push({
                        ...nodeInfo,
                        reason: (
                            computedStyle.display === 'none' ? 'display:none' :
                            computedStyle.visibility === 'hidden' ? 'visibility:hidden' :
                            computedStyle.opacity === '0' ? 'opacity:0' :
                            'size:0'
                        ),
                        textContent: node.textContent?.substring(0, 50) || ''
                    });
                }

                if (node.nodeType === Node.ELEMENT_NODE) {
                    results.nodes.push(nodeInfo);
                }

                // 递归遍历子节点
                for (const child of node.childNodes) {
                    traverse(child, depth + 1);
                }
            }

            // 从目标容器开始遍历
            const containers = document.querySelectorAll(selector);
            containers.forEach(container => traverse(container));

            return results;
        };

        try {
            // V87.202 修正 A: 传递单个参数对象
            const result = await this.page.evaluate(traversalScript, {
                selector: SCAN_CONFIG.targetContainerSelector,
                maxDepth: SCAN_CONFIG.maxDepth,
                maxNodes: SCAN_CONFIG.maxNodes
            });

            this.scanResults.hiddenElements = result ? result.hiddenElements : [];
            this.scanResults.domTraversal = {
                totalNodes: result ? result.totalNodes : 0,
                hiddenCount: result ? result.hiddenElements.length : 0,
                depthReached: SCAN_CONFIG.maxDepth
            };

            log.debug(`[A.2] 遍历完成: ${this.scanResults.domTraversal.totalNodes} 节点, ${this.scanResults.domTraversal.hiddenCount} 个隐藏元素`);

        } catch (error) {
            log.error(`[A.2] 遍历失败: ${error.message}`);
            // V88.100 修复: 确保始终返回初始化的 results 对象
            if (!this.scanResults.hiddenElements) {
                this.scanResults.hiddenElements = [];
            }
            if (!this.scanResults.domTraversal) {
                this.scanResults.domTraversal = {
                    totalNodes: 0,
                    hiddenCount: 0,
                    depthReached: SCAN_CONFIG.maxDepth
                };
            }
        }

        // V88.100 修复: 显式返回包含 totalNodes、hiddenElements 和 depthReached 的结果对象
        return {
            totalNodes: this.scanResults.domTraversal.totalNodes,
            hiddenElements: this.scanResults.hiddenElements,
            depthReached: this.scanResults.domTraversal.depthReached
        };
    }

    /**
     * A.3: 检测 Shadow Root
     * @private
     */
    async _detectShadowRoots() {
        log.debug('[A.3] 检测 Shadow Root...');

        // V87.202 修正 A: 参数封装为单个对象
        const shadowDetectionScript = (params) => {
            const { selector } = params;
            const results = [];
            const containers = document.querySelectorAll(selector);

            function findShadowRoots(element, path = []) {
                // 检查当前元素是否有 Shadow Root
                if (element.shadowRoot) {
                    results.push({
                        path: path.join(' > '),
                        tagName: element.tagName,
                        id: element.id || '',
                        className: element.className || '',
                        childCount: element.shadowRoot.children.length,
                        innerHTML: element.shadowRoot.innerHTML.substring(0, 500)
                    });
                }

                // 递归检查子元素
                for (const child of element.children) {
                    findShadowRoots(child, [...path, `${child.tagName}${child.id ? '#' + child.id : ''}`]);
                }
            }

            containers.forEach(container => findShadowRoots(container, [selector]));

            return results;
        };

        try {
            // V87.202 修正 A: 传递单个参数对象
            const shadowRoots = await this.page.evaluate(shadowDetectionScript, {
                selector: SCAN_CONFIG.targetContainerSelector
            });

            this.scanResults.shadowRoots = shadowRoots;

            if (shadowRoots.length > 0) {
                log.success(`[A.3] 检测到 ${shadowRoots.length} 个 Shadow Root`);
            } else {
                log.debug('[A.3] 未检测到 Shadow Root');
            }

        } catch (error) {
            log.error(`[A.3] Shadow Root 检测失败: ${error.message}`);
        }
    }

    /**
     * A.4: 检测 iframe
     * @private
     */
    async _detectIframes() {
        log.debug('[A.4] 检测 iframe...');

        // V87.202 修正 A: 参数封装为单个对象
        const iframeDetectionScript = (params) => {
            const { selector } = params;
            const results = [];
            const containers = document.querySelectorAll(selector);

            function findIframes(element, path = []) {
                const iframes = element.querySelectorAll('iframe');

                iframes.forEach(iframe => {
                    const rect = iframe.getBoundingClientRect();

                    results.push({
                        path: path.join(' > '),
                        src: iframe.src || '(no src)',
                        width: iframe.width,
                        height: iframe.height,
                        displayRect: {
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height,
                            visible: rect.width > 0 && rect.height > 0
                        },
                        sandbox: iframe.sandbox?.toString() || '',
                        loading: iframe.loading || 'eager'
                    });
                });

                // 递归检查子元素
                for (const child of element.children) {
                    if (child.tagName !== 'IFRAME') {
                        findIframes(child, [...path, `${child.tagName}`]);
                    }
                }
            }

            containers.forEach(container => findIframes(container, [selector]));

            return results;
        };

        try {
            // V87.202 修正 A: 传递单个参数对象
            const iframes = await this.page.evaluate(iframeDetectionScript, {
                selector: SCAN_CONFIG.targetContainerSelector
            });

            this.scanResults.iframes = iframes;

            if (iframes.length > 0) {
                log.success(`[A.4] 检测到 ${iframes.length} 个 iframe`);
            } else {
                log.debug('[A.4] 未检测到 iframe');
            }

        } catch (error) {
            log.error(`[A.4] iframe 检测失败: ${error.message}`);
        }
    }

    /**
     * A.5: 分析组件可见性
     * @private
     */
    async _analyzeComponentVisibility() {
        log.debug('[A.5] 分析组件可见性...');

        // V87.202 修正 A: 参数封装为单个对象
        const visibilityAnalysisScript = (params) => {
            const { selector } = params;
            const results = {
                totalComponents: 0,
                visibleComponents: 0,
                hiddenComponents: 0,
                partiallyVisibleComponents: 0,
                components: []
            };

            const containers = document.querySelectorAll(selector);

            function analyzeVisibility(element, depth = 0) {
                if (depth > 5) return; // 限制深度

                const rect = element.getBoundingClientRect();
                const computedStyle = window.getComputedStyle(element);

                // 跳过非组件元素
                if (!element.querySelector && !element.textContent) {
                    return;
                }

                results.totalComponents++;

                // V87.202 修正 B: 使用安全的 className 获取方式（兼容 SVG）
                const className = String(element.getAttribute('class') || '').substring(0, 100);

                const componentInfo = {
                    tagName: element.tagName,
                    id: element.id || '',
                    className: className,
                    depth: depth,
                    rect: {
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    },
                    viewport: {
                        innerWidth: window.innerWidth,
                        innerHeight: window.innerHeight
                    }
                };

                // 判断可见性状态
                const isInViewport = (
                    rect.top >= 0 &&
                    rect.left >= 0 &&
                    rect.bottom <= window.innerHeight &&
                    rect.right <= window.innerWidth
                );

                const isVisible = (
                    computedStyle.display !== 'none' &&
                    computedStyle.visibility !== 'hidden' &&
                    parseFloat(computedStyle.opacity) > 0 &&
                    rect.width > 0 &&
                    rect.height > 0
                );

                const isPartiallyVisible = (
                    isVisible &&
                    !isInViewport &&
                    rect.bottom > 0 &&
                    rect.right > 0 &&
                    rect.top < window.innerHeight &&
                    rect.left < window.innerWidth
                );

                if (isVisible && isInViewport) {
                    componentInfo.state = 'RENDERED';
                    results.visibleComponents++;
                } else if (isPartiallyVisible) {
                    componentInfo.state = 'PARTIAL';
                    results.partiallyVisibleComponents++;
                } else if (!isVisible) {
                    componentInfo.state = 'MISSING';
                    componentInfo.reason = (
                        computedStyle.display === 'none' ? 'display:none' :
                        computedStyle.visibility === 'hidden' ? 'visibility:hidden' :
                        parseFloat(computedStyle.opacity) === 0 ? 'opacity:0' :
                        'size:0'
                    );
                    results.hiddenComponents++;
                } else {
                    componentInfo.state = 'OFFSCREEN';
                    results.hiddenComponents++;
                }

                results.components.push(componentInfo);

                // 递归分析子组件
                for (const child of element.children) {
                    analyzeVisibility(child, depth + 1);
                }
            }

            containers.forEach(container => analyzeVisibility(container));

            return results;
        };

        try {
            // V87.202 修正 A: 传递单个参数对象
            const analysis = await this.page.evaluate(visibilityAnalysisScript, {
                selector: SCAN_CONFIG.targetContainerSelector
            });

            this.scanResults.componentStates = analysis.components;
            this.scanResults.visibilitySummary = {
                total: analysis.totalComponents,
                rendered: analysis.visibleComponents,
                partial: analysis.partiallyVisibleComponents,
                missing: analysis.hiddenComponents
            };

            log.success(`[A.5] 组件可见性分析完成:`);
            log.info(`  - 总计: ${analysis.totalComponents}`);
            log.info(`  - 渲染完成: ${analysis.visibleComponents}`);
            log.info(`  - 部分可见: ${analysis.partiallyVisibleComponents}`);
            log.info(`  - 缺失/隐藏: ${analysis.hiddenComponents}`);

        } catch (error) {
            log.error(`[A.5] 组件可见性分析失败: ${error.message}`);
        }
    }

    /**
     * A.6: 导出扫描结果
     * @private
     */
    async _exportScanResults() {
        log.debug('[A.6] 导出扫描结果...');

        try {
            // 确保输出目录存在
            if (!fs.existsSync(SCAN_CONFIG.outputDir)) {
                fs.mkdirSync(SCAN_CONFIG.outputDir, { recursive: true });
            }

            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const filenameBase = `scan_${timestamp}`;

            // 导出 JSON
            if (SCAN_CONFIG.exportJSON) {
                const jsonPath = path.join(SCAN_CONFIG.outputDir, `${filenameBase}.json`);
                fs.writeFileSync(
                    jsonPath,
                    JSON.stringify(this.scanResults, null, 2),
                    'utf8'
                );
                log.debug(`[A.6] JSON 导出: ${jsonPath}`);
            }

            // 导出完整 HTML
            if (SCAN_CONFIG.exportHTML) {
                const htmlContent = await this.page.content();
                const htmlPath = path.join(SCAN_CONFIG.outputDir, `${filenameBase}.html`);
                fs.writeFileSync(htmlPath, htmlContent, 'utf8');
                log.debug(`[A.6] HTML 导出: ${htmlPath}`);
            }

        } catch (error) {
            log.error(`[A.6] 结果导出失败: ${error.message}`);
        }
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * 创建扫描器实例
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @returns {ShadowDomScanner}
 */
function createScanner(page) {
    return new ShadowDomScanner(page);
}

/**
 * 快速扫描：仅检测关键元素
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @returns {Promise<Object>}
 */
async function quickScan(page) {
    const scanner = createScanner(page);
    return await scanner.performDeepScan();
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    ShadowDomScanner,
    createScanner,
    quickScan,
    SCAN_CONFIG
};
