/**
 * Mock数据配置
 * 将硬编码的Mock数据移至配置文件中，便于管理和修改
 */

// 从环境变量获取配置或使用默认值
const getEnvConfig = () => {
  try {
    return {
      mockUsers: JSON.parse(import.meta.env.VITE_MOCK_USERS || '{}'),
      adminEmail: import.meta.env.VITE_MOCK_USER_EMAIL || 'admin@football.com',
      adminPassword: import.meta.env.VITE_MOCK_USER_PASSWORD || 'admin123',
      enableMockFallback: import.meta.env.VITE_ENABLE_MOCK_FALLBACK === 'true'
    };
  } catch (e) {
    console.warn('环境变量解析失败，使用默认配置:', e);
    return {
      mockUsers: {},
      adminEmail: 'admin@football.com',
      adminPassword: 'admin123',
      enableMockFallback: true
    };
  }
};

export const mockConfig = getEnvConfig();

// 默认Mock用户数据（当环境变量为空时使用）
export const defaultMockUsers = {
  admin: {
    id: 1,
    username: 'admin',
    email: 'admin@football.com',
    role: 'admin',
    created_at: new Date().toISOString()
  },
  user: {
    id: 2,
    username: 'user',
    email: 'user@football.com',
    role: 'user',
    created_at: new Date().toISOString()
  }
};

// 生成Mock Token
export const generateMockToken = (userType = 'admin') => {
  const timestamp = Date.now();
  return `mock-jwt-token-${userType}-${timestamp}`;
};

// 生成Mock Refresh Token
export const generateMockRefreshToken = (userType = 'admin') => {
  const timestamp = Date.now();
  return `mock-refresh-token-${userType}-${timestamp}`;
};

// Mock预测数据配置
export const mockPredictionData = {
  // 默认概率分布
  defaultProbabilities: [0.15, 0.25, 0.6], // [AWAY_WIN, DRAW, HOME_WIN]

  // 常用球队
  teams: [
    'Manchester United', 'Manchester City', 'Arsenal', 'Chelsea', 'Liverpool',
    'Barcelona', 'Real Madrid', 'Atletico Madrid', 'Sevilla', 'Valencia',
    'Bayern Munich', 'Borussia Dortmund', 'RB Leipzig', 'Bayer Leverkusen',
    'Juventus', 'AC Milan', 'Inter', 'Napoli', 'AS Roma', 'Lazio',
    'PSG', 'Lyon', 'Marseille', 'Monaco'
  ],

  // 联赛
  leagues: ['Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1'],

  // 模型版本
  modelVersion: 'simulation-1.0',

  // 特征数量
  featureCount: 12
};

// Mock历史数据
export const generateMockHistory = (count = 100) => {
  const history = [];
  const outcomes = ['home_win', 'draw', 'away_win'];
  const results = ['win', 'loss', 'push'];

  for (let i = 0; i < count; i++) {
    const homeTeam = mockPredictionData.teams[Math.floor(Math.random() * mockPredictionData.teams.length)];
    let awayTeam = mockPredictionData.teams[Math.floor(Math.random() * mockPredictionData.teams.length)];

    // 确保主客队不同
    while (awayTeam === homeTeam) {
      awayTeam = mockPredictionData.teams[Math.floor(Math.random() * mockPredictionData.teams.length)];
    }

    const prediction = outcomes[Math.floor(Math.random() * outcomes.length)];
    const result = results[Math.floor(Math.random() * results.length)];

    history.push({
      id: 1000 + i,
      match_id: 12000 + i,
      home_team: homeTeam,
      away_team: awayTeam,
      league: mockPredictionData.leagues[Math.floor(Math.random() * mockPredictionData.leagues.length)],
      scheduled_at: new Date(Date.now() - Math.floor(Math.random() * 30) * 24 * 60 * 60 * 1000).toISOString(),
      prediction,
      predicted_outcome: prediction,
      stake: 50 + Math.floor(Math.random() * 200),
      odds: 1.8 + Math.random() * 2.5,
      result,
      profit: result === 'win' ? (1.8 + Math.random() * 2.5 - 1) * (50 + Math.floor(Math.random() * 200)) : -(50 + Math.floor(Math.random() * 200)),
      confidence: 0.6 + Math.random() * 0.4,
      created_at: new Date(Date.now() - Math.floor(Math.random() * 30) * 24 * 60 * 60 * 1000).toISOString(),
      match_status: 'completed'
    });
  }

  return history.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
};

// Mock比赛数据
export const generateMockMatches = (count = 20) => {
  const matches = [];

  for (let i = 0; i < count; i++) {
    const homeTeam = mockPredictionData.teams[Math.floor(Math.random() * mockPredictionData.teams.length)];
    let awayTeam = mockPredictionData.teams[Math.floor(Math.random() * mockPredictionData.teams.length)];

    while (awayTeam === homeTeam) {
      awayTeam = mockPredictionData.teams[Math.floor(Math.random() * mockPredictionData.teams.length)];
    }

    const status = Math.random() > 0.7 ? 'scheduled' : 'live';

    matches.push({
      id: 12345 + i,
      home_team: homeTeam,
      away_team: awayTeam,
      scheduled_at: new Date(Date.now() + Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
      league: mockPredictionData.leagues[Math.floor(Math.random() * mockPredictionData.leagues.length)],
      status: status,
      odds: {
        home_win: 2.0 + Math.random() * 1.5,
        draw: 3.0 + Math.random() * 1.0,
        away_win: 2.5 + Math.random() * 2.0,
      },
      ...(status === 'live' && {
        score: {
          home: Math.floor(Math.random() * 3),
          away: Math.floor(Math.random() * 3)
        }
      })
    });
  }

  return matches;
};