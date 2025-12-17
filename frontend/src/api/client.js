import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { mockConfig, defaultMockUsers, generateMockToken, generateMockRefreshToken, mockPredictionData, generateMockHistory, generateMockMatches } from '../config/mockData';
class ApiClient {
    client;
    refreshTokenPromise = null;
    constructor() {
        this.client = axios.create({
            baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
            timeout: 10000,
            headers: {
                'Content-Type': 'application/json',
            },
        });
        this.setupInterceptors();
    }
    setupInterceptors() {
        // Request interceptor
        this.client.interceptors.request.use((config) => {
            // Add auth token if available
            const token = localStorage.getItem('auth_token');
            if (token) {
                config.headers = config.headers || {};
                config.headers.Authorization = `Bearer ${token}`;
            }
            return config;
        }, (error) => {
            return Promise.reject(error);
        });
        // Response interceptor
        this.client.interceptors.response.use((response) => {
            return response;
        }, async (error) => {
            const originalRequest = error.config;
            // Handle 401 Unauthorized errors
            if (error.response?.status === 401 && !originalRequest._retry) {
                originalRequest._retry = true;
                // Try to refresh token
                if (this.refreshTokenPromise === null) {
                    this.refreshTokenPromise = this.attemptTokenRefresh();
                }
                const refreshSuccess = await this.refreshTokenPromise;
                this.refreshTokenPromise = null;
                if (refreshSuccess) {
                    // Retry original request with new token
                    const token = localStorage.getItem('auth_token');
                    if (token) {
                        originalRequest.headers = originalRequest.headers || {};
                        originalRequest.headers.Authorization = `Bearer ${token}`;
                    }
                    return this.client(originalRequest);
                }
                else {
                    // Refresh failed, clear auth and redirect to login
                    this.handleAuthError();
                }
            }
            return Promise.reject(error);
        });
    }
    async attemptTokenRefresh() {
        try {
            const refreshToken = localStorage.getItem('refresh_token');
            if (!refreshToken) {
                return false;
            }
            const response = await axios.post(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'}/auth/refresh`, { refreshToken });
            // Update stored tokens
            localStorage.setItem('auth_token', response.data.token);
            if (response.data.refreshToken) {
                localStorage.setItem('refresh_token', response.data.refreshToken);
            }
            return true;
        }
        catch (error) {
            console.error('Token refresh failed:', error);
            return false;
        }
    }
    handleAuthError() {
        // Clear all auth data
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_data');
        // Redirect to login page (only if we're in browser)
        if (typeof window !== 'undefined') {
            // Use window.location to force a hard redirect
            window.location.href = '/login';
        }
    }
    // Auth endpoints
    async login(email, password) {
        try {
            const response = await this.client.post('/auth/login', {
                email,
                password
            });
            return response.data;
        }
        catch (error) {
            // Fallback to mock login for development
            if (error.response?.status >= 500) {
                return this.mockLogin(email, password);
            }
            throw error;
        }
    }
    async register(username, email, password) {
        try {
            const response = await this.client.post('/auth/register', {
                username,
                email,
                password
            });
            return response.data;
        }
        catch (error) {
            // Fallback to mock register for development
            if (error.response?.status >= 500) {
                return this.mockRegister(username, email, password);
            }
            throw error;
        }
    }
    async logout() {
        try {
            await this.client.post('/auth/logout');
        }
        catch (error) {
            // Continue even if logout API fails
            console.warn('Logout API call failed:', error);
        }
    }
    async refreshAuth(refreshToken) {
        try {
            const response = await this.client.post('/auth/refresh', {
                refreshToken
            });
            return response.data;
        }
        catch (error) {
            // Fallback to mock refresh for development
            if (error.response?.status >= 500) {
                return this.mockRefresh();
            }
            throw error;
        }
    }
    async updateProfile(updates) {
        try {
            const response = await this.client.put('/auth/profile', updates);
            return response.data;
        }
        catch (error) {
            throw error;
        }
    }
    // User profile methods
    async getUserProfile() {
        try {
            const response = await this.client.get('/user/profile');
            return response.data;
        }
        catch (error) {
            console.error('Failed to fetch user profile:', error);
            // Return mock data for development
            return this.getMockUserProfile();
        }
    }
    async getUserHistory(page = 1, limit = 20) {
        try {
            const response = await this.client.get(`/user/history?page=${page}&limit=${limit}`);
            return response.data;
        }
        catch (error) {
            console.error('Failed to fetch user history:', error);
            // Return mock data for development
            return this.getMockUserHistory(page, limit);
        }
    }
    async updateUserProfile(data) {
        try {
            const response = await this.client.put('/user/profile', data);
            return response.data;
        }
        catch (error) {
            console.error('Failed to update user profile:', error);
            throw error;
        }
    }
    // Mock auth methods for development
    mockLogin(email, password) {
        // 使用配置化的Mock认证
        const mockUsers = Object.keys(mockConfig.mockUsers).length > 0
            ? mockConfig.mockUsers
            : defaultMockUsers;

        // 查找匹配的用户
        const userEntry = Object.entries(mockUsers).find(([key, user]) =>
            user.email === email && user.password === password
        );

        if (userEntry) {
            const [userType, userData] = userEntry;
            return {
                user: {
                    ...userData,
                    id: userData.id || (userType === 'admin' ? 1 : 2),
                    created_at: userData.created_at || new Date().toISOString()
                },
                token: generateMockToken(userType),
                refreshToken: generateMockRefreshToken(userType),
                expiresIn: 3600
            };
        }

        throw new Error('Invalid credentials');
    }
    mockRegister(username, email, password) {
        // Mock registration
        return {
            user: {
                id: 3,
                username: username,
                email: email,
                role: 'user',
                created_at: new Date().toISOString()
            },
            token: 'mock-jwt-token-new-' + Date.now(),
            refreshToken: 'mock-refresh-token-new-' + Date.now(),
            expiresIn: 3600
        };
    }
    mockRefresh() {
        return {
            user: {
                id: 1,
                username: 'admin',
                email: 'admin@football.com',
                role: 'admin',
                created_at: new Date().toISOString()
            },
            token: 'mock-jwt-token-refreshed-' + Date.now(),
            refreshToken: 'mock-refresh-token-refreshed-' + Date.now(),
            expiresIn: 3600
        };
    }
    // Health check
    async healthCheck() {
        try {
            const response = await this.client.get('/health');
            return response.data;
        }
        catch (error) {
            throw new Error('Health check failed');
        }
    }
    // Get predictions for a specific match
    async getPredictions(matchId) {
        try {
            const url = matchId ? `/predictions?match_id=${matchId}` : '/predictions';
            const response = await this.client.get(url);
            return response.data;
        }
        catch (error) {
            console.error('Failed to fetch predictions:', error);
            // Return mock data for development
            return this.getMockPredictions(matchId);
        }
    }
    // Get recent matches
    async getRecentMatches(limit = 20) {
        try {
            const response = await this.client.get(`/matches?limit=${limit}`);
            return response.data;
        }
        catch (error) {
            console.error('Failed to fetch recent matches:', error);
            // Return mock data for development
            return this.getMockMatches();
        }
    }
    // Get match details
    async getMatch(matchId) {
        try {
            const response = await this.client.get(`/matches/${matchId}`);
            return response.data;
        }
        catch (error) {
            console.error(`Failed to fetch match ${matchId}:`, error);
            throw new Error('Match not found');
        }
    }
    // Get detailed match information (metadata)
    async getMatchDetails(matchId) {
        try {
            const response = await this.client.get(`/matches/${matchId}/details`);
            return response.data;
        }
        catch (error) {
            console.error(`Failed to fetch match details for ${matchId}:`, error);
            // Return mock data for development
            return this.getMockMatchDetails(matchId);
        }
    }
    // Get match statistics
    async getMatchStats(matchId) {
        try {
            const response = await this.client.get(`/matches/${matchId}/stats`);
            return response.data;
        }
        catch (error) {
            console.error(`Failed to fetch match stats for ${matchId}:`, error);
            // Return mock data for development
            return this.getMockMatchStats();
        }
    }
    // Mock predictions for development
    getMockPredictions(matchId) {
        // 使用配置化的Mock预测数据
        const probabilities = mockPredictionData.defaultProbabilities;
        const predictions = [];

        // 生成第一个预测结果（主场优势）
        predictions.push({
            match_id: matchId || 12345,
            prediction: probabilities[2] > probabilities[0] && probabilities[2] > probabilities[1] ? 'home_win' :
                      probabilities[1] > probabilities[0] && probabilities[1] > probabilities[2] ? 'draw' : 'away_win',
            predicted_outcome: probabilities[2] > probabilities[0] && probabilities[2] > probabilities[1] ? 'HOME_WIN' :
                            probabilities[1] > probabilities[0] && probabilities[1] > probabilities[2] ? 'DRAW' : 'AWAY_WIN',
            home_win_prob: probabilities[2],
            draw_prob: probabilities[1],
            away_win_prob: probabilities[0],
            confidence: Math.max(...probabilities),
            success: true,
            mode: 'mock',
            mock_reason: 'Development mode - configuration-based mock data',
            features_used: Array.from({length: mockPredictionData.featureCount}, (_, i) => `feature_${i + 1}`),
            created_at: new Date().toISOString(),
        });

        // 生成第二个预测结果（更平衡）
        const balancedProbabilities = [0.35, 0.40, 0.25];
        predictions.push({
            match_id: matchId || 12346,
            prediction: balancedProbabilities[1] > balancedProbabilities[0] && balancedProbabilities[1] > balancedProbabilities[2] ? 'draw' :
                      balancedProbabilities[0] > balancedProbabilities[2] ? 'home_win' : 'away_win',
            predicted_outcome: balancedProbabilities[1] > balancedProbabilities[0] && balancedProbabilities[1] > balancedProbabilities[2] ? 'DRAW' :
                            balancedProbabilities[0] > balancedProbabilities[2] ? 'HOME_WIN' : 'AWAY_WIN',
            home_win_prob: balancedProbabilities[2],
            draw_prob: balancedProbabilities[1],
            away_win_prob: balancedProbabilities[0],
            confidence: Math.max(...balancedProbabilities),
            success: true,
            mode: 'mock',
            mock_reason: 'Development mode - configuration-based mock data',
            features_used: Array.from({length: mockPredictionData.featureCount}, (_, i) => `feature_${i + 1}`),
            created_at: new Date().toISOString(),
        });
        return {
            predictions: mockPredictions,
            total: mockPredictions.length,
            page: 1,
            limit: 20,
        };
    }
    // Mock matches for development
    getMockMatches() {
        // 使用配置化的Mock比赛数据
        return generateMockMatches();
    }
    // Mock match details for development
    getMockMatchDetails(matchId) {
        const matches = this.getMockMatches();
        const match = matches.find(m => m.id === matchId) || matches[0];
        return {
            ...match,
            venue: 'Old Trafford',
            weather: 'Clear, 15°C',
            attendance: 75000,
            referee: 'Michael Oliver',
            home_team_form: ['W', 'W', 'L', 'W', 'D'], // Recent 5 matches
            away_team_form: ['W', 'D', 'W', 'L', 'W'],
            head_to_head: {
                home_wins: 3,
                draws: 2,
                away_wins: 2,
                last_matches: [
                    {
                        date: '2023-03-05',
                        home_team: 'Manchester United',
                        away_team: 'Liverpool',
                        home_score: 2,
                        away_score: 1
                    },
                    {
                        date: '2022-08-22',
                        home_team: 'Liverpool',
                        away_team: 'Manchester United',
                        home_score: 3,
                        away_score: 1
                    },
                    {
                        date: '2022-01-15',
                        home_team: 'Manchester United',
                        away_team: 'Liverpool',
                        home_score: 0,
                        away_score: 0
                    }
                ]
            }
        };
    }
    // Mock match statistics for development
    getMockMatchStats() {
        return {
            home_xg: 1.5,
            away_xg: 0.8,
            home_possession: 55,
            away_possession: 45,
            home_shots: 12,
            away_shots: 8,
            home_shots_on_target: 5,
            away_shots_on_target: 3,
            home_corners: 6,
            away_corners: 4,
            home_fouls: 8,
            away_fouls: 12,
            home_yellow_cards: 1,
            away_yellow_cards: 3,
            home_red_cards: 0,
            away_red_cards: 0
        };
    }
    // Mock user profile for development
    getMockUserProfile() {
        return {
            id: 1,
            username: 'admin',
            email: 'admin@football.com',
            role: 'admin',
            bankroll: 10000.00,
            total_winnings: 2450.75,
            total_bets: 156,
            win_rate: 67.3,
            roi: 12.5,
            created_at: '2024-01-01T00:00:00Z',
            last_login: new Date().toISOString(),
            avatar: null,
            phone: '+86-138-0000-0000',
            timezone: 'Asia/Shanghai',
            currency: 'CNY'
        };
    }
    // Mock user history for development
    getMockUserHistory(page = 1, limit = 20) {
        // 使用配置化的Mock历史数据生成
        const mockRecords = generateMockHistory();
        const startIndex = (page - 1) * limit;
        const endIndex = startIndex + limit;
        const paginatedRecords = mockRecords.slice(startIndex, endIndex);
        const winCount = mockRecords.filter(r => r.result === 'win').length;
        const lossCount = mockRecords.filter(r => r.result === 'loss').length;
        const pushCount = mockRecords.filter(r => r.result === 'push').length;
        const totalProfit = mockRecords.reduce((sum, r) => sum + r.profit, 0);
        const totalStake = mockRecords.reduce((sum, r) => sum + r.stake, 0);
        return {
            records: paginatedRecords,
            total: mockRecords.length,
            page,
            limit,
            stats: {
                total_bets: mockRecords.length,
                total_winnings: totalProfit,
                total_loss: Math.abs(Math.min(0, totalProfit)),
                win_count: winCount,
                loss_count: lossCount,
                push_count: pushCount,
                win_rate: (winCount / mockRecords.length) * 100,
                roi: (totalProfit / totalStake) * 100
            }
        };
    }
    // 注意: generateMockHistoryRecords 方法已移至 config/mockData.js
}
// Create singleton instance
const apiClient = new ApiClient();
export default apiClient;
