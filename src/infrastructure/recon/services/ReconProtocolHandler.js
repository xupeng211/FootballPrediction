'use strict';

const { reconProtocolArchiveFlow } = require('./ReconProtocolArchiveFlow');
const { reconProtocolSeasonSweep } = require('./ReconProtocolSeasonSweep');
const { reconProtocolFetchFlow } = require('./ReconProtocolFetchFlow');

class ReconProtocolHandler {
  constructor(navigator) {
    this.navigator = navigator;
  }

  _callNavigatorOverride(methodName, fallback, ...args) {
    const instanceMethod = this.navigator?.[methodName];
    const prototypeMethod = Object.getPrototypeOf(this.navigator || null)?.[methodName];
    if (typeof instanceMethod === 'function' && instanceMethod !== prototypeMethod) {
      return instanceMethod.apply(this.navigator, args);
    }
    return fallback(...args);
  }

  get logger() {
    return this.navigator.logger;
  }

  get page() {
    return this.navigator.page;
  }
}

Object.assign(
  ReconProtocolHandler.prototype,
  reconProtocolArchiveFlow,
  reconProtocolSeasonSweep,
  reconProtocolFetchFlow
);

module.exports = {
  ReconProtocolHandler
};
