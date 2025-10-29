import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { PredictionResponse } from '../../services/api';
import { apiService } from '../../services/api';

// 异步thunk
export const fetchPrediction = createAsyncThunk(
  'predictions/fetchPrediction',
  async (matchId: number) => {
    const response = await apiService.getPrediction(matchId);
    return { matchId, prediction: response };
  }
);

export const generatePrediction = createAsyncThunk(
  'predictions/generatePrediction',
  async (matchId: number) => {
    const response = await apiService.generatePrediction(matchId);
    return { matchId, prediction: response };
  }
);

export const batchPredict = createAsyncThunk(
  'predictions/batchPredict',
  async (matchIds: number[]) => {
    const response = await apiService.batchPredict(matchIds);
    return response;
  }
);

export const fetchPredictionHistory = createAsyncThunk(
  'predictions/fetchHistory',
  async (matchId: number) => {
    const response = await apiService.getPredictionHistory(matchId);
    return { matchId, history: response };
  }
);

// 状态接口
interface PredictionsState {
  // 单个预测缓存
  predictions: Record<number, PredictionResponse>;

  // 批量预测结果
  batchPredictions: PredictionResponse[];

  // 历史预测
  predictionHistory: Record<number, PredictionResponse[]>;

  // 加载状态
  loading: Record<number, boolean>; // 每个matchId的加载状态
  batchLoading: boolean;

  // 错误状态
  errors: Record<number, string | null>;
  batchError: string | null;

  // 统计信息
  stats: {
    totalPredictions: number;
    accuracyRate: number;
    avgConfidence: number;
  } | null;
}

// 初始状态
const initialState: PredictionsState = {
  predictions: {},
  batchPredictions: [],
  predictionHistory: {},
  loading: {},
  batchLoading: false,
  errors: {},
  batchError: null,
  stats: null,
};

// Slice定义
const predictionsSlice = createSlice({
  name: 'predictions',
  initialState,
  reducers: {
    // 清除单个预测错误
    clearPredictionError: (state, action: PayloadAction<number>) => {
      const matchId = action.payload;
      state.errors[matchId] = null;
    },

    // 清除批量预测错误
    clearBatchError: (state) => {
      state.batchError = null;
    },

    // 清除批量预测结果
    clearBatchPredictions: (state) => {
      state.batchPredictions = [];
    },

    // 更新预测置信度
    updatePredictionConfidence: (state, action: PayloadAction<{ matchId: number; confidence: number }>) => {
      const { matchId, confidence } = action.payload;
      if (state.predictions[matchId]) {
        state.predictions[matchId].confidence = confidence;
      }
    },

    // 设置统计信息
    setStats: (state, action: PayloadAction<PredictionsState['stats']>) => {
      state.stats = action.payload;
    },

    // 清除所有预测数据
    clearAllPredictions: (state) => {
      state.predictions = {};
      state.batchPredictions = [];
      state.predictionHistory = {};
      state.loading = {};
      state.errors = {};
      state.batchError = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // 获取单个预测
      .addCase(fetchPrediction.pending, (state, action) => {
        const matchId = action.meta.arg;
        state.loading[matchId] = true;
        state.errors[matchId] = null;
      })
      .addCase(fetchPrediction.fulfilled, (state, action) => {
        const { matchId, prediction } = action.payload;
        state.loading[matchId] = false;
        state.predictions[matchId] = prediction;
        state.errors[matchId] = null;
      })
      .addCase(fetchPrediction.rejected, (state, action) => {
        const matchId = action.meta.arg;
        state.loading[matchId] = false;
        state.errors[matchId] = action.error.message || '获取预测失败';
      })

      // 生成预测
      .addCase(generatePrediction.pending, (state, action) => {
        const matchId = action.meta.arg;
        state.loading[matchId] = true;
        state.errors[matchId] = null;
      })
      .addCase(generatePrediction.fulfilled, (state, action) => {
        const { matchId, prediction } = action.payload;
        state.loading[matchId] = false;
        state.predictions[matchId] = prediction;
        state.errors[matchId] = null;
      })
      .addCase(generatePrediction.rejected, (state, action) => {
        const matchId = action.meta.arg;
        state.loading[matchId] = false;
        state.errors[matchId] = action.error.message || '生成预测失败';
      })

      // 批量预测
      .addCase(batchPredict.pending, (state) => {
        state.batchLoading = true;
        state.batchError = null;
      })
      .addCase(batchPredict.fulfilled, (state, action) => {
        state.batchLoading = false;
        state.batchPredictions = action.payload.predictions;
        state.batchError = null;

        // 更新单个预测缓存
        action.payload.predictions.forEach(prediction => {
          if (prediction.match_id) {
            state.predictions[prediction.match_id] = prediction;
          }
        });
      })
      .addCase(batchPredict.rejected, (state, action) => {
        state.batchLoading = false;
        state.batchError = action.error.message || '批量预测失败';
      })

      // 获取预测历史
      .addCase(fetchPredictionHistory.pending, (state, action) => {
        const matchId = action.meta.arg;
        state.loading[matchId] = true;
        state.errors[matchId] = null;
      })
      .addCase(fetchPredictionHistory.fulfilled, (state, action) => {
        const { matchId, history } = action.payload;
        state.loading[matchId] = false;
        state.predictionHistory[matchId] = history;
        state.errors[matchId] = null;
      })
      .addCase(fetchPredictionHistory.rejected, (state, action) => {
        const matchId = action.meta.arg;
        state.loading[matchId] = false;
        state.errors[matchId] = action.error.message || '获取预测历史失败';
      });
  },
});

// 导出actions
export const {
  clearPredictionError,
  clearBatchError,
  clearBatchPredictions,
  updatePredictionConfidence,
  setStats,
  clearAllPredictions,
} = predictionsSlice.actions;

// 选择器
export const selectPrediction = (state: { predictions: PredictionsState }, matchId: number) =>
  state.predictions.predictions[matchId];

export const selectPredictionLoading = (state: { predictions: PredictionsState }, matchId: number) =>
  state.predictions.loading[matchId] || false;

export const selectPredictionError = (state: { predictions: PredictionsState }, matchId: number) =>
  state.predictions.errors[matchId];

export const selectBatchPredictions = (state: { predictions: PredictionsState }) =>
  state.predictions.batchPredictions;

export const selectBatchLoading = (state: { predictions: PredictionsState }) =>
  state.predictions.batchLoading;

export const selectBatchError = (state: { predictions: PredictionsState }) =>
  state.predictions.batchError;

export const selectPredictionHistory = (state: { predictions: PredictionsState }, matchId: number) =>
  state.predictions.predictionHistory[matchId] || [];

export const selectStats = (state: { predictions: PredictionsState }) =>
  state.predictions.stats;

// 计算选择器
export const selectPredictionsCount = (state: { predictions: PredictionsState }) =>
  Object.keys(state.predictions.predictions).length;

export const selectAverageConfidence = (state: { predictions: PredictionsState }) => {
  const predictions = Object.values(state.predictions.predictions);
  if (predictions.length === 0) return 0;

  const totalConfidence = predictions.reduce((sum, pred) => sum + pred.confidence, 0);
  return totalConfidence / predictions.length;
};

// 导出reducer
export default predictionsSlice.reducer;