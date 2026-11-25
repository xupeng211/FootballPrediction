'use strict';

// lifecycle: permanent；按隔离记录汇总原因代码。

function summarizeQuarantineReasons(quarantine) {
    const counts = new Map();
    for (const { reasons } of quarantine) {
        for (const reason of new Set(reasons)) {
            counts.set(reason, (counts.get(reason) ?? 0) + 1);
        }
    }

    const sortedReasons = [...counts.keys()].sort();
    return Object.fromEntries(sortedReasons.map(reason => [reason, counts.get(reason)]));
}

module.exports = { summarizeQuarantineReasons };
