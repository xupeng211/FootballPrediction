import type { Match, PredictionResponse, MatchDetails, MatchStats, UserProfile, HistoryResponse, UserUpdateData } from '@/types/prediction';
import type { AuthResponse } from '@/types/auth';
declare class ApiClient {
    private client;
    private refreshTokenPromise;
    constructor();
    private setupInterceptors;
    private attemptTokenRefresh;
    private handleAuthError;
    login(email: string, password: string): Promise<AuthResponse>;
    register(username: string, email: string, password: string): Promise<AuthResponse>;
    logout(): Promise<void>;
    refreshAuth(refreshToken: string): Promise<AuthResponse>;
    updateProfile(updates: any): Promise<any>;
    getUserProfile(): Promise<UserProfile>;
    getUserHistory(page?: number, limit?: number): Promise<HistoryResponse>;
    updateUserProfile(data: UserUpdateData): Promise<UserProfile>;
    private mockLogin;
    private mockRegister;
    private mockRefresh;
    healthCheck(): Promise<{
        status: string;
        message: string;
    }>;
    getPredictions(matchId?: number): Promise<PredictionResponse>;
    getRecentMatches(limit?: number): Promise<Match[]>;
    getMatch(matchId: number): Promise<Match>;
    getMatchDetails(matchId: number): Promise<MatchDetails>;
    getMatchStats(matchId: number): Promise<MatchStats>;
    private getMockPredictions;
    private getMockMatches;
    private getMockMatchDetails;
    private getMockMatchStats;
    private getMockUserProfile;
    private getMockUserHistory;
    private generateMockHistoryRecords;
}
declare const apiClient: ApiClient;
export default apiClient;
