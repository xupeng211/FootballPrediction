'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const { EntityMapper } = require('../../src/infrastructure/etl/EntityMapper');

test('normalizeBookmakerName 应识别亚洲博彩公司预留别名', () => {
  const mapper = new EntityMapper();

  assert.equal(mapper.normalizeBookmakerName('澳门彩票'), 'MACAU_SLOT');
  assert.equal(mapper.normalizeBookmakerName('MacauSlot'), 'MACAU_SLOT');
  assert.equal(mapper.normalizeBookmakerName('澳彩'), 'MACAU_SLOT');

  assert.equal(mapper.normalizeBookmakerName('皇冠'), 'CROWN');
  assert.equal(mapper.normalizeBookmakerName('IBC'), 'CROWN');
  assert.equal(mapper.normalizeBookmakerName('IBCBET'), 'CROWN');

  assert.equal(mapper.normalizeBookmakerName('188Bet'), '188BET');
  assert.equal(mapper.normalizeBookmakerName('利记'), '188BET');
  assert.equal(mapper.normalizeBookmakerName('188'), '188BET');
});

test('normalizeBookmakerName 对未预置庄家应保持原值', () => {
  const mapper = new EntityMapper();

  assert.equal(mapper.normalizeBookmakerName('Bet365'), 'Bet365');
  assert.equal(mapper.normalizeBookmakerName('Betfair Exchange'), 'Betfair Exchange');
});

test('normalizeLeagueName 应识别 LaLiga 别名', () => {
  const mapper = new EntityMapper();

  assert.equal(mapper.normalizeLeagueName('LaLiga'), 'La Liga');
});
