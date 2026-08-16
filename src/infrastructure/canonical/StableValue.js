'use strict';

// lifecycle: permanent
// 跨领域复用的纯值序列化与 SHA-256 工具。此模块不读取文件、不访问网络、
// 不连接数据库，避免纯语义引擎依赖具体 provider/inventory 实现。

const crypto = require('node:crypto');

function sha256Text(value) {
    return crypto.createHash('sha256').update(String(value), 'utf8').digest('hex');
}

function stableCanonicalize(value) {
    if (Array.isArray(value)) return value.map(stableCanonicalize);
    if (value && typeof value === 'object') {
        return Object.keys(value)
            .sort()
            .reduce((out, key) => {
                out[key] = stableCanonicalize(value[key]);
                return out;
            }, {});
    }
    return value;
}

function stableStringify(value) {
    return JSON.stringify(stableCanonicalize(value));
}

module.exports = { sha256Text, stableStringify };
