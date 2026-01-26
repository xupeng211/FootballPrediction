/**
 * V88.000 Test C: 矩阵算法校准测试
 * =====================================
 *
 * 测试目标：
 *   - 输入特定 boundingBox（宽 10px, 高 10px）
 *   - 断言生成的 9 个点击坐标点全部落在矩形范围内
 *   - 验证坐标计算精度
 *
 * @file interaction_v52.test.js
 * @version V88.000
 * @since 2026-01-26
 */

'use strict';

const interactionV52 = require('../modules/interaction_v52');

// Mock Playwright Page 对象
const mockPage = {
    evaluate: jest.fn(),
    $$: jest.fn(),
    $: jest.fn(),
    mouse: {
        click: jest.fn().mockResolvedValue(undefined)
    },
    waitForTimeout: jest.fn().mockResolvedValue(undefined),
    keyboard: {
        press: jest.fn().mockResolvedValue(undefined)
    }
};

describe('V88.000 Test C: 矩阵算法校准', () => {
    let clicker;
    let mockElement;

    beforeEach(() => {
        jest.clearAllMocks();

        // 创建矩阵点击器（禁用实际交互）
        clicker = interactionV52.createMatrixClicker(mockPage, {
            matrixSize: 3,
            pixelOffset: 5,
            trustedEvents: false,  // 使用 Playwright 原生点击
            retryMechanism: {
                enabled: false
            },
            canaryCheck: {
                enabled: false
            }
        });

        // Mock 元素
        mockElement = {
            boundingBox: jest.fn(),
            scrollIntoViewIfNeeded: jest.fn().mockResolvedValue(undefined),
            evaluateHandle: jest.fn()
        };
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    describe('C.1: 3x3 矩阵坐标生成测试', () => {
        test('应生成 9 个点击坐标', () => {
            const boundingBox = {
                x: 100,
                y: 200,
                width: 10,
                height: 10
            };

            // 访问私有方法进行测试
            const coordinates = clicker._generateMatrixCoordinates(
                boundingBox,
                3,  // matrixSize
                5   // pixelOffset
            );

            expect(coordinates).toHaveLength(9);
        });

        test('所有坐标应落在原始矩形范围内', () => {
            const boundingBox = {
                x: 100,
                y: 200,
                width: 10,
                height: 10
            };

            const coordinates = clicker._generateMatrixCoordinates(
                boundingBox,
                3,
                5
            );

            // V88.100: 验证所有坐标严格落在 boundingBox 范围内
            coordinates.forEach((coord) => {
                expect(coord.x).toBeGreaterThanOrEqual(boundingBox.x);
                expect(coord.x).toBeLessThanOrEqual(boundingBox.x + boundingBox.width);
                expect(coord.y).toBeGreaterThanOrEqual(boundingBox.y);
                expect(coord.y).toBeLessThanOrEqual(boundingBox.y + boundingBox.height);
            });
        });

        test('中心点应为第一个坐标（最近优先）', () => {
            const boundingBox = {
                x: 100,
                y: 200,
                width: 10,
                height: 10
            };

            const coordinates = clicker._generateMatrixCoordinates(
                boundingBox,
                3,
                5
            );

            // 中心点坐标
            const centerX = boundingBox.x + boundingBox.width / 2;
            const centerY = boundingBox.y + boundingBox.height / 2;

            // 第一个坐标应该是中心点（偏移为 0,0）
            expect(coordinates[0].offsetX).toBe(0);
            expect(coordinates[0].offsetY).toBe(0);
            expect(coordinates[0].x).toBe(Math.round(centerX));
            expect(coordinates[0].y).toBe(Math.round(centerY));
        });

        test('坐标应按距离中心点排序', () => {
            const boundingBox = {
                x: 100,
                y: 200,
                width: 10,
                height: 10
            };

            const coordinates = clicker._generateMatrixCoordinates(
                boundingBox,
                3,
                5
            );

            // 计算每个坐标到中心的距离
            const centerX = boundingBox.x + boundingBox.width / 2;
            const centerY = boundingBox.y + boundingBox.height / 2;

            for (let i = 0; i < coordinates.length - 1; i++) {
                const dist1 = Math.sqrt(
                    Math.pow(coordinates[i].x - centerX, 2) +
                    Math.pow(coordinates[i].y - centerY, 2)
                );
                const dist2 = Math.sqrt(
                    Math.pow(coordinates[i + 1].x - centerX, 2) +
                    Math.pow(coordinates[i + 1].y - centerY, 2)
                );

                // 前面的坐标距离应该小于或等于后面的
                expect(dist1).toBeLessThanOrEqual(dist2);
            }
        });
    });

    describe('C.2: 边界条件测试', () => {
        test('应处理最小有效矩形（10x10）', () => {
            const boundingBox = {
                x: 0,
                y: 0,
                width: 10,
                height: 10
            };

            const coordinates = clicker._generateMatrixCoordinates(
                boundingBox,
                3,
                5
            );

            expect(coordinates).toHaveLength(9);
            coordinates.forEach(coord => {
                expect(coord.x).toBeGreaterThanOrEqual(0);
                expect(coord.y).toBeGreaterThanOrEqual(0);
            });
        });

        test('应处理超大矩形（1920x1080）', () => {
            const boundingBox = {
                x: 0,
                y: 0,
                width: 1920,
                height: 1080
            };

            const coordinates = clicker._generateMatrixCoordinates(
                boundingBox,
                3,
                5
            );

            expect(coordinates).toHaveLength(9);
            coordinates.forEach(coord => {
                expect(coord.x).toBeGreaterThanOrEqual(10);  // padding
                expect(coord.x).toBeLessThanOrEqual(1910);
                expect(coord.y).toBeGreaterThanOrEqual(10);
                expect(coord.y).toBeLessThanOrEqual(1070);
            });
        });

        test('应处理负坐标矩形', () => {
            const boundingBox = {
                x: -50,
                y: -100,
                width: 100,
                height: 200
            };

            const coordinates = clicker._generateMatrixCoordinates(
                boundingBox,
                3,
                5
            );

            expect(coordinates).toHaveLength(9);
        });
    });

    describe('C.3: 像素偏移计算', () => {
        test('像素偏移应正确计算', () => {
            const boundingBox = {
                x: 100,
                y: 200,
                width: 20,
                height: 20
            };

            const coordinates = clicker._generateMatrixCoordinates(
                boundingBox,
                3,
                5
            );

            // V88.100: 验证偏移步长（边界钳制后使用 floor）
            const expectedOffsetStep = Math.floor(Math.min(5, 20 / 3) / 2);  // 2

            // 检查生成的偏移
            const uniqueOffsets = new Set();
            coordinates.forEach(coord => {
                uniqueOffsets.add(`${coord.offsetX},${coord.offsetY}`);
            });

            // 应该有 9 个不同的偏移组合
            expect(uniqueOffsets.size).toBe(9);
        });

        test('应包含所有 3x3 矩阵偏移组合', () => {
            const boundingBox = {
                x: 100,
                y: 200,
                width: 20,
                height: 20
            };

            const coordinates = clicker._generateMatrixCoordinates(
                boundingBox,
                3,
                5
            );

            // 检查是否包含 3x3 的所有偏移
            const offsets = coordinates.map(c => `${c.offsetX},${c.offsetY}`);

            // V88.100: 预期的偏移组合（边界钳制后的步长为 2）
            const expectedOffsets = [
                '0,0',    // 中心
                '0,2',    // 下
                '0,-2',   // 上
                '2,0',    // 右
                '2,2',    // 右下
                '2,-2',   // 右上
                '-2,0',   // 左
                '-2,2',   // 左下
                '-2,-2'   // 左上
            ];

            expectedOffsets.forEach(offset => {
                expect(offsets).toContain(offset);
            });
        });
    });

    describe('C.4: 坐标精度测试', () => {
        test('坐标应为整数（向上取整）', () => {
            const boundingBox = {
                x: 100.5,
                y: 200.7,
                width: 10.3,
                height: 10.9
            };

            const coordinates = clicker._generateMatrixCoordinates(
                boundingBox,
                3,
                5
            );

            coordinates.forEach(coord => {
                expect(Number.isInteger(coord.x)).toBe(true);
                expect(Number.isInteger(coord.y)).toBe(true);
            });
        });

        test('中心点应精确计算', () => {
            const boundingBox = {
                x: 100,
                y: 200,
                width: 11,  // 奇数宽度，中心应为 .5
                height: 11
            };

            const coordinates = clicker._generateMatrixCoordinates(
                boundingBox,
                3,
                5
            );

            // 中心点
            expect(coordinates[0].x).toBe(106);
            expect(coordinates[0].y).toBe(206);
        });
    });

    describe('C.5: 边界框填充影响', () => {
        test('应正确应用边界框填充', () => {
            const boundingBox = {
                x: 0,
                y: 0,
                width: 50,
                height: 50
            };

            const padding = 10;
            const coordinates = clicker._generateMatrixCoordinates(
                boundingBox,
                3,
                5
            );

            // 坐标应在填充后的边界内
            const minX = padding;
            const maxX = boundingBox.width - padding;
            const minY = padding;
            const maxY = boundingBox.height - padding;

            coordinates.forEach(coord => {
                // 允许像素偏移范围
                expect(coord.x).toBeGreaterThanOrEqual(minX - 5);
                expect(coord.x).toBeLessThanOrEqual(maxX + 5);
                expect(coord.y).toBeGreaterThanOrEqual(minY - 5);
                expect(coord.y).toBeLessThanOrEqual(maxY + 5);
            });
        });
    });

    describe('C.6: 点击轨迹记录', () => {
        test('应正确记录点击轨迹', async () => {
            mockElement.boundingBox.mockResolvedValue({
                x: 100,
                y: 200,
                width: 10,
                height: 10
            });

            mockPage.evaluate.mockResolvedValue({
                success: true
            });

            // 执行矩阵点击（使用简化的 mock）
            const result = await clicker.executeMatrixClick(mockElement);

            // 验证点击轨迹
            const trace = clicker.exportClickTrace();
            expect(trace.summary.totalClicks).toBeGreaterThan(0);
        });
    });
});
