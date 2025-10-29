import React, { useEffect } from 'react';
import {
  Typography,
  Spin,
  ConfigProvider,
  theme as antdTheme,
} from 'antd';
import { useDispatch, useSelector } from 'react-redux';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { RootState, AppDispatch } from './store';
import { setGlobalLoading, addNotification } from './store/slices/uiSlice';
import { fetchMatches } from './store/slices/matchesSlice';
import { apiService } from './services/api';
import ResponsiveLayout from './components/ResponsiveLayout';
import MatchList from './components/MatchList';
import Dashboard from './components/Dashboard';
import Analytics from './components/Analytics';
import Settings from './components/Settings';
import HelpCenter from './components/HelpCenter';

const { Title, Text } = Typography;

const App: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const globalLoading = useSelector((state: RootState) => state.ui.globalLoading);
  const theme = useSelector((state: RootState) => state.ui.theme);

  // 应用初始化
  useEffect(() => {
    const initializeApp = async () => {
      try {
        dispatch(setGlobalLoading(true));

        // 检查API连接
        await apiService.getSystemStatus();

        // 获取初始数据
        await dispatch(fetchMatches()).unwrap();

        dispatch(addNotification({
          type: 'success',
          title: '系统初始化成功',
          message: 'API连接正常，数据加载完成',
        }));
      } catch (error) {
        console.error('应用初始化失败:', error);
        dispatch(addNotification({
          type: 'error',
          title: '系统初始化失败',
          message: '无法连接到后端API，请检查网络连接',
        }));
      } finally {
        dispatch(setGlobalLoading(false));
      }
    };

    initializeApp();
  }, [dispatch]);

  // 渲染加载状态
  if (globalLoading) {
    return (
      <ConfigProvider
        theme={{
          algorithm: theme === 'dark' ? antdTheme.darkAlgorithm : undefined,
        }}
      >
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          flexDirection: 'column',
          gap: '16px'
        }}>
          <Spin size="large" />
          <Text>正在初始化系统...</Text>
        </div>
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider
      theme={{
        algorithm: theme === 'dark' ? antdTheme.darkAlgorithm : undefined,
      }}
    >
      <Router>
        <Routes>
          <Route
            path="/"
            element={
              <ResponsiveLayout pageTitle="仪表板">
                <Dashboard />
              </ResponsiveLayout>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ResponsiveLayout pageTitle="仪表板">
                <Dashboard />
              </ResponsiveLayout>
            }
          />
          <Route
            path="/matches"
            element={
              <ResponsiveLayout pageTitle="比赛预测">
                <MatchList />
              </ResponsiveLayout>
            }
          />
          <Route
            path="/analytics"
            element={
              <ResponsiveLayout pageTitle="数据分析">
                <Analytics />
              </ResponsiveLayout>
            }
          />
          <Route
            path="/settings"
            element={
              <ResponsiveLayout pageTitle="系统设置">
                <Settings />
              </ResponsiveLayout>
            }
          />
          <Route
            path="/help"
            element={
              <ResponsiveLayout pageTitle="帮助中心">
                <HelpCenter />
              </ResponsiveLayout>
            }
          />
        </Routes>
      </Router>
    </ConfigProvider>
  );
};

export default App;
