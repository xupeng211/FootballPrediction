import axios, { AxiosInstance, AxiosResponse } from 'axios';

// API响应类型定义
export interface PredictionResponse {
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
  confidence: number;
  prediction: 'home_win' | 'draw' | 'away_win';
  match_id?: number;
  ev?: number; // 期望收益
  suggestion?: string; // 投注建议
}

// 球队信息接口
export interface TeamInfo {
  id: number;
  name: string;
  short_name?: string;
}

// 联赛信息接口
export interface LeagueInfo {
  id: number;
  name: string;
  country: string;
}

// 辅助函数：获取联赛名称，兼容新旧数据格式
export const getLeagueName = (league: LeagueInfo | string): string => {
  if (typeof league === 'object' && league !== null && league.name) {
    return league.name;
  }
  return String(league);
};

// 辅助函数：获取球队名称，兼容新旧数据格式
export const getTeamName = (team: TeamInfo | string): string => {
  if (typeof team === 'object' && team !== null && team.name) {
    return team.name;
  }
  return String(team);
};

export interface MatchData {
  id: number;
  home_team: TeamInfo | string;  // 兼容新旧格式
  away_team: TeamInfo | string;  // 兼容新旧格式
  match_date: string;
  league: LeagueInfo | string;  // 兼容新旧格式
  status: 'upcoming' | 'live' | 'finished';
  home_score?: number;
  away_score?: number;
}

export interface BatchPredictionRequest {
  match_ids: number[];
}

export interface BatchPredictionResponse {
  predictions: PredictionResponse[];
  total_processed: number;
  success_count: number;
}

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1',
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 请求拦截器
    this.client.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // 响应拦截器
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        console.log(`API Response: ${response.status} ${response.config.url}`);
        return response;
      },
      (error) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // 获取比赛列表
  async getMatches(params?: {
    league?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<MatchData[]> {
    try {
      const response = await this.client.get('/matches', { params });

      // 后端返回 { "matches": [...] } 结构，需要提取 matches 数组
      const responseData = response.data;
      if (responseData && Array.isArray(responseData.matches)) {
        return responseData.matches;
      }

      // 防御性检查：如果直接返回数组
      if (Array.isArray(responseData)) {
        return responseData;
      }

      // 如果都不是，返回空数组
      console.warn('API returned unexpected data structure:', responseData);
      return [];
    } catch (error) {
      console.error('获取比赛列表失败:', error);
      throw error;
    }
  }

  // 获取单个比赛预测
  async getPrediction(matchId: number): Promise<PredictionResponse> {
    try {
      const response = await this.client.get(`/predictions/${matchId}`);
      return response.data;
    } catch (error) {
      console.error('获取预测失败:', error);
      throw error;
    }
  }

  // 生成预测
  async generatePrediction(matchId: number): Promise<PredictionResponse> {
    try {
      const response = await this.client.post(`/predictions/${matchId}/predict`);
      return response.data;
    } catch (error) {
      console.error('生成预测失败:', error);
      throw error;
    }
  }

  // 批量预测
  async batchPredict(matchIds: number[]): Promise<BatchPredictionResponse> {
    try {
      const response = await this.client.post('/predictions/batch', {
        match_ids: matchIds,
      });
      return response.data;
    } catch (error) {
      console.error('批量预测失败:', error);
      throw error;
    }
  }

  // 获取历史预测
  async getPredictionHistory(matchId: number): Promise<PredictionResponse[]> {
    try {
      const response = await this.client.get(`/predictions/history/${matchId}`);
      return response.data;
    } catch (error) {
      console.error('获取历史预测失败:', error);
      throw error;
    }
  }

  // 获取系统状态
  async getSystemStatus(): Promise<{
    status: 'healthy' | 'degraded' | 'down';
    version: string;
    uptime: number;
    database_status: string;
    cache_status: string;
  }> {
    try {
      const response = await this.client.get('/health');
      return response.data;
    } catch (error) {
      console.error('获取系统状态失败:', error);
      throw error;
    }
  }

  // 获取统计信息
  async getStats(): Promise<{
    total_matches: number;
    total_predictions: number;
    accuracy_rate: number;
    avg_confidence: number;
  }> {
    try {
      const response = await this.client.get('/stats');
      const data = response.data;

      // 适配后端返回的嵌套格式到前端期望的格式
      return {
        total_matches: data.system?.total_matches || 0,
        total_predictions: data.system?.total_predictions || 0,
        accuracy_rate: data.accuracy?.overall_accuracy || 0.0,
        avg_confidence: data.performance?.success_rate || 0.0, // 使用成功率作为置信度近似
      };
    } catch (error) {
      console.error('获取统计信息失败:', error);
      throw error;
    }
  }
}

// 导出单例实例
export const apiService = new ApiService();
export default apiService;
