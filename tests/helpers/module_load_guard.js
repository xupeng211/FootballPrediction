'use strict';

// lifecycle: permanent；供单元测试规范化 Module._load 请求，避免 clone 父目录污染模块匹配。

const path = require('node:path');

function normalizeModuleRequest(request, projectRoot) {
    const rawRequest = String(request ?? '');
    if (!path.isAbsolute(rawRequest)) {
        return rawRequest;
    }

    const root = path.resolve(projectRoot);
    const resolvedRequest = path.resolve(rawRequest);
    const relativeRequest = path.relative(root, resolvedRequest);
    const isInsideProject =
        relativeRequest &&
        relativeRequest !== '..' &&
        !relativeRequest.startsWith(`..${path.sep}`) &&
        !path.isAbsolute(relativeRequest);

    return isInsideProject
        ? relativeRequest.split(path.sep).join('/')
        : path.basename(resolvedRequest);
}

function matchesForbiddenImport(request, projectRoot, pattern) {
    pattern.lastIndex = 0;
    return pattern.test(normalizeModuleRequest(request, projectRoot));
}

module.exports = {
    matchesForbiddenImport,
    normalizeModuleRequest,
};
