import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import type { ApiResponse, Prediction, Match, PredictionResponse, MatchDetails, MatchStats, UserProfile, HistoryResponse, UserUpdateData } from '@/types/prediction'
import type { AuthResponse } from '@/types/auth'

class ApiClient {
  private client: AxiosInstance
  private refreshTokenPromise: Promise<boolean> | null = null

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // Add auth token if available
        const token = localStorage.getItem('auth_token')
        if (token) {
          config.headers = config.headers || {}
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        return response
      },
      async (error) => {
        const originalRequest = error.config

        // Handle 401 Unauthorized errors
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true

          // Try to refresh token
          if (this.refreshTokenPromise === null) {
            this.refreshTokenPromise = this.attemptTokenRefresh()
          }

          const refreshSuccess = await this.refreshTokenPromise
          this.refreshTokenPromise = null

          if (refreshSuccess) {
            // Retry original request with new token
            const token = localStorage.getItem('auth_token')
            if (token) {
              originalRequest.headers = originalRequest.headers || {}
              originalRequest.headers.Authorization = `Bearer ${token}`
            }
            return this.client(originalRequest)
          } else {
            // Refresh failed, clear auth and redirect to login
            this.handleAuthError()
          }
        }

        return Promise.reject(error)
      }
    )
  }

  private async attemptTokenRefresh(): Promise<boolean> {
    try {
      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        return false
      }

      const response = await axios.post<AuthResponse>(
        `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'}/auth/refresh`,
        { refreshToken }
      )

      // Update stored tokens
      localStorage.setItem('auth_token', response.data.token)
      if (response.data.refreshToken) {
        localStorage.setItem('refresh_token', response.data.refreshToken)
      }

      return true
    } catch (error) {
      console.error('Token refresh failed:', error)
      return false
    }
  }

  private handleAuthError() {
    // Clear all auth data
    localStorage.removeItem('auth_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_data')

    // Redirect to login page (only if we're in browser)
    if (typeof window !== 'undefined') {
      // Use window.location to force a hard redirect
      window.location.href = '/login'
    }
  }

  // Auth endpoints
  async login(email: string, password: string): Promise<AuthResponse> {
    try {
      const response = await this.client.post<AuthResponse>('/auth/login', {
        email,
        password
      })
      return response.data
    } catch (error) {
      // Fallback to mock login for development
      if (error.response?.status >= 500) {
        return this.mockLogin(email, password)
      }
      throw error
    }
  }

  async register(username: string, email: string, password: string): Promise<AuthResponse> {
    try {
      const response = await this.client.post<AuthResponse>('/auth/register', {
        username,
        email,
        password
      })
      return response.data
    } catch (error) {
      // Fallback to mock register for development
      if (error.response?.status >= 500) {
        return this.mockRegister(username, email, password)
      }
      throw error
    }
  }

  async logout(): Promise<void> {
    try {
      await this.client.post('/auth/logout')
    } catch (error) {
      // Continue even if logout API fails
      console.warn('Logout API call failed:', error)
    }
  }

  async refreshAuth(refreshToken: string): Promise<AuthResponse> {
    try {
      const response = await this.client.post<AuthResponse>('/auth/refresh', {
        refreshToken
      })
      return response.data
    } catch (error) {
      // Fallback to mock refresh for development
      if (error.response?.status >= 500) {
        return this.mockRefresh()
      }
      throw error
    }
  }

  async updateProfile(updates: any): Promise<any> {
    try {
      const response = await this.client.put('/auth/profile', updates)
      return response.data
    } catch (error) {
      throw error
    }
  }

  // User profile methods
  async getUserProfile(): Promise<UserProfile> {
    try {
      const response = await this.client.get<UserProfile>('/user/profile')
      return response.data
    } catch (error) {
      console.error('Failed to fetch user profile:', error)
      // Return mock data for development
      return this.getMockUserProfile()
    }
  }

  async getUserHistory(page: number = 1, limit: number = 20): Promise<HistoryResponse> {
    try {
      const response = await this.client.get<HistoryResponse>(`/user/history?page=${page}&limit=${limit}`)
      return response.data
    } catch (error) {
      console.error('Failed to fetch user history:', error)
      // Return mock data for development
      return this.getMockUserHistory(page, limit)
    }
  }

  async updateUserProfile(data: UserUpdateData): Promise<UserProfile> {
    try {
      const response = await this.client.put<UserProfile>('/user/profile', data)
      return response.data
    } catch (error) {
      console.error('Failed to update user profile:', error)
      throw error
    }
  }

  // Mock auth methods for development
  private mockLogin(email: string, password: string): AuthResponse {
    // Mock validation
    if (email === 'admin@football.com' && password === 'admin123') {
      return {
        user: {
          id: 1,
          username: 'admin',
          email: 'admin@football.com',
          role: 'admin',
          created_at: new Date().toISOString()
        },
        token: 'mock-jwt-token-admin-' + Date.now(),
        refreshToken: 'mock-refresh-token-admin-' + Date.now(),
        expiresIn: 3600
      }
    }

    if (email === 'user@football.com' && password === 'user123') {
      return {
        user: {
          id: 2,
          username: 'user',
          email: 'user@football.com',
          role: 'user',
          created_at: new Date().toISOString()
        },
        token: 'mock-jwt-token-user-' + Date.now(),
        refreshToken: 'mock-refresh-token-user-' + Date.now(),
        expiresIn: 3600
      }
    }

    throw new Error('Invalid credentials')
  }

  private mockRegister(username: string, email: string, password: string): AuthResponse {
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
    }
  }

  private mockRefresh(): AuthResponse {
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
    }
  }

  // Health check
  async healthCheck(): Promise<{ status: string; message: string }> {
    try {
      const response = await this.client.get('/health')
      return response.data
    } catch (error) {
      throw new Error('Health check failed')
    }
  }

  // Get predictions for a specific match
  async getPredictions(matchId?: number): Promise<PredictionResponse> {
    try {
      const url = matchId ? `/predictions?match_id=${matchId}` : '/predictions'
      const response = await this.client.get<PredictionResponse>(url)
      return response.data
    } catch (error) {
      console.error('Failed to fetch predictions:', error)
      // Return mock data for development
      return this.getMockPredictions(matchId)
    }
  }

  // Get recent matches
  async getRecentMatches(limit: number = 20): Promise<Match[]> {
    try {
      const response = await this.client.get<Match[]>(`/matches?limit=${limit}`)
      return response.data
    } catch (error) {
      console.error('Failed to fetch recent matches:', error)
      // Return mock data for development
      return this.getMockMatches()
    }
  }

  // Get match details
  async getMatch(matchId: number): Promise<Match> {
    try {
      const response = await this.client.get<Match>(`/matches/${matchId}`)
      return response.data
    } catch (error) {
      console.error(`Failed to fetch match ${matchId}:`, error)
      throw new Error('Match not found')
    }
  }

  // Get detailed match information (metadata)
  async getMatchDetails(matchId: number): Promise<MatchDetails> {
    try {
      const response = await this.client.get<MatchDetails>(`/matches/${matchId}/details`)
      return response.data
    } catch (error) {
      console.error(`Failed to fetch match details for ${matchId}:`, error)
      // Return mock data for development
      return this.getMockMatchDetails(matchId)
    }
  }

  // Get match statistics
  async getMatchStats(matchId: number): Promise<MatchStats> {
    try {
      const response = await this.client.get<MatchStats>(`/matches/${matchId}/stats`)
      return response.data
    } catch (error) {
      console.error(`Failed to fetch match stats for ${matchId}:`, error)
      // Return mock data for development
      return this.getMockMatchStats()
    }
  }

  // Mock predictions for development
  private getMockPredictions(matchId?: number): PredictionResponse {
    const mockPredictions: Prediction[] = [
      {
        match_id: matchId || 12345,
        prediction: 'home_win',
        predicted_outcome: 'home_win',
        home_win_prob: 0.65,
        draw_prob: 0.25,
        away_win_prob: 0.10,
        confidence: 0.82,
        success: true,
        mode: 'mock',
        mock_reason: 'Development mode - mock data',
        features_used: ['home_xg', 'away_xg', 'home_possession', 'away_possession'],
        created_at: new Date().toISOString(),
      },
      {
        match_id: matchId || 12346,
        prediction: 'draw',
        predicted_outcome: 'draw',
        home_win_prob: 0.35,
        draw_prob: 0.40,
        away_win_prob: 0.25,
        confidence: 0.71,
        success: true,
        mode: 'mock',
        mock_reason: 'Development mode - mock data',
        features_used: ['home_xg', 'away_xg', 'shots_difference'],
        created_at: new Date().toISOString(),
      },
    ]

    return {
      predictions: mockPredictions,
      total: mockPredictions.length,
      page: 1,
      limit: 20,
    }
  }

  // Mock matches for development
  private getMockMatches(): Match[] {
    return [
      {
        id: 12345,
        home_team: 'Manchester United',
        away_team: 'Liverpool',
        scheduled_at: '2024-01-15T20:00:00Z',
        league: 'Premier League',
        status: 'scheduled',
        odds: {
          home_win: 2.10,
          draw: 3.40,
          away_win: 3.80,
        },
      },
      {
        id: 12346,
        home_team: 'Barcelona',
        away_team: 'Real Madrid',
        scheduled_at: '2024-01-16T19:45:00Z',
        league: 'La Liga',
        status: 'scheduled',
        odds: {
          home_win: 2.50,
          draw: 3.20,
          away_win: 2.80,
        },
      },
      {
        id: 12347,
        home_team: 'Bayern Munich',
        away_team: 'Borussia Dortmund',
        scheduled_at: '2024-01-17T18:30:00Z',
        league: 'Bundesliga',
        status: 'live',
        score: {
          home: 1,
          away: 0,
        },
        odds: {
          home_win: 1.45,
          draw: 4.80,
          away_win: 6.50,
        },
      },
    ]
  }

  // Mock match details for development
  private getMockMatchDetails(matchId: number): MatchDetails {
    const matches = this.getMockMatches()
    const match = matches.find(m => m.id === matchId) || matches[0]

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
    }
  }

  // Mock match statistics for development
  private getMockMatchStats(): MatchStats {
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
    }
  }

  // Mock user profile for development
  private getMockUserProfile(): UserProfile {
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
    }
  }

  // Mock user history for development
  private getMockUserHistory(page: number = 1, limit: number = 20): HistoryResponse {
    const mockRecords = this.generateMockHistoryRecords()
    const startIndex = (page - 1) * limit
    const endIndex = startIndex + limit
    const paginatedRecords = mockRecords.slice(startIndex, endIndex)

    const winCount = mockRecords.filter(r => r.result === 'win').length
    const lossCount = mockRecords.filter(r => r.result === 'loss').length
    const pushCount = mockRecords.filter(r => r.result === 'push').length
    const totalProfit = mockRecords.reduce((sum, r) => sum + r.profit, 0)
    const totalStake = mockRecords.reduce((sum, r) => sum + r.stake, 0)

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
    }
  }

  // Generate mock history records
  private generateMockHistoryRecords(): any[] {
    const teams = [
      'Manchester United', 'Liverpool', 'Barcelona', 'Real Madrid', 'Bayern Munich',
      'Borussia Dortmund', 'PSG', 'Manchester City', 'Chelsea', 'Arsenal',
      'Juventus', 'AC Milan', 'Inter', 'Atletico Madrid', 'Tottenham'
    ]

    const leagues = ['Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1']
    const outcomes: Array<'home_win' | 'draw' | 'away_win'> = ['home_win', 'draw', 'away_win']
    const results: Array<'win' | 'loss' | 'push'> = ['win', 'loss', 'push']

    return Array.from({ length: 100 }, (_, index) => {
      const homeTeam = teams[Math.floor(Math.random() * teams.length)]
      let awayTeam = teams[Math.floor(Math.random() * teams.length)]
      while (awayTeam === homeTeam) {
        awayTeam = teams[Math.floor(Math.random() * teams.length)]
      }

      const prediction = outcomes[Math.floor(Math.random() * outcomes.length)]
      const result = results[Math.floor(Math.random() * results.length)]
      const odds = 1.8 + Math.random() * 2.5 // 1.8 to 4.3
      const stake = 50 + Math.floor(Math.random() * 200) // 50 to 250

      let profit = 0
      if (result === 'win') {
        profit = stake * odds - stake
      } else if (result === 'loss') {
        profit = -stake
      } // push = 0 profit

      const matchDate = new Date()
      matchDate.setDate(matchDate.getDate() - Math.floor(Math.random() * 30))

      const finalScore = result !== 'push' ? {
        home: Math.floor(Math.random() * 5),
        away: Math.floor(Math.random() * 5)
      } : { home: 0, away: 0 }

      return {
        id: 1000 + index,
        match_id: 12000 + index,
        home_team: homeTeam,
        away_team: awayTeam,
        league: leagues[Math.floor(Math.random() * leagues.length)],
        scheduled_at: matchDate.toISOString(),
        prediction,
        predicted_outcome: prediction,
        actual_outcome: result === 'win' ? prediction : outcomes[Math.floor(Math.random() * outcomes.length)],
        stake,
        odds: parseFloat(odds.toFixed(2)),
        result,
        profit: parseFloat(profit.toFixed(2)),
        confidence: 0.6 + Math.random() * 0.4, // 0.6 to 1.0
        created_at: matchDate.toISOString(),
        match_status: 'completed',
        final_score
      }
    }).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  }
}

// Create singleton instance
const apiClient = new ApiClient()

export default apiClient