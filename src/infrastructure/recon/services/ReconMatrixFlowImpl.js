'use strict';

const { reconImmediateStore } = require('./ReconImmediateStore');
const { reconMatrixRuntime } = require('./ReconMatrixRuntime');
const { reconMatrixRuntimeSupport } = require('./ReconMatrixRuntimeSupport');
const { reconMatrixTargetRunner } = require('./ReconMatrixTargetRunner');
const { reconLocalDictionaryService } = require('./ReconLocalDictionaryService');
const { reconResultStitcher } = require('./ReconResultStitcher');
const { reconRouteDegradePolicy } = require('./ReconRouteDegradePolicy');
const { reconSourceProber } = require('./ReconSourceProber');

const reconMatrixFlow = Object.assign(
  {},
  reconMatrixRuntimeSupport,
  reconMatrixRuntime,
  reconMatrixTargetRunner,
  reconRouteDegradePolicy,
  reconSourceProber,
  reconLocalDictionaryService,
  reconResultStitcher,
  reconImmediateStore
);

module.exports = { reconMatrixFlow };
