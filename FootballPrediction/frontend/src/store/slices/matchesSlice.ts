import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { MatchData, getTeamName, getLeagueName } from '../../services/api';
import { apiService } from '../../services/api';

// 异步thunk用于获取比赛列表
export const fetchMatches = createAsyncThunk(
  'matches/fetchMatches',
  async (params?: {
    league?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const response = await apiService.getMatches(params);
    return response;
  }
);

// 状态接口定义
interface MatchesState {
  matches: MatchData[];
  loading: boolean;
  error: string | null;
  filters: {
    league?: string;
    status?: string;
    search?: string;
  };
  pagination: {
    currentPage: number;
    pageSize: number;
    total: number;
  };
}

// 初始状态
const initialState: MatchesState = {
  matches: [],
  loading: false,
  error: null,
  filters: {},
  pagination: {
    currentPage: 1,
    pageSize: 20,
    total: 0,
  },
};

// Slice定义
const matchesSlice = createSlice({
  name: 'matches',
  initialState,
  reducers: {
    // 设置过滤器
    setFilters: (state, action: PayloadAction<Partial<MatchesState['filters']>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },

    // 清除过滤器
    clearFilters: (state) => {
      state.filters = {};
    },

    // 设置分页
    setPagination: (state, action: PayloadAction<Partial<MatchesState['pagination']>>) => {
      state.pagination = { ...state.pagination, ...action.payload };
    },

    // 更新单个比赛
    updateMatch: (state, action: PayloadAction<MatchData>) => {
      const index = state.matches.findIndex(match => match.id === action.payload.id);
      if (index !== -1) {
        state.matches[index] = action.payload;
      }
    },

    // 清除错误
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // 获取比赛列表 - pending
      .addCase(fetchMatches.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      // 获取比赛列表 - fulfilled
      .addCase(fetchMatches.fulfilled, (state, action) => {
        state.loading = false;
        state.matches = action.payload;
        state.error = null;
      })
      // 获取比赛列表 - rejected
      .addCase(fetchMatches.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || '获取比赛列表失败';
      });
  },
});

// 导出actions
export const {
  setFilters,
  clearFilters,
  setPagination,
  updateMatch,
  clearError,
} = matchesSlice.actions;

// 选择器
export const selectMatches = (state: { matches: MatchesState }) => state.matches.matches;
export const selectMatchesLoading = (state: { matches: MatchesState }) => state.matches.loading;
export const selectMatchesError = (state: { matches: MatchesState }) => state.matches.error;
export const selectMatchesFilters = (state: { matches: MatchesState }) => state.matches.filters;
export const selectMatchesPagination = (state: { matches: MatchesState }) => state.matches.pagination;

// 过滤后的比赛列表
export const selectFilteredMatches = (state: { matches: MatchesState }) => {
  const { matches, filters } = state.matches;

  // 防御性检查：确保 matches 是数组
  const safeMatches = Array.isArray(matches) ? matches : [];

  return safeMatches.filter(match => {
    // 联赛过滤
    if (filters.league && match.league !== filters.league) {
      return false;
    }

    // 状态过滤
    if (filters.status && match.status !== filters.status) {
      return false;
    }

    // 搜索过滤
    if (filters.search) {
      const searchTerm = filters.search.toLowerCase();
      return (
        getTeamName(match.home_team).toLowerCase().includes(searchTerm) ||
        getTeamName(match.away_team).toLowerCase().includes(searchTerm) ||
        getLeagueName(match.league).toLowerCase().includes(searchTerm)
      );
    }

    return true;
  });
};

// 导出reducer
export default matchesSlice.reducer;
