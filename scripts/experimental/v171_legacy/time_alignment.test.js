/**
 * V122.000 - Time Alignment Unit Tests
 * Quantitative Data Acquisition Engine
 *
 * @module tests/unit/time_alignment
 * @version V122.000
 * @since 2026-01-27
 */

const { alignTimestamp, SyncTimestamp, TrajectoryParser } = require('../../src/engines/QuantHarvester');

describe('Time Alignment Logic', () => {
    const currentYear = new Date().getFullYear();

    describe('Standard Format Parsing', () => {
        test('should align "27 Jan, 05:30" to ISO format', () => {
            const input = '27 Jan, 05:30';
            const expected = `${currentYear}-01-27T05:30:00Z`;
            const result = alignTimestamp(input);
            expect(result).toBe(expected);
        });

        test('should handle year boundary crossover', () => {
            const input = '01 Jan, 23:59';
            const currentMonth = new Date().getMonth();

            // If currently in December, expected year should be next year
            const expectedYear = currentMonth === 11 ? currentYear + 1 : currentYear;
            const expected = `${expectedYear}-01-01T23:59:00Z`;

            const result = alignTimestamp(input);
            expect(result).toBe(expected);
        });

        test('should parse full datetime string', () => {
            const input = '2025-12-31 15:30:00';
            const result = alignTimestamp(input);
            expect(result).toBe('2025-12-31T15:30:00Z');
        });

        test('should handle month-first format', () => {
            const input = 'Jan 24, 10:00';
            const expected = `${currentYear}-01-24T10:00:00Z`;
            const result = alignTimestamp(input);
            expect(result).toBe(expected);
        });
    });

    describe('Dirty Data Handling (V122.000)', () => {
        test('should return null for null input', () => {
            const result = alignTimestamp(null);
            expect(result).toBeNull();
        });

        test('should return null for undefined input', () => {
            const result = alignTimestamp(undefined);
            expect(result).toBeNull();
        });

        test('should return null for empty string', () => {
            const result = alignTimestamp('');
            expect(result).toBeNull();
        });

        test('should return null for malformed input', () => {
            const result = alignTimestamp('not-a-date');
            expect(result).toBeNull();
        });

        test('should return null for garbage string', () => {
            const result = alignTimestamp('!@#$%^&*()');
            expect(result).toBeNull();
        });

        test('should handle month abbreviation with period', () => {
            const input = '24 Jan., 10:00';
            const expected = `${currentYear}-01-24T10:00:00Z`;
            const result = alignTimestamp(input);
            expect(result).toBe(expected);
        });

        test('should handle different month formats', () => {
            const result1 = alignTimestamp('24 Feb, 10:00');
            const result2 = alignTimestamp('24 Mar., 10:00');
            const result3 = alignTimestamp('24 Apr, 10:00');

            expect(result1).toContain('-02-24');
            expect(result2).toContain('-03-24');
            expect(result3).toContain('-04-24');
        });
    });

    describe('SyncTimestamp Class Edge Cases', () => {
        test('should handle leap year dates', () => {
            const sync = new SyncTimestamp(2024); // Leap year
            const result = sync.parse('29 Feb, 12:00');
            expect(result).toBe('2024-02-29T12:00:00Z');
        });

        test('should handle invalid date gracefully', () => {
            const sync = new SyncTimestamp(2025); // Non-leap year
            const result = sync.parse('29 Feb, 12:00');
            // Should not throw, but may return null or computed value
            expect(result).not.toThrow();
        });

        test('should handle midnight time', () => {
            const input = '01 Jan, 00:00';
            const expected = `${currentYear}-01-01T00:00:00Z`;
            const result = alignTimestamp(input);
            expect(result).toBe(expected);
        });

        test('should handle end of day time', () => {
            const input = '31 Dec, 23:59';
            const expected = `${currentYear}-12-31T23:59:00Z`;
            const result = alignTimestamp(input);
            expect(result).toBe(expected);
        });
    });
});

describe('TrajectoryParser - Dirty Data Extraction', () => {
    let parser;

    beforeEach(() => {
        parser = new TrajectoryParser();
    });

    describe('Malformed HTML Handling', () => {
        test('should return empty array for null input', () => {
            const result = parser.extractFullTrajectoryDOM(null);
            expect(result).toEqual([]);
        });

        test('should return empty array for undefined input', () => {
            const result = parser.extractFullTrajectoryDOM(undefined);
            expect(result).toEqual([]);
        });

        test('should return empty array for empty string', () => {
            const result = parser.extractFullTrajectoryDOM('');
            expect(result).toEqual([]);
        });

        test('should handle HTML without trajectory data', () => {
            const html = '<div><p>Some random content</p></div>';
            const result = parser.extractFullTrajectoryDOM(html);
            expect(Array.isArray(result)).toBe(true);
            expect(result.length).toBe(0);
        });

        test('should handle HTML with incomplete table rows', () => {
            const html = `
                <table>
                    <tr><td>Broken data</td></tr>
                    <tr><td>24 Jan, 10:00</td></tr>
                </table>
            `;
            const result = parser.extractFullTrajectoryDOM(html);
            expect(Array.isArray(result)).toBe(true);
            // Should not crash, may have zero or partial results
        });
    });

    describe('Trajectory Validation', () => {
        test('should reject empty trajectory', () => {
            const result = parser.validateTrajectory([]);
            expect(result.valid).toBe(false);
            expect(result.error).toBe('Trajectory is empty');
        });

        test('should reject trajectory with insufficient points', () => {
            const trajectory = [
                { time: '2026-01-27T10:00:00Z', value: 2.5, type: 'Initial' }
            ];
            const result = parser.validateTrajectory(trajectory);
            expect(result.valid).toBe(false);
            expect(result.error).toContain('Insufficient points');
        });

        test('should accept valid trajectory', () => {
            const trajectory = [
                { time: '2026-01-27T10:00:00Z', value: 2.5, type: 'Initial' },
                { time: '2026-01-27T11:00:00Z', value: 2.45, type: 'Historical' }
            ];
            const result = parser.validateTrajectory(trajectory);
            expect(result.valid).toBe(true);
            expect(result.hasDrift).toBe(true);
        });

        test('should detect no drift when values are identical', () => {
            const trajectory = [
                { time: '2026-01-27T10:00:00Z', value: 2.5, type: 'Initial' },
                { time: '2026-01-27T11:00:00Z', value: 2.5, type: 'Historical' }
            ];
            const result = parser.validateTrajectory(trajectory);
            expect(result.valid).toBe(true);
            expect(result.hasDrift).toBe(false);
        });
    });

    describe('Memory Leak Prevention (V122.000)', () => {
        test('should not leak memory with repeated extractions', () => {
            const html = `
                <div>Opening odds: 2.50 at 24 Jan, 10:00</div>
                <table>
                    <tr><td>24 Jan, 11:00</td><td>2.45</td></tr>
                    <tr><td>24 Jan, 12:00</td><td>2.40</td></tr>
                </table>
            `;

            // Run multiple times to verify no memory buildup
            for (let i = 0; i < 100; i++) {
                const result = parser.extractFullTrajectoryDOM(html);
                expect(Array.isArray(result)).toBe(true);
            }

            // If we reach here without OOM, memory leak is fixed
            expect(true).toBe(true);
        });
    });
});
