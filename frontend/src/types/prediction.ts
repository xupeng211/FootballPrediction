export interface Prediction {
  match_id: number
  prediction: string
  predicted_outcome: string
  home_win_prob: number
  draw_prob: number
  away_win_prob: number
  confidence: number
  success: boolean
  mode?: string
  mock_reason?: string | null
  features_used?: string[]
  created_at?: string
}

export interface Match {
  id: number
  home_team: string
  away_team: string
  scheduled_at: string
  league: string
  status: string
  score?: {
    home: number
    away: number
  }
  odds?: {
    home_win: number
    draw: number
    away_win: number
  }
}

export interface PredictionResponse {
  predictions: Prediction[]
  total: number
  page: number
  limit: number
}

export interface MatchStats {
  home_xg: number
  away_xg: number
  home_possession: number
  away_possession: number
  home_shots: number
  away_shots: number
  home_shots_on_target: number
  away_shots_on_target: number
  home_corners: number
  away_corners: number
  home_fouls: number
  away_fouls: number
  home_yellow_cards: number
  away_yellow_cards: number
  home_red_cards: number
  away_red_cards: number
}

export interface MatchDetails extends Match {
  venue?: string
  weather?: string
  attendance?: number
  referee?: string
  home_team_form: string[]
  away_team_form: string[]
  head_to_head: {
    home_wins: number
    draws: number
    away_wins: number
    last_matches: Array<{
      date: string
      home_team: string
      away_team: string
      home_score: number
      away_score: number
    }>
  }
}

export interface UserProfile {
  id: number
  username: string
  email: string
  role: 'user' | 'admin'
  bankroll: number
  total_winnings: number
  total_bets: number
  win_rate: number
  roi: number
  created_at: string
  last_login?: string
  avatar?: string
  phone?: string
  timezone?: string
  currency?: string
}

export interface HistoryRecord {
  id: number
  match_id: number
  home_team: string
  away_team: string
  league: string
  scheduled_at: string
  prediction: 'home_win' | 'draw' | 'away_win'
  predicted_outcome: 'home_win' | 'draw' | 'away_win'
  actual_outcome?: 'home_win' | 'draw' | 'away_win'
  stake: number
  odds: number
  result?: 'win' | 'loss' | 'push'
  profit: number
  confidence: number
  created_at: string
  match_status?: string
  final_score?: {
    home: number
    away: number
  }
}

export interface HistoryResponse {
  records: HistoryRecord[]
  total: number
  page: number
  limit: number
  stats: {
    total_bets: number
    total_winnings: number
    total_loss: number
    win_count: number
    loss_count: number
    push_count: number
    win_rate: number
    roi: number
  }
}

export interface UserUpdateData {
  username?: string
  email?: string
  phone?: string
  timezone?: string
  currency?: string
  notification_settings?: {
    email_notifications: boolean
    prediction_reminders: boolean
    result_notifications: boolean
  }
}

export interface ApiResponse<T = any> {
  data: T
  message: string
  status: 'success' | 'error'
  error?: string
}