import { createSlice, PayloadAction } from '@reduxjs/toolkit';

// UI状态接口
interface UIState {
  // 主题模式
  theme: 'light' | 'dark';

  // 侧边栏状态
  sidebarCollapsed: boolean;

  // 加载状态
  globalLoading: boolean;

  // 模态框状态
  modals: {
    predictionDetails: boolean;
    batchPrediction: boolean;
    settings: boolean;
    help: boolean;
  };

  // 当前选中的比赛
  selectedMatchId: number | null;

  // 通知消息
  notifications: Array<{
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    title: string;
    message?: string;
    timestamp: number;
    read: boolean;
  }>;

  // 页面标题
  pageTitle: string;

  // 布局设置
  layout: {
    contentPadding: number;
    headerHeight: number;
    sidebarWidth: number;
  };

  // 用户偏好
  preferences: {
    autoRefresh: boolean;
    refreshInterval: number; // 秒
    showConfidence: boolean;
    showEV: boolean;
    defaultPageSize: number;
  };
}

// 初始状态
const initialState: UIState = {
  theme: 'light',
  sidebarCollapsed: false,
  globalLoading: false,
  modals: {
    predictionDetails: false,
    batchPrediction: false,
    settings: false,
    help: false,
  },
  selectedMatchId: null,
  notifications: [],
  pageTitle: '足球预测系统',
  layout: {
    contentPadding: 24,
    headerHeight: 64,
    sidebarWidth: 256,
  },
  preferences: {
    autoRefresh: true,
    refreshInterval: 30,
    showConfidence: true,
    showEV: true,
    defaultPageSize: 20,
  },
};

// Slice定义
const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    // 切换主题
    toggleTheme: (state) => {
      state.theme = state.theme === 'light' ? 'dark' : 'light';
    },

    // 设置主题
    setTheme: (state, action: PayloadAction<'light' | 'dark'>) => {
      state.theme = action.payload;
    },

    // 切换侧边栏
    toggleSidebar: (state) => {
      state.sidebarCollapsed = !state.sidebarCollapsed;
    },

    // 设置侧边栏状态
    setSidebarCollapsed: (state, action: PayloadAction<boolean>) => {
      state.sidebarCollapsed = action.payload;
    },

    // 设置全局加载状态
    setGlobalLoading: (state, action: PayloadAction<boolean>) => {
      state.globalLoading = action.payload;
    },

    // 打开模态框
    openModal: (state, action: PayloadAction<keyof UIState['modals']>) => {
      state.modals[action.payload] = true;
    },

    // 关闭模态框
    closeModal: (state, action: PayloadAction<keyof UIState['modals']>) => {
      state.modals[action.payload] = false;
    },

    // 关闭所有模态框
    closeAllModals: (state) => {
      Object.keys(state.modals).forEach(key => {
        state.modals[key as keyof UIState['modals']] = false;
      });
    },

    // 设置选中的比赛
    setSelectedMatchId: (state, action: PayloadAction<number | null>) => {
      state.selectedMatchId = action.payload;
    },

    // 添加通知
    addNotification: (state, action: PayloadAction<Omit<UIState['notifications'][0], 'id' | 'timestamp' | 'read'>>) => {
      const notification = {
        ...action.payload,
        id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
        timestamp: Date.now(),
        read: false,
      };
      state.notifications.unshift(notification);

      // 限制通知数量，保留最新的50条
      if (state.notifications.length > 50) {
        state.notifications = state.notifications.slice(0, 50);
      }
    },

    // 标记通知为已读
    markNotificationAsRead: (state, action: PayloadAction<string>) => {
      const notification = state.notifications.find(n => n.id === action.payload);
      if (notification) {
        notification.read = true;
      }
    },

    // 删除通知
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(n => n.id !== action.payload);
    },

    // 清除所有通知
    clearAllNotifications: (state) => {
      state.notifications = [];
    },

    // 标记所有通知为已读
    markAllNotificationsAsRead: (state) => {
      state.notifications.forEach(notification => {
        notification.read = true;
      });
    },

    // 设置页面标题
    setPageTitle: (state, action: PayloadAction<string>) => {
      state.pageTitle = action.payload;
    },

    // 更新布局设置
    updateLayout: (state, action: PayloadAction<Partial<UIState['layout']>>) => {
      state.layout = { ...state.layout, ...action.payload };
    },

    // 更新用户偏好
    updatePreferences: (state, action: PayloadAction<Partial<UIState['preferences']>>) => {
      state.preferences = { ...state.preferences, ...action.payload };
    },

    // 重置UI状态
    resetUIState: (state) => {
      return { ...initialState, preferences: state.preferences }; // 保留用户偏好
    },
  },
});

// 导出actions
export const {
  toggleTheme,
  setTheme,
  toggleSidebar,
  setSidebarCollapsed,
  setGlobalLoading,
  openModal,
  closeModal,
  closeAllModals,
  setSelectedMatchId,
  addNotification,
  markNotificationAsRead,
  removeNotification,
  clearAllNotifications,
  markAllNotificationsAsRead,
  setPageTitle,
  updateLayout,
  updatePreferences,
  resetUIState,
} = uiSlice.actions;

// 选择器
export const selectTheme = (state: { ui: UIState }) => state.ui.theme;
export const selectSidebarCollapsed = (state: { ui: UIState }) => state.ui.sidebarCollapsed;
export const selectGlobalLoading = (state: { ui: UIState }) => state.ui.globalLoading;
export const selectModals = (state: { ui: UIState }) => state.ui.modals;
export const selectSelectedMatchId = (state: { ui: UIState }) => state.ui.selectedMatchId;
export const selectNotifications = (state: { ui: UIState }) => state.ui.notifications;
export const selectUnreadNotifications = (state: { ui: UIState }) =>
  state.ui.notifications.filter(n => !n.read);
export const selectPageTitle = (state: { ui: UIState }) => state.ui.pageTitle;
export const selectLayout = (state: { ui: UIState }) => state.ui.layout;
export const selectPreferences = (state: { ui: UIState }) => state.ui.preferences;

// 导出reducer
export default uiSlice.reducer;