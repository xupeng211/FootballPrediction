/**
 * V146.000 React SPA Index Configuration
 * =========================================
 *
 * Index-based targeting configuration for React SPA architecture.
 * Since data-type attributes are no longer available, we use
 * position-based mapping to identify Home/Draw/Away cells.
 *
 * @module config/ReactIndexConfig
 * @version V146.000
 * @since 2026-01-28
 * @author Principal Frontend Reverse Engineer
 */

'use strict';

/**
 * V146.000: Index offset mapping for axis identification
 *
 * React SPA页面结构：
 * - 每行包含3个赔率单元格（按顺序：Home, Draw, Away）
 * - 通过单元格在行内的索引位置来识别类型
 * - Index 0 -> Home (主胜)
 * - Index 1 -> Draw (平局)
 * - Index 2 -> Away (客胜)
 */
const AXIS_INDEX_OFFSETS = {
    home: 0,   // 第1个单元格
    draw: 1,   // 第2个单元格
    away: 2    // 第3个单元格
};

/**
 * V146.000: Dimension code mapping (legacy compatibility)
 * Maps internal axis names to legacy dimension codes
 */
const AXIS_DIMENSIONS = {
    home: 'A',
    draw: 'B',
    away: 'C'
};

/**
 * V146.000: Cells per row in React SPA layout
 * Used for validation and bounds checking
 */
const CELLS_PER_ROW = 3;

/**
 * V146.000: React rendering wait configuration
 */
const REACT_RENDER_CONFIG = {
    // Maximum time to wait for odds cells to render (milliseconds)
    waitForSelectorTimeout: 10000,
    // Polling interval for checking selector availability (milliseconds)
    pollingInterval: 100,
    // State: whether cells are expected to be present
    expectCellsPresent: true
};

/**
 * V146.000: Get index offset for a given axis
 * @param {string} axisName - Axis name ('home', 'draw', 'away')
 * @returns {number|null} Index offset or null if invalid
 */
function getIndexOffset(axisName) {
    // Debug: log axisName and AXIS_INDEX_OFFSETS
    if (typeof AXIS_INDEX_OFFSETS === 'undefined') {
        console.error('[V146.000] ❌ AXIS_INDEX_OFFSETS is undefined!');
        return null;
    }
    const offset = AXIS_INDEX_OFFSETS[axisName];
    if (offset === undefined) {
        console.error(`[V146.000] ❌ No offset found for axis: ${axisName}`);
        console.error(`[V146.000] Available axes:`, Object.keys(AXIS_INDEX_OFFSETS));
        return null;
    }
    return offset;
}

/**
 * V146.000: Get dimension code for a given axis
 * @param {string} axisName - Axis name ('home', 'draw', 'away')
 * @returns {string|null} Dimension code ('A', 'B', 'C') or null if invalid
 */
function getDimensionCode(axisName) {
    return AXIS_DIMENSIONS[axisName] || null;
}

/**
 * V146.000: Validate row structure
 * @param {number} cellCount - Number of cells in the row
 * @returns {boolean} True if row structure is valid
 */
function validateRowStructure(cellCount) {
    return cellCount >= CELLS_PER_ROW;
}

/**
 * V146.000: Get cell index for axis in a row
 * @param {string} axisName - Axis name ('home', 'draw', 'away')
 * @param {number} rowIndex - Row index (for multi-row layouts)
 * @returns {number} Absolute cell index
 */
function getCellIndex(axisName, rowIndex = 0) {
    const offset = getIndexOffset(axisName);
    if (offset === null) return -1;
    return rowIndex * CELLS_PER_ROW + offset;
}

module.exports = {
    AXIS_INDEX_OFFSETS,
    AXIS_DIMENSIONS,
    CELLS_PER_ROW,
    REACT_RENDER_CONFIG,
    getIndexOffset,
    getDimensionCode,
    validateRowStructure,
    getCellIndex
};
