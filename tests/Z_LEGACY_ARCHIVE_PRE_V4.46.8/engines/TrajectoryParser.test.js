/**
 * TrajectoryParser Unit Tests - V167.000
 * ==========================================
 *
 * [Genesis.Reconstruction] 测试保护机制
 *
 * 测试覆盖:
 * - PayoutCalculator: 统一返还率计算
 * - Opening/Closing 识别
 * - 时间戳解析与对齐
 * - 边界条件处理
 *
 * @module tests/engines/TrajectoryParser.test
 * @version V167.000
 * @since 2026-02-02
 * @author [Genesis.Reconstruction]
 */

'use strict';

const {
    TrajectoryParser,
    PayoutCalculator,
    SyncTimestamp,
    alignTimestamp
} = require('../../src/infrastructure/engines/parsers/TrajectoryParser');

describe('TrajectoryParser - V167.000 Consolidated Edition', () => {

    // ========================================================================
    // PayoutCalculator Tests (Consolidated Logic)
    // ========================================================================

    describe('PayoutCalculator', () => {

        describe('calculate() - Standard Cases', () => {
            it('should calculate correct payout for standard odds', () => {
                const result = PayoutCalculator.calculate(2.0, 3.5, 4.0);
                expect(result).toBeCloseTo(91.53, 1);
            });

            it('should calculate correct payout for another set', () => {
                const result = PayoutCalculator.calculate(1.5, 4.0, 6.0);
                expect(result).toBeCloseTo(92.31, 1);
            });

            it('should handle decimal odds correctly', () => {
                const result = PayoutCalculator.calculate(2.5, 3.0, 3.0);
                expect(result).toBeCloseTo(92.86, 1);
            });
        });

        describe('calculate() - Edge Cases', () => {
            it('should return null for zero odds', () => {
                expect(PayoutCalculator.calculate(0, 3.5, 4.0)).toBeNull();
                expect(PayoutCalculator.calculate(2.0, 0, 4.0)).toBeNull();
                expect(PayoutCalculator.calculate(2.0, 3.5, 0)).toBeNull();
            });

            it('should return null for negative odds', () => {
                expect(PayoutCalculator.calculate(-2.0, 3.5, 4.0)).toBeNull();
            });

            it('should return null for null/undefined odds', () => {
                expect(PayoutCalculator.calculate(null, 3.5, 4.0)).toBeNull();
                expect(PayoutCalculator.calculate(2.0, undefined, 4.0)).toBeNull();
                expect(PayoutCalculator.calculate(2.0, 3.5, null)).toBeNull();
            });

            it('should return null for NaN odds', () => {
                expect(PayoutCalculator.calculate(NaN, 3.5, 4.0)).toBeNull();
                expect(PayoutCalculator.calculate(2.0, NaN, 4.0)).toBeNull();
            });

            it('should return null for odds below minimum (1.01)', () => {
                expect(PayoutCalculator.calculate(1.0, 3.5, 4.0)).toBeNull();
                expect(PayoutCalculator.calculate(1.001, 3.5, 4.0)).toBeNull();
            });

            it('should return null for odds above maximum (500)', () => {
                expect(PayoutCalculator.calculate(600, 3.5, 4.0)).toBeNull();
            });
        });

        describe('calculate() - Boundary Payouts', () => {
            it('should warn but calculate for low payout (< 85%)', () => {
                const consoleWarn = jest.spyOn(console, 'warn').mockImplementation();
                const result = PayoutCalculator.calculate(1.5, 1.5, 1.5);
                // Extreme low odds = extremely low payout
                expect(result).not.toBeNull();
                expect(result).toBeLessThan(85);
                consoleWarn.mockRestore();
            });

            it('should warn but calculate for high payout (> 105%)', () => {
                const consoleWarn = jest.spyOn(console, 'warn').mockImplementation();
                const result = PayoutCalculator.calculate(100, 100, 100);
                expect(result).not.toBeNull();
                expect(result).toBeCloseTo(100, 0);
                consoleWarn.mockRestore();
            });
        });

        describe('fromOddsObject() - Object Parsing', () => {
            it('should calculate from {home, draw, away} object', () => {
                const odds = { home: 2.0, draw: 3.5, away: 4.0 };
                expect(PayoutCalculator.fromOddsObject(odds)).toBeCloseTo(91.53, 1);
            });

            it('should calculate from {h, d, a} object', () => {
                const odds = { h: 2.0, d: 3.5, a: 4.0 };
                expect(PayoutCalculator.fromOddsObject(odds)).toBeCloseTo(91.53, 1);
            });

            it('should calculate from {H, D, A} object', () => {
                const odds = { H: 2.0, D: 3.5, A: 4.0 };
                expect(PayoutCalculator.fromOddsObject(odds)).toBeCloseTo(91.53, 1);
            });

            it('should return null for invalid object', () => {
                expect(PayoutCalculator.fromOddsObject(null)).toBeNull();
                expect(PayoutCalculator.fromOddsObject({})).toBeNull();
                expect(PayoutCalculator.fromOddsObject([])).toBeNull();
            });
        });

        describe('isHealthy() - Health Check', () => {
            it('should return true for healthy payout', () => {
                expect(PayoutCalculator.isHealthy(95.0)).toBe(true);
                expect(PayoutCalculator.isHealthy(90.0)).toBe(true);
                expect(PayoutCalculator.isHealthy(100.0)).toBe(true);
            });

            it('should return false for unhealthy payout', () => {
                expect(PayoutCalculator.isHealthy(null)).toBe(false);
                expect(PayoutCalculator.isHealthy(80.0)).toBe(false);
                expect(PayoutCalculator.isHealthy(110.0)).toBe(false);
            });
        });

        describe('calculateBatch() - Batch Processing', () => {
            it('should calculate multiple payouts', () => {
                const oddsArray = [
                    [2.0, 3.5, 4.0],
                    [1.5, 4.0, 6.0],
                    [2.5, 3.0, 3.0]
                ];
                const results = PayoutCalculator.calculateBatch(oddsArray);

                expect(results).toHaveLength(3);
                expect(results[0]).toBeCloseTo(91.53, 1);
                expect(results[1]).toBeCloseTo(92.31, 1);
                expect(results[2]).toBeCloseTo(92.86, 1);
            });

            it('should handle null in batch', () => {
                const oddsArray = [
                    [2.0, 3.5, 4.0],
                    [0, 3.5, 4.0],     // Invalid
                    [2.5, 3.0, 3.0]
                ];
                const results = PayoutCalculator.calculateBatch(oddsArray);

                expect(results).toHaveLength(3);
                expect(results[0]).not.toBeNull();
                expect(results[1]).toBeNull();
                expect(results[2]).not.toBeNull();
            });
        });
    });

    // ========================================================================
    // SyncTimestamp Tests
    // ========================================================================

    describe('SyncTimestamp', () => {

        describe('parse() - Date Format Parsing', () => {
            it('should parse "DD Mon, HH:mm" format', () => {
                const sync = new SyncTimestamp({ baseYear: 2024 });
                const result = sync.parse('24 Jan, 10:00');
                expect(result).toBe('2024-01-24T10:00:00.000Z');
            });

            it('should parse "Mon DD, HH:mm" format', () => {
                const sync = new SyncTimestamp({ baseYear: 2024 });
                const result = sync.parse('Jan 24, 10:00');
                expect(result).toBe('2024-01-24T10:00:00.000Z');
            });

            it('should parse with period in month', () => {
                const sync = new SyncTimestamp({ baseYear: 2024 });
                const result = sync.parse('24 Jan., 10:00');
                expect(result).toBe('2024-01-24T10:00:00.000Z');
            });
        });

        describe('parse() - Edge Cases', () => {
            it('should return null for invalid input', () => {
                const sync = new SyncTimestamp();
                expect(sync.parse(null)).toBeNull();
                expect(sync.parse(undefined)).toBeNull();
                expect(sync.parse('')).toBeNull();
                expect(sync.parse('invalid')).toBeNull();
                expect(sync.parse({})).toBeNull();
            });

            it('should return null for non-string input', () => {
                const sync = new SyncTimestamp();
                expect(sync.parse(123)).toBeNull();
                expect(sync.parse([])).toBeNull();
            });
        });

        describe('parse() - Year Calibration', () => {
            it('should calibrate year when date is in future', () => {
                const futureDate = new Date();
                futureDate.setFullYear(futureDate.getFullYear() + 2);
                const futureStr = `${futureDate.getDate()} Jan, 10:00`;

                const sync = new SyncTimestamp({ baseYear: 2024 });
                const result = sync.parse(futureStr);

                // Should roll back to baseYear
                expect(result).toContain('2024-01-');
            });
        });
    });

    describe('alignTimestamp() - Standalone Function', () => {
        it('should parse date string to ISO format', () => {
            const result = alignTimestamp('24 Jan, 10:00');
            expect(result).toBe('2024-01-24T10:00:00.000Z');
        });

        it('should return null for invalid input', () => {
            expect(alignTimestamp('invalid')).toBeNull();
        });
    });

    // ========================================================================
    // TrajectoryParser Tests - Opening/Closing/Points
    // ========================================================================

    describe('TrajectoryParser.extractFullTrajectoryDOM()', () => {

        describe('Opening Odds Identification', () => {
            it('should extract Opening odds from separate section', () => {
                const parser = new TrajectoryParser();
                const html = `
                    <div class="mt-2 gap-1">
                        <div class="flex gap-1">
                            <div>24 Jan, 10:00</div>
                            <div>2.50</div>
                        </div>
                    </div>
                `;

                const result = parser.extractFullTrajectoryDOM(html);

                expect(result.valid).toBe(true);
                expect(result.trajectory).toHaveLength(1);
                expect(result.trajectory[0].type).toBe('Initial');
                expect(result.trajectory[0].value).toBe(2.50);
            });

            it('should mark earliest point as Initial if no Opening section', () => {
                const parser = new TrajectoryParser();
                const html = `
                    <div class="flex flex-row gap-3">
                        <div>
                            <div class="text-[10px]">24 Jan, 10:00</div>
                        </div>
                        <div>
                            <div class="text-[10px]">2.50</div>
                        </div>
                    </div>
                `;

                const result = parser.extractFullTrajectoryDOM(html);

                expect(result.valid).toBe(true);
                expect(result.trajectory[0].type).toBe('Initial');
            });

            it('should handle Opening with "Opening" text detection', () => {
                const parser = new TrajectoryParser();
                const html = `
                    <div class="mt-2 gap-1">
                        <div>Opening odds:</div>
                        <div class="flex gap-1">
                            <div>24 Jan, 10:00</div>
                            <div>2.50</div>
                        </div>
                    </div>
                `;

                const result = parser.extractFullTrajectoryDOM(html);

                expect(result.valid).toBe(true);
                expect(result.trajectory[0].type).toBe('Initial');
            });
        });

        describe('Closing Odds Identification', () => {
            it('should identify Closing odds (latest point)', () => {
                const parser = new TrajectoryParser();
                const html = `
                    <div class="flex flex-row gap-3">
                        <div>
                            <div class="text-[10px]">24 Jan, 10:00</div>
                            <div class="text-[10px]">25 Jan, 11:00</div>
                        </div>
                        <div>
                            <div class="text-[10px]">2.50</div>
                            <div class="text-[10px]">2.40</div>
                        </div>
                    </div>
                `;

                const result = parser.extractFullTrajectoryDOM(html);

                expect(result.valid).toBe(true);
                expect(result.trajectory).toHaveLength(2);

                // First (earliest) is Initial
                expect(result.trajectory[0].type).toBe('Initial');

                // Last (latest) is Closing
                expect(result.trajectory[result.trajectory.length - 1].value).toBe(2.40);
            });
        });

        describe('Points Extraction', () => {
            it('should extract multiple trajectory points', () => {
                const parser = new TrajectoryParser();
                const html = `
                    <div class="flex flex-row gap-3">
                        <div>
                            <div class="text-[10px]">24 Jan, 10:00</div>
                            <div class="text-[10px]">24 Jan, 12:00</div>
                            <div class="text-[10px]">24 Jan, 14:00</div>
                        </div>
                        <div>
                            <div class="text-[10px]">2.50</div>
                            <div class="text-[10px]">2.45</div>
                            <div class="text-[10px]">2.40</div>
                        </div>
                    </div>
                `;

                const result = parser.extractFullTrajectoryDOM(html);

                expect(result.valid).toBe(true);
                expect(result.trajectory).toHaveLength(3);
                expect(result.trajectory[0].value).toBe(2.50);
                expect(result.trajectory[1].value).toBe(2.45);
                expect(result.trajectory[2].value).toBe(2.40);
            });
        });

        describe('Edge Cases - Single Point', () => {
            it('should handle single point trajectory', () => {
                const parser = new TrajectoryParser();
                const html = `
                    <div class="flex flex-row gap-3">
                        <div>
                            <div class="text-[10px]">24 Jan, 10:00</div>
                        </div>
                        <div>
                            <div class="text-[10px]">2.50</div>
                        </div>
                    </div>
                `;

                const result = parser.extractFullTrajectoryDOM(html);

                expect(result.valid).toBe(true);
                expect(result.trajectory).toHaveLength(1);
                expect(result.trajectory[0].type).toBe('Initial');
                expect(result.quality_score).toBe('skeleton');
            });
        });

        describe('Edge Cases - No Data', () => {
            it('should return empty trajectory for invalid HTML', () => {
                const parser = new TrajectoryParser();
                const result = parser.extractFullTrajectoryDOM('');

                expect(result.valid).toBe(false);
                expect(result.trajectory).toHaveLength(0);
                expect(result.warning).toBeDefined();
            });

            it('should return empty trajectory for null input', () => {
                const parser = new TrajectoryParser();
                const result = parser.extractFullTrajectoryDOM(null);

                expect(result.valid).toBe(false);
                expect(result.trajectory).toHaveLength(0);
            });

            it('should return empty trajectory for non-string input', () => {
                const parser = new TrajectoryParser();
                const result = parser.extractFullTrajectoryDOM({});

                expect(result.valid).toBe(false);
                expect(result.trajectory).toHaveLength(0);
            });
        });

        describe('Quality Score Calculation', () => {
            it('should return POOR quality for < 3 points', () => {
                const parser = new TrajectoryParser();
                const html = `
                    <div class="flex flex-row gap-3">
                        <div>
                            <div class="text-[10px]">24 Jan, 10:00</div>
                            <div class="text-[10px]">24 Jan, 12:00</div>
                        </div>
                        <div>
                            <div class="text-[10px]">2.50</div>
                            <div class="text-[10px]">2.45</div>
                        </div>
                    </div>
                `;

                const result = parser.extractFullTrajectoryDOM(html);

                expect(result.quality).toBe('POOR');
                expect(result.quality_score).toBe('skeleton');
            });

            it('should return GOOD quality for 3-4 points', () => {
                const parser = new TrajectoryParser();
                let html = '<div class="flex flex-row gap-3"><div>';
                for (let i = 0; i < 3; i++) {
                    html += `<div class="text-[10px]">24 Jan, ${10 + i}:00</div>`;
                }
                html += '</div><div>';
                for (let i = 0; i < 3; i++) {
                    html += `<div class="text-[10px]">${(2.5 + i * 0.1).toFixed(2)}</div>`;
                }
                html += '</div></div>';

                const result = parser.extractFullTrajectoryDOM(html);

                expect(result.quality).toBe('GOOD');
                expect(result.quality_score).toBe('partial');
            });

            it('should return EXCELLENT quality for >= 5 points', () => {
                const parser = new TrajectoryParser();
                let html = '<div class="flex flex-row gap-3"><div>';
                for (let i = 0; i < 5; i++) {
                    html += `<div class="text-[10px]">24 Jan, ${10 + i}:00</div>`;
                }
                html += '</div><div>';
                for (let i = 0; i < 5; i++) {
                    html += `<div class="text-[10px]">${(2.5 + i * 0.1).toFixed(2)}</div>`;
                }
                html += '</div></div>';

                const result = parser.extractFullTrajectoryDOM(html);

                expect(result.quality).toBe('EXCELLENT');
                expect(result.quality_score).toBe('complete');
            });
        });
    });

    // ========================================================================
    // TrajectoryParser.calculatePayout() Tests
    // ========================================================================

    describe('TrajectoryParser.calculatePayout()', () => {
        it('should delegate to PayoutCalculator.calculate()', () => {
            const parser = new TrajectoryParser();
            const result = parser.calculatePayout(2.0, 3.5, 4.0);
            expect(result).toBeCloseTo(91.53, 1);
        });

        it('should return null for invalid odds', () => {
            const parser = new TrajectoryParser();
            expect(parser.calculatePayout(0, 3.5, 4.0)).toBeNull();
        });
    });

    describe('TrajectoryParser.calculatePayoutFromObject()', () => {
        it('should calculate from odds object', () => {
            const parser = new TrajectoryParser();
            const odds = { home: 2.0, draw: 3.5, away: 4.0 };
            const result = parser.calculatePayoutFromObject(odds);
            expect(result).toBeCloseTo(91.53, 1);
        });
    });

    // ========================================================================
    // TrajectoryParser.validateTrajectory() Tests
    // ========================================================================

    describe('TrajectoryParser.validateTrajectory()', () => {
        it('should return valid for healthy trajectory', () => {
            const parser = new TrajectoryParser();
            const trajectory = [
                { time: '2024-01-24T10:00:00.000Z', value: 2.50 },
                { time: '2024-01-24T12:00:00.000Z', value: 2.40 }
            ];

            const result = parser.validateTrajectory(trajectory);

            expect(result.valid).toBe(true);
            expect(result.initial).toBe(2.50);
            expect(result.current).toBe(2.40);
            expect(result.hasDrift).toBe(true);
        });

        it('should return invalid for empty trajectory', () => {
            const parser = new TrajectoryParser();
            const result = parser.validateTrajectory([]);

            expect(result.valid).toBe(false);
            expect(result.error).toBe('Trajectory is empty');
        });

        it('should return invalid for single point', () => {
            const parser = new TrajectoryParser();
            const trajectory = [
                { time: '2024-01-24T10:00:00.000Z', value: 2.50 }
            ];

            const result = parser.validateTrajectory(trajectory);

            expect(result.valid).toBe(false);
            expect(result.error).toContain('Insufficient points');
        });

        it('should detect no drift for identical values', () => {
            const parser = new TrajectoryParser();
            const trajectory = [
                { time: '2024-01-24T10:00:00.000Z', value: 2.50 },
                { time: '2024-01-24T12:00:00.000Z', value: 2.50 }
            ];

            const result = parser.validateTrajectory(trajectory);

            expect(result.valid).toBe(true);
            expect(result.hasDrift).toBe(false);
        });
    });

    // ========================================================================
    // Integration Tests - Full Workflow
    // ========================================================================

    describe('Integration Tests - Full Workflow', () => {
        it('should extract Opening/Closing/Points from complete HTML', () => {
            const parser = new TrajectoryParser();
            const html = `
                <div class="mt-2 gap-1">
                    <div>Opening odds:</div>
                    <div class="flex gap-1">
                        <div>24 Jan, 09:00</div>
                        <div>2.60</div>
                    </div>
                </div>
                <div class="flex flex-row gap-3">
                    <div>
                        <div class="text-[10px]">24 Jan, 10:00</div>
                        <div class="text-[10px]">24 Jan, 12:00</div>
                        <div class="text-[10px]">24 Jan, 14:00</div>
                    </div>
                    <div>
                        <div class="text-[10px]">2.55</div>
                        <div class="text-[10px]">2.50</div>
                        <div class="text-[10px]">2.45</div>
                    </div>
                </div>
            `;

            const result = parser.extractFullTrajectoryDOM(html);

            // Validation
            expect(result.valid).toBe(true);
            expect(result.trajectory).toHaveLength(4); // 1 Opening + 3 Historical

            // Opening
            expect(result.trajectory[0].type).toBe('Initial');
            expect(result.trajectory[0].value).toBe(2.60);

            // Closing (last point)
            const closing = result.trajectory[result.trajectory.length - 1];
            expect(closing.value).toBe(2.45);

            // Quality
            expect(result.quality).toBe('EXCELLENT');
            expect(result.quality_score).toBe('complete');
        });

        it('should handle HTML with payout data', () => {
            const parser = new TrajectoryParser();
            const semanticData = [
                {
                    provider: 'Pinnacle',
                    home: 2.0,
                    draw: 3.5,
                    away: 4.0,
                    timestamp: '2024-01-24T10:00:00.000Z'
                }
            ];

            const result = parser.parseDOMExtractedData(semanticData);

            expect(result.valid).toBe(true);
            expect(result.providers).toHaveLength(1);
            expect(result.providers[0].payout).toBeCloseTo(91.53, 1);
        });
    });
});
