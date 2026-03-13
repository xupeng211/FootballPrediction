/**
 * Jest Test Setup
 * 测试环境初始化
 */

// 加载测试环境变量
process.env.NODE_ENV = 'test';
process.env.DB_HOST = 'localhost';
process.env.DB_PORT = '5432';
process.env.DB_NAME = 'football_test';
process.env.DB_USER = 'test_user';
process.env.DB_PASSWORD = 'test_pass';
process.env.DATA_MATCHES_PATH = 'data/matches';
process.env.MAX_WORKERS = '2';

// 全局测试工具
global.testUtils = {
  /**
   * 创建模拟的 match 数据
   * @param overrides
   */
  createMockMatch: (overrides = {}) => ({
    match_id: 'test_12345',
    home_team: 'Team A',
    away_team: 'Team B',
    match_date: '2026-03-12',
    league: 'Premier League',
    ...overrides
  }),

  /**
   * 创建模拟的 raw_data 数据
   * @param overrides
   */
  createMockRawData: (overrides = {}) => ({
    match_id: 'test_12345',
    home_team: { name: 'Team A', id: 1 },
    away_team: { name: 'Team B', id: 2 },
    match_info: { date: '2026-03-12', status: 'FINISHED' },
    statistics: { possession: [50, 50] },
    ...overrides
  }),

  /**
   * 创建损坏的 mock 数据
   */
  createCorruptData: () => ({
    match_id: null,
    raw_data: {},
    saved_at: null
  }),

  /**
   * 延迟函数
   * @param ms
   */
  delay: (ms) => new Promise(resolve => { setTimeout(resolve, ms); })
};

// 测试前清理
beforeAll(() => {
  console.log('\n🧪 TITAN Test Suite Starting...\n');
});

// 测试后清理
afterAll(() => {
  console.log('\n✅ TITAN Test Suite Completed\n');
});
