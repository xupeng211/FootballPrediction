/**
 * SurgicalInteraction ForceTrigger Tests
 * =====================================
 * 
 * Tests for V169.100 ForceTrigger fallback logic.
 */

const { SurgicalInteraction } = require('../../src/infrastructure/engines/services/SurgicalInteraction');

// Mock Playwright Page
const createMockPage = (options = {}) => ({
    mouse: {
        move: jest.fn().mockResolvedValue(undefined)
    },
    waitForTimeout: jest.fn().mockResolvedValue(undefined),
    dispatchEvent: jest.fn().mockResolvedValue(undefined),
    $: jest.fn().mockResolvedValue({
        evaluate: jest.fn().mockResolvedValue(undefined),
        boundingBox: jest.fn().mockResolvedValue({ x: 100, y: 100, width: 50, height: 20 })
    }),
    evaluate: jest.fn().mockImplementation((fn, ...args) => {
        if (typeof fn === 'function') {
            return fn(...args);
        }
        // Handle specific evaluation strings if needed
        if (options.tooltipVisible) return true;
        return options.evalResult;
    }),
    ...options
});

describe('SurgicalInteraction ForceTrigger', () => {
    let page;
    let surgical;

    beforeEach(() => {
        page = createMockPage();
        surgical = new SurgicalInteraction(page, { logLevel: 'silent' });
        // Silence info/warn/error for tests
        surgical.info = jest.fn();
        surgical.warn = jest.fn();
        surgical.error = jest.fn();
    });

    test('should call dispatchEvent when _forceTriggerTooltip is invoked', async () => {
        const selector = '.test-cell';
        await surgical._forceTriggerTooltip(selector);
        
        expect(page.dispatchEvent).toHaveBeenCalledWith(selector, 'mouseover');
        expect(page.dispatchEvent).toHaveBeenCalledWith(selector, 'mouseenter');
    });

    test('should attempt ForceTrigger as fallback in _captureTrajectories when tooltip is missing', async () => {
        const targets = [{ provider: 'bet365', selector: '.bet365-cell', instantValue: 1.5 }];
        
        // Mock _ensureTooltipVisible to return false initially, then true after ForceTrigger
        let callCount = 0;
        surgical._ensureTooltipVisible = jest.fn().mockImplementation(() => {
            callCount++;
            return callCount > 1; // Success on second call (after force trigger)
        });

        // Mock _forceTriggerTooltip
        surgical._forceTriggerTooltip = jest.fn().mockResolvedValue(undefined);
        
        // Mock extract tooltip text
        page.evaluate.mockResolvedValueOnce(null) // for first ensure check inside loop
                     .mockResolvedValueOnce('ODDS MOVEMENT\n10:00 1.50') // for tooltip extraction
        
        // Mock handleOverlays etc if needed, but we are testing _captureTrajectories
        await surgical._captureTrajectories(targets);

        expect(surgical._forceTriggerTooltip).toHaveBeenCalledWith('.bet365-cell');
        expect(surgical._ensureTooltipVisible).toHaveBeenCalled();
    });
});
