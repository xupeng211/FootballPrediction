'use strict';

const { reconFetchCoordinator } = require('./ReconFetchCoordinator');
const { reconProtocolAdapter } = require('./ReconProtocolAdapter');

const reconProtocolFetchFlow = {
  ...reconProtocolAdapter,
  ...reconFetchCoordinator
};

module.exports = { reconProtocolFetchFlow };
