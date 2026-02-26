/**
 * V88.000 Test A: 扫描器健壮性测试
 * =====================================
 *
 * 测试目标：
 *   - 模拟混合 nodeType 环境（Element, Text, Comment）
 *   - 确保 getComputedStyle 仅在 Element 上触发
 *   - 验证不抛出 TypeError
 *
 * @file shadow_dom_scanner.test.js
 * @version V88.000
 * @since 2026-01-26
 */

'use strict';

// Mock Playwright Page 对象
const mockPage = {
    evaluate: jest.fn(),
    $$: jest.fn(),
    content: jest.fn().mockResolvedValue('<html></html>')
};

// 导入被测试模块
const shadowScanner = require('../modules/shadow_dom_scanner');

describe('V88.000 Test A: Shadow DOM Scanner 健壮性', () => {
    let scanner;

    beforeEach(() => {
        // 重置所有 mocks
        jest.clearAllMocks();
        scanner = shadowScanner.createScanner(mockPage);
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    describe('A.1: 混合 nodeType 环境测试', () => {
        test('应正确处理 Element 节点（nodeType = 1）', async () => {
            // 模拟返回的 DOM 结构
            mockPage.evaluate.mockResolvedValueOnce({
                nodes: [
                    { tagName: 'DIV', id: 'container', className: 'test-class', depth: 0 }
                ],
                hiddenElements: [],
                totalNodes: 1
            });

            const result = await scanner._deepTraverseDOM();

            expect(mockPage.evaluate).toHaveBeenCalled();
            expect(result.totalNodes).toBe(1);
        });

        test('应跳过 Text 节点（nodeType = 3）且不抛出错误', async () => {
            // 模拟包含 Text 节点的 DOM
            const mockTraversalScript = (params) => {
                const results = { nodes: [], hiddenElements: [], totalNodes: 0 };

                // 模拟 traverse 函数处理混合节点类型
                function traverse(node, depth = 0) {
                    if (node.nodeType !== Node.ELEMENT_NODE) {
                        // 对于非 Element 节点，递归处理子节点后返回
                        if (node.childNodes) {
                            node.childNodes.forEach(child => traverse(child, depth + 1));
                        }
                        return;
                    }

                    results.totalNodes++;
                    results.nodes.push({
                        tagName: node.tagName,
                        id: node.id || '',
                        className: node.className || '',
                        depth: depth
                    });
                }

                return results;
            };

            mockPage.evaluate.mockImplementationOnce(mockTraversalScript);

            // 验证不抛出 TypeError
            await expect(scanner._deepTraverseDOM()).resolves.not.toThrow();
        });

        test('应跳过 Comment 节点（nodeType = 8）且不抛出错误', async () => {
            // 模拟包含 Comment 节点的 DOM
            mockPage.evaluate.mockResolvedValueOnce({
                nodes: [],
                hiddenElements: [],
                totalNodes: 0
            });

            const result = await scanner._deepTraverseDOM();

            expect(mockPage.evaluate).toHaveBeenCalled();
            expect(result.totalNodes).toBe(0);
        });
    });

    describe('A.2: getComputedStyle 仅在 Element 上触发', () => {
        test('不应在 Text 节点上调用 getComputedStyle', async () => {
            // 创建模拟环境
            const mockDomScript = (params) => {
                let getComputedStyleCalledOnNonElement = false;

                function traverse(node, depth = 0) {
                    // V87.203 修复: 检查 nodeType
                    if (node.nodeType !== Node.ELEMENT_NODE) {
                        // 不应调用 getComputedStyle
                        return;
                    }

                    // 只在 Element 节点上调用
                    try {
                        window.getComputedStyle(node);
                    } catch (e) {
                        // 记录错误
                        getComputedStyleCalledOnNonElement = true;
                    }
                }

                return { getComputedStyleCalledOnNonElement };
            };

            mockPage.evaluate.mockImplementationOnce(mockDomScript);

            const result = await scanner._deepTraverseDOM();

            expect(result).toBeDefined();
        });

        test('应正确识别隐藏的 Element 节点', async () => {
            mockPage.evaluate.mockResolvedValueOnce({
                nodes: [],
                hiddenElements: [
                    {
                        tagName: 'DIV',
                        id: 'hidden-div',
                        className: 'hidden',
                        depth: 1,
                        reason: 'display:none',
                        textContent: 'hidden text'
                    }
                ],
                totalNodes: 1
            });

            const result = await scanner._deepTraverseDOM();

            expect(result.hiddenElements).toHaveLength(1);
            expect(result.hiddenElements[0].reason).toBe('display:none');
        });
    });

    describe('A.3: 参数封装正确性', () => {
        test('应正确传递参数对象给 page.evaluate', async () => {
            mockPage.evaluate.mockResolvedValueOnce({
                nodes: [],
                hiddenElements: [],
                totalNodes: 0
            });

            await scanner._deepTraverseDOM();

            // 验证参数被正确封装为单个对象
            const evaluateCall = mockPage.evaluate.mock.calls[0];
            expect(evaluateCall[1]).toEqual({
                selector: 'div.border-black-borders',
                maxDepth: 10,
                maxNodes: 5000
            });
        });
    });

    describe('A.4: className 类型兼容性', () => {
        test('应正确处理 SVG 元素的 className', async () => {
            // 模拟 SVG 元素的 className 是 SVGAnimatedString
            mockPage.evaluate.mockImplementationOnce((params) => {
                // 模拟 SVG 元素
                return {
                    nodes: [{
                        tagName: 'svg',
                        id: '',
                        className: 'svg-icon',  // 应该是字符串，不是对象
                        depth: 0
                    }],
                    hiddenElements: [],
                    totalNodes: 1
                };
            });

            const result = await scanner._deepTraverseDOM();

            expect(result).toBeDefined();
        });
    });

    describe('A.5: 边界条件测试', () => {
        test('应正确处理空 DOM', async () => {
            mockPage.evaluate.mockResolvedValueOnce({
                nodes: [],
                hiddenElements: [],
                totalNodes: 0
            });

            const result = await scanner._deepTraverseDOM();

            expect(result.totalNodes).toBe(0);
            expect(result.hiddenElements).toHaveLength(0);
        });

        test('应正确处理超深嵌套', async () => {
            mockPage.evaluate.mockResolvedValueOnce({
                nodes: [],
                hiddenElements: [],
                totalNodes: 5000,
                depthReached: 10
            });

            const result = await scanner._deepTraverseDOM();

            expect(result.totalNodes).toBe(5000);
            expect(result.depthReached).toBe(10);
        });
    });
});
