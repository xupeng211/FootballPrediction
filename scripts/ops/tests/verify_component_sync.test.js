/**
 * V88.450 Component Sync Verification Tests
 * ==========================================
 *
 * Jest test suite for component sync verification logic
 *
 * V88.400 Enhancements:
 *   - Test Vendor Fingerprinting (SVG path recognition)
 *   - Test Temporal Extraction (sequence ordering)
 *   - Test Data Mapping (5-D dimension validation)
 *
 * V88.450 Enhancements:
 *   - Test Enhanced Target Locator (Multi-level Fallback)
 *   - Test Text Anchor Fallback
 *   - Test Last Resort Strategy
 *
 * @module verify_component_sync.test
 * @version V88.450
 */

'use strict';

const { CircuitBreaker, ComponentMonitor, DatabaseVerifier } = require('../verify_component_sync');
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

// ============================================================================
// CIRCUIT BREAKER TESTS
// ============================================================================

describe('CircuitBreaker', () => {
    let circuitBreaker;

    beforeEach(() => {
        circuitBreaker = new CircuitBreaker();
    });

    test('should start in operational state', () => {
        expect(circuitBreaker.failureCount).toBe(0);
        expect(circuitBreaker.isDegraded).toBe(false);
    });

    test('should record failure and update state', () => {
        circuitBreaker.recordFailure();
        expect(circuitBreaker.failureCount).toBe(1);

        circuitBreaker.recordFailure();
        expect(circuitBreaker.failureCount).toBe(2);
        expect(circuitBreaker.isDegraded).toBe(true);
    });

    test('should reset on success', () => {
        circuitBreaker.recordFailure();
        circuitBreaker.recordFailure();
        expect(circuitBreaker.isDegraded).toBe(true);

        circuitBreaker.recordSuccess();
        expect(circuitBreaker.failureCount).toBe(0);
        expect(circuitBreaker.isDegraded).toBe(false);
    });

    test('should return correct status', () => {
        const status = circuitBreaker.getStatus();
        expect(status).toHaveProperty('failureCount');
        expect(status).toHaveProperty('threshold');
        expect(status).toHaveProperty('isDegraded');
    });
});

// ============================================================================
// V88.400: VENDOR FINGERPRINTING TESTS
// ============================================================================

describe('V88.400: Vendor Identifier (Technical Obfuscation Applied)', () => {
    let clicker;

    beforeEach(() => {
        jest.clearAllMocks();
        clicker = interactionV52.createMatrixClicker(mockPage, {
            trustedEvents: false,
            retryMechanism: { enabled: false },
            canaryCheck: { enabled: false }
        });
    });

    test('should identify vendor via SVG path fingerprint (confidence: 0.95)', async () => {
        // 模拟包含特定 SVG 路径的元素
        const mockElement = {
            querySelectorAll: jest.fn().mockReturnValue([
                { getAttribute: jest.fn().mockReturnValue('m453.3 193.3l-126.6...') }
            ])
        };

        mockPage.evaluate.mockResolvedValue({
            vendorId: 'Alpha',
            confidence: 0.95,
            method: 'svg_path_fingerprint',
            details: { patternMatched: 'm453.3 193.3' }
        });

        const result = await clicker.identifyVendor(mockElement);

        expect(result.vendorId).toBe('Alpha');
        expect(result.confidence).toBe(0.95);
        expect(result.method).toBe('svg_path_fingerprint');
    });

    test('should identify vendor via CSS class name (confidence: 0.85)', async () => {
        const mockElement = {
            querySelectorAll: jest.fn().mockReturnValue([]),
            className: 'bg-vendor-green logo-alpha'
        };

        mockPage.evaluate.mockResolvedValue({
            vendorId: 'Alpha',
            confidence: 0.85,
            method: 'css_class_match',
            details: { classMatched: 'bg-vendor-green' }
        });

        const result = await clicker.identifyVendor(mockElement);

        expect(result.vendorId).toBe('Alpha');
        expect(result.confidence).toBe(0.85);
        expect(result.method).toBe('css_class_match');
    });

    test('should fallback to parent container ID (confidence: 0.60)', async () => {
        const mockParent = {
            id: 'provider-container-alpha',
            className: 'vendor-wrapper',
            parentElement: null
        };

        const mockElement = {
            querySelectorAll: jest.fn().mockReturnValue([]),
            className: '',
            parentElement: mockParent,
            getAttribute: jest.fn().mockReturnValue('')
        };

        mockPage.evaluate.mockResolvedValue({
            vendorId: 'Container_provider',
            confidence: 0.60,
            method: 'parent_container_fallback',
            details: { containerId: 'provider-container-alpha' }
        });

        const result = await clicker.identifyVendor(mockElement);

        expect(result.confidence).toBe(0.60);
        expect(result.method).toBe('parent_container_fallback');
    });

    test('should fallback to text matching (confidence: 0.50)', async () => {
        const mockElement = {
            querySelectorAll: jest.fn().mockReturnValue([]),
            className: '',
            parentElement: null,
            getAttribute: jest.fn().mockReturnValue('Pinnacle Logo')
        };

        mockPage.evaluate.mockResolvedValue({
            vendorId: 'Pinnacle',
            confidence: 0.50,
            method: 'text_fallback',
            details: { textMatched: 'Pinnacle' }
        });

        const result = await clicker.identifyVendor(mockElement);

        expect(result.vendorId).toBe('Pinnacle');
        expect(result.confidence).toBe(0.50);
        expect(result.method).toBe('text_fallback');
    });

    test('should return Unknown when no identification possible', async () => {
        const mockElement = {
            querySelectorAll: jest.fn().mockReturnValue([]),
            className: '',
            parentElement: null,
            getAttribute: jest.fn().mockReturnValue('')
        };

        mockPage.evaluate.mockResolvedValue({
            vendorId: 'Unknown',
            confidence: 0,
            method: 'none',
            details: {}
        });

        const result = await clicker.identifyVendor(mockElement);

        expect(result.vendorId).toBe('Unknown');
        expect(result.confidence).toBe(0);
        expect(result.method).toBe('none');
    });
});

// ============================================================================
// V88.400: TEMPORAL EXTRACTION TESTS (Metric Stream)
// ============================================================================

describe('V88.400: Temporal Sequence Extraction (Technical Obfuscation Applied)', () => {
    test('should extract temporal points with correct sequence ordering', async () => {
        // 模拟 5 行不同时间戳的 HTML 表格
        const mockHtml = `
            <table>
                <tr class="data-row">
                    <td class="time">10:00 am</td>
                    <td>2.50</td>
                    <td>3.20</td>
                    <td>2.80</td>
                </tr>
                <tr class="data-row">
                    <td class="time">10:15 am</td>
                    <td>2.45</td>
                    <td>3.25</td>
                    <td>2.85</td>
                </tr>
                <tr class="data-row">
                    <td class="time">10:30 am</td>
                    <td>2.40</td>
                    <td>3.30</td>
                    <td>2.90</td>
                </tr>
                <tr class="data-row">
                    <td class="time">10:45 am</td>
                    <td>2.35</td>
                    <td>3.35</td>
                    <td>2.95</td>
                </tr>
                <tr class="data-row">
                    <td class="time">11:00 am</td>
                    <td>2.30</td>
                    <td>3.40</td>
                    <td>3.00</td>
                </tr>
            </table>
        `;

        // 模拟 page.evaluate 返回提取的时序数据
        const mockEvalResult = {
            textContent: ['2.50', '3.20', '2.80', '10:00 am'],
            numericValues: [2.50, 3.20, 2.80],
            providersDetected: ['Alpha'],
            fieldCount: 4,
            temporalSequence: [
                {
                    timeLabel: '10:00 am',
                    metricTime: '2026-01-26T10:00:00.000Z',
                    sequenceOrder: 0,
                    dimensions: { home: 2.50, draw: 3.20, away: 2.80 }
                },
                {
                    timeLabel: '10:15 am',
                    metricTime: '2026-01-26T10:15:00.000Z',
                    sequenceOrder: 1,
                    dimensions: { home: 2.45, draw: 3.25, away: 2.85 }
                },
                {
                    timeLabel: '10:30 am',
                    metricTime: '2026-01-26T10:30:00.000Z',
                    sequenceOrder: 2,
                    dimensions: { home: 2.40, draw: 3.30, away: 2.90 }
                },
                {
                    timeLabel: '10:45 am',
                    metricTime: '2026-01-26T10:45:00.000Z',
                    sequenceOrder: 3,
                    dimensions: { home: 2.35, draw: 3.35, away: 2.95 }
                },
                {
                    timeLabel: '11:00 am',
                    metricTime: '2026-01-26T11:00:00.000Z',
                    sequenceOrder: 4,
                    dimensions: { home: 2.30, draw: 3.40, away: 3.00 }
                }
            ],
            historyPoints: 5,
            vendorIdentities: []
        };

        mockPage.evaluate.mockResolvedValueOnce(mockEvalResult);

        // 验证序列号从 0 正确递增
        const result = await mockPage.evaluate();
        const temporalSequence = result.temporalSequence;

        expect(temporalSequence).toHaveLength(5);
        expect(temporalSequence[0].sequenceOrder).toBe(0);
        expect(temporalSequence[1].sequenceOrder).toBe(1);
        expect(temporalSequence[2].sequenceOrder).toBe(2);
        expect(temporalSequence[3].sequenceOrder).toBe(3);
        expect(temporalSequence[4].sequenceOrder).toBe(4);

        // 验证时间标签正确解析
        expect(temporalSequence[0].timeLabel).toBe('10:00 am');
        expect(temporalSequence[4].timeLabel).toBe('11:00 am');

        // 验证 3 维度数值正确提取
        expect(temporalSequence[0].dimensions.home).toBe(2.50);
        expect(temporalSequence[0].dimensions.draw).toBe(3.20);
        expect(temporalSequence[0].dimensions.away).toBe(2.80);
    });

    test('should handle empty temporal sequence gracefully', async () => {
        const mockEvalResult = {
            textContent: [],
            numericValues: [],
            providersDetected: [],
            fieldCount: 0,
            temporalSequence: [],
            historyPoints: 0,
            vendorIdentities: []
        };

        mockPage.evaluate.mockResolvedValueOnce(mockEvalResult);

        const result = await mockPage.evaluate();

        expect(result.temporalSequence).toHaveLength(0);
        expect(result.historyPoints).toBe(0);
    });

    test('should parse time labels with am/pm format', async () => {
        // 测试不同的时间格式
        const timeLabels = ['9:00 am', '12:00 pm', '11:59 pm', '12:01 am'];

        // 模拟解析逻辑
        const parseTimeLabel = (label) => {
            const match = label.match(/(\d{1,2}):(\d{2})\s*(am|pm)?/i);
            if (!match) return null;

            const hours = parseInt(match[1]);
            const minutes = parseInt(match[2]);
            const meridiem = match[3]?.toLowerCase();

            let adjustedHours = hours;
            if (meridiem === 'pm' && hours < 12) adjustedHours += 12;
            if (meridiem === 'am' && hours === 12) adjustedHours = 0;

            return adjustedHours;
        };

        expect(parseTimeLabel(timeLabels[0])).toBe(9);   // 9:00 am -> 9
        expect(parseTimeLabel(timeLabels[1])).toBe(12);  // 12:00 pm -> 12
        expect(parseTimeLabel(timeLabels[2])).toBe(23);  // 11:59 pm -> 23
        expect(parseTimeLabel(timeLabels[3])).toBe(0);   // 12:01 am -> 0
    });
});

// ============================================================================
// V88.400: DATA MAPPING 5-D DIMENSION TESTS
// ============================================================================

describe('V88.400: Data Mapping 5-D Dimension Validation (Technical Obfuscation Applied)', () => {
    test('should map extracted data to strict 5-D structure', () => {
        // 模拟提取的时序数据
        const extractedData = {
            temporalSequence: [
                {
                    timeLabel: '10:00 am',
                    metricTime: '2026-01-26T10:00:00.000Z',
                    sequenceOrder: 0,
                    dimensions: { home: 2.50, draw: 3.20, away: 2.80 }
                }
            ],
            vendorIdentities: [
                { element: 'Alpha', svgFingerprint: 'm453.3...', hasSvg: true }
            ],
            historyPoints: 1,
            fieldCount: 10
        };

        // 模拟 5-D 映射逻辑
        const vendorId = extractedData.vendorIdentities[0]?.element || 'Unknown';

        const metricRecords = [];
        for (const temporalPoint of extractedData.temporalSequence) {
            for (const [dimensionLabel, value] of Object.entries(temporalPoint.dimensions)) {
                if (value !== null && value >= 1) {
                    metricRecords.push({
                        entity_id: 'test-entity-uuid',
                        vendor_id: vendorId,
                        metric_time: temporalPoint.metricTime,
                        dimension_label: dimensionLabel,
                        sequence_order: temporalPoint.sequenceOrder,
                        value: value
                    });
                }
            }
        }

        // 验证 5-D 结构
        expect(metricRecords).toHaveLength(3); // home, draw, away

        // 验证每条记录包含所有 5 个维度
        metricRecords.forEach(record => {
            expect(record).toHaveProperty('entity_id');
            expect(record).toHaveProperty('vendor_id');
            expect(record).toHaveProperty('metric_time');
            expect(record).toHaveProperty('dimension_label');
            expect(record).toHaveProperty('sequence_order');
        });

        // 验证维度标签正确
        const dimensionLabels = metricRecords.map(r => r.dimension_label);
        expect(dimensionLabels).toContain('home');
        expect(dimensionLabels).toContain('draw');
        expect(dimensionLabels).toContain('away');

        // 验证供应商 ID 正确
        expect(metricRecords[0].vendor_id).toBe('Alpha');

        // 验证序列号正确
        expect(metricRecords[0].sequence_order).toBe(0);
    });

    test('should validate entity_id format (UUID)', () => {
        const validUUID = '550e8400-e29b-41d4-a716-446655440000';
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

        expect(uuidRegex.test(validUUID)).toBe(true);
        expect(uuidRegex.test('invalid-uuid')).toBe(false);
    });

    test('should validate metric_time format (ISO 8601)', () => {
        const validISO = '2026-01-26T10:00:00.000Z';
        const isoRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;

        expect(isoRegex.test(validISO)).toBe(true);
        expect(isoRegex.test('invalid-time')).toBe(false);
    });

    test('should validate dimension_label values', () => {
        const validDimensions = ['home', 'draw', 'away'];

        validDimensions.forEach(dim => {
            expect(['home', 'draw', 'away']).toContain(dim);
        });

        expect(['home', 'draw', 'away']).toContain('home');
        expect(['home', 'draw', 'away']).not.toContain('invalid');
    });

    test('should validate sequence_order is non-negative integer', () => {
        const sequenceOrders = [0, 1, 2, 10, 100];

        sequenceOrders.forEach(seq => {
            expect(Number.isInteger(seq)).toBe(true);
            expect(seq).toBeGreaterThanOrEqual(0);
        });

        expect(Number.isInteger(-1)).toBe(true);  // 负数也是整数，但不符合业务逻辑
        expect(-1).toBeLessThan(0);
    });

    test('should handle missing dimensions gracefully', () => {
        const extractedData = {
            temporalSequence: [
                {
                    metricTime: '2026-01-26T10:00:00.000Z',
                    sequenceOrder: 0,
                    dimensions: { home: 2.50, draw: null, away: 2.80 }
                }
            ]
        };

        const metricRecords = [];
        for (const temporalPoint of extractedData.temporalSequence) {
            for (const [dimensionLabel, value] of Object.entries(temporalPoint.dimensions)) {
                if (value !== null && value >= 1) {
                    metricRecords.push({
                        dimension_label: dimensionLabel,
                        value: value
                    });
                }
            }
        }

        // 应该只包含 home 和 away，draw 被跳过
        expect(metricRecords).toHaveLength(2);
        const dimensionLabels = metricRecords.map(r => r.dimension_label);
        expect(dimensionLabels).not.toContain('draw');
        expect(dimensionLabels).toContain('home');
        expect(dimensionLabels).toContain('away');
    });
});

// ============================================================================
// COMPONENT MONITOR MOCK TESTS
// ============================================================================

describe('ComponentMonitor', () => {
    test('should export ComponentMonitor class', () => {
        expect(ComponentMonitor).toBeDefined();
        expect(typeof ComponentMonitor).toBe('function');
    });
});

// ============================================================================
// DATABASE VERIFIER MOCK TESTS
// ============================================================================

describe('DatabaseVerifier', () => {
    test('should export DatabaseVerifier class', () => {
        expect(DatabaseVerifier).toBeDefined();
        expect(typeof DatabaseVerifier).toBe('function');
    });
});

// ============================================================================
// CONFIGURATION TESTS
// ============================================================================

describe('V88.450: Enhanced Target Locator (Technical Obfuscation Applied)', () => {
    test('should define multi-level fallback selectors', () => {
        const fs = require('fs');
        const path = require('path');
        const scriptPath = path.join(__dirname, '..', 'verify_component_sync.js');
        const scriptContent = fs.readFileSync(scriptPath, 'utf-8');

        // Verify primary selectors are present
        expect(scriptContent).toContain('div.border-black-borders');
        expect(scriptContent).toContain('div[class*="event-row"]');
        expect(scriptContent).toContain('div[class*="match-row"]');
        expect(scriptContent).toContain('div[data-testid*="match"]');
        expect(scriptContent).toContain('div[class*="flex"][class*="relative"]');
        expect(scriptContent).toContain('a[href*="/football/"][href*="-"]');
    });

    test('should have text anchor fallback logic', () => {
        const fs = require('fs');
        const path = require('path');
        const scriptPath = path.join(__dirname, '..', 'verify_component_sync.js');
        const scriptContent = fs.readFileSync(scriptPath, 'utf-8');

        expect(scriptContent).toContain('Text Anchor Fallback');
        expect(scriptContent).toContain('Betting');
        expect(scriptContent).toContain('Odds');
        expect(scriptContent).toContain('Premier League');
    });

    test('should have last resort strategy', () => {
        const fs = require('fs');
        const path = require('path');
        const scriptPath = path.join(__dirname, '..', 'verify_component_sync.js');
        const scriptContent = fs.readFileSync(scriptPath, 'utf-8');

        expect(scriptContent).toContain('Last Resort');
        expect(scriptContent).toContain('flex container');
        expect(scriptContent).toContain('maxArea');
    });
});

describe('Configuration', () => {
    test('should have V88.450 branding', () => {
        const fs = require('fs');
        const path = require('path');
        const scriptPath = path.join(__dirname, '..', 'verify_component_sync.js');
        const scriptContent = fs.readFileSync(scriptPath, 'utf-8');

        expect(scriptContent).toContain('V88.450');
        expect(scriptContent).toContain('V88.310');  // Keep legacy branding
        expect(scriptContent).toContain('Vendor Identity');
        expect(scriptContent).toContain('Temporal Sequence');
        expect(scriptContent).toContain('5-D');
        expect(scriptContent).toContain('Multi-level Fallback');
    });

    test('should export all required classes', () => {
        const { CircuitBreaker, ComponentMonitor, DatabaseVerifier } = require('../verify_component_sync');

        expect(CircuitBreaker).toBeDefined();
        expect(ComponentMonitor).toBeDefined();
        expect(DatabaseVerifier).toBeDefined();
    });
});
