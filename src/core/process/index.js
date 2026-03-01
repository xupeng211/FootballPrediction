/**
 * 进程管理模块入口
 * @module core/process
 * @version V175.0.0
 */

'use strict';

const { ZombieKiller, preFlightCleanup, forceKillBrowser, getZombieStats } = require('./ZombieKiller');

module.exports = {
    ZombieKiller,
    preFlightCleanup,
    forceKillBrowser,
    getZombieStats
};
