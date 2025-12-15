import type { Prediction, Match } from '@/types/prediction';
export declare function usePredictions(): {
    predictions: import("vue").Ref<{
        match_id: number;
        prediction: string;
        predicted_outcome: string;
        home_win_prob: number;
        draw_prob: number;
        away_win_prob: number;
        confidence: number;
        success: boolean;
        mode?: string | undefined;
        mock_reason?: string | null | undefined;
        features_used?: string[] | undefined;
        created_at?: string | undefined;
    }[], Prediction[] | {
        match_id: number;
        prediction: string;
        predicted_outcome: string;
        home_win_prob: number;
        draw_prob: number;
        away_win_prob: number;
        confidence: number;
        success: boolean;
        mode?: string | undefined;
        mock_reason?: string | null | undefined;
        features_used?: string[] | undefined;
        created_at?: string | undefined;
    }[]>;
    loading: import("vue").Ref<boolean, boolean>;
    error: import("vue").Ref<string | null, string | null>;
    fetchPredictions: (matchId?: number) => Promise<void>;
    successfulPredictions: import("vue").ComputedRef<{
        match_id: number;
        prediction: string;
        predicted_outcome: string;
        home_win_prob: number;
        draw_prob: number;
        away_win_prob: number;
        confidence: number;
        success: boolean;
        mode?: string | undefined;
        mock_reason?: string | null | undefined;
        features_used?: string[] | undefined;
        created_at?: string | undefined;
    }[]>;
    highConfidencePredictions: import("vue").ComputedRef<{
        match_id: number;
        prediction: string;
        predicted_outcome: string;
        home_win_prob: number;
        draw_prob: number;
        away_win_prob: number;
        confidence: number;
        success: boolean;
        mode?: string | undefined;
        mock_reason?: string | null | undefined;
        features_used?: string[] | undefined;
        created_at?: string | undefined;
    }[]>;
};
export declare function useMatches(): {
    matches: import("vue").Ref<{
        id: number;
        home_team: string;
        away_team: string;
        scheduled_at: string;
        league: string;
        status: string;
        score?: {
            home: number;
            away: number;
        } | undefined;
        odds?: {
            home_win: number;
            draw: number;
            away_win: number;
        } | undefined;
    }[], Match[] | {
        id: number;
        home_team: string;
        away_team: string;
        scheduled_at: string;
        league: string;
        status: string;
        score?: {
            home: number;
            away: number;
        } | undefined;
        odds?: {
            home_win: number;
            draw: number;
            away_win: number;
        } | undefined;
    }[]>;
    loading: import("vue").Ref<boolean, boolean>;
    error: import("vue").Ref<string | null, string | null>;
    fetchRecentMatches: (limit?: number) => Promise<void>;
    upcomingMatches: import("vue").ComputedRef<{
        id: number;
        home_team: string;
        away_team: string;
        scheduled_at: string;
        league: string;
        status: string;
        score?: {
            home: number;
            away: number;
        } | undefined;
        odds?: {
            home_win: number;
            draw: number;
            away_win: number;
        } | undefined;
    }[]>;
    liveMatches: import("vue").ComputedRef<{
        id: number;
        home_team: string;
        away_team: string;
        scheduled_at: string;
        league: string;
        status: string;
        score?: {
            home: number;
            away: number;
        } | undefined;
        odds?: {
            home_win: number;
            draw: number;
            away_win: number;
        } | undefined;
    }[]>;
};
export declare function useHealthCheck(): {
    isHealthy: import("vue").Ref<boolean, boolean>;
    lastCheck: import("vue").Ref<Date | null, Date | null>;
    checking: import("vue").Ref<boolean, boolean>;
    checkHealth: () => Promise<void>;
    startAutoCheck: () => void;
};
