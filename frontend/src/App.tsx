import React, { useEffect, Suspense, lazy, useState } from 'react';
import {
  Typography,
  Spin,
  ConfigProvider,
  theme as antdTheme
} from 'antd';
import { useDispatch, useSelector } from 'react-redux';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { RootState, AppDispatch } from './store';
import { setGlobalLoading, addNotification } from './store/slices/uiSlice';
import { fetchMatches } from './store/slices/matchesSlice';
import { apiService } from './services/api';
import ResponsiveLayout from './components/ResponsiveLayout';
import MobileOptimizedLayout from './components/MobileOptimizedLayout';

// 代码分割 - 懒加载组件
const Dashboard = lazy(() => import('./components/Dashboard'));
const MatchList = lazy(() => import('./components/MatchList'));
const Analytics = lazy(() => import('./components/Analytics'));
const Settings = lazy(() => import('./components/Settings'));
const HelpCenter = lazy(() => import('./components/HelpCenter'));

const { Text } = Typography;

const App: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const globalLoading = useSelector((state: RootState) => state.ui.globalLoading);
  const theme = useSelector((state: RootState) => state.ui.theme);
  const [useMobileLayout, setUseMobileLayout] = useState(false);

  // 检测设备类型并选择布局
  useEffect(() => {
    const checkDeviceType = () => {
      const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
                       (window.innerWidth <= 768);
      setUseMobileLayout(isMobile);
    };

    checkDeviceType();
    window.addEventListener('resize', checkDeviceType);
    return () => window.removeEventListener('resize', checkDeviceType);
  }, []);

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
          message: 'API连接正常，数据加载完成'
        }));
      } catch (error) {
        console.error('应用初始化失败:', error);
        dispatch(addNotification({
          type: 'error',
          title: '系统初始化失败',
          message: '无法连接到后端API，请检查网络连接'
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
          algorithm: theme === 'dark' ? antdTheme.darkAlgorithm : undefined
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
        algorithm: theme === 'dark' ? antdTheme.darkAlgorithm : undefined
      }}
    >
      <Router>
        <Routes>
          <Route
            path="/"
            element={
              useMobileLayout ? (
                <MobileOptimizedLayout title="仪表板">
                  <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载仪表板..." /></div>}>
                    <Dashboard />
                  </Suspense>
                </MobileOptimizedLayout>
              ) : (
                <ResponsiveLayout pageTitle="仪表板">
                  <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载仪表板..." /></div>}>
                    <Dashboard />
                  </Suspense>
                </ResponsiveLayout>
              )
            }
          />
          <Route
            path="/dashboard"
            element={
              useMobileLayout ? (
                <MobileOptimizedLayout title="仪表板">
                  <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载仪表板..." /></div>}>
                    <Dashboard />
                  </Suspense>
                </MobileOptimizedLayout>
              ) : (
                <ResponsiveLayout pageTitle="仪表板">
                  <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载仪表板..." /></div>}>
                    <Dashboard />
                  </Suspense>
                </ResponsiveLayout>
              )
            }
          />
          <Route
            path="/matches"
            element={
              useMobileLayout ? (
                <MobileOptimizedLayout title="比赛预测">
                  <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载比赛预测..." /></div>}>
                    <MatchList />
                  </Suspense>
                </MobileOptimizedLayout>
              ) : (
                <ResponsiveLayout pageTitle="比赛预测">
                  <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载比赛预测..." /></div>}>
                    <MatchList />
                  </Suspense>
                </ResponsiveLayout>
              )
            }
          />
          <Route
            path="/analytics"
            element={
              useMobileLayout ? (
                <MobileOptimizedLayout title="数据分析">
                  <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载数据分析..." /></div>}>
                    <Analytics />
                  </Suspense>
                </MobileOptimizedLayout>
              ) : (
                <ResponsiveLayout pageTitle="数据分析">
                  <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载数据分析..." /></div>}>
                    <Analytics />
                  </Suspense>
                </ResponsiveLayout>
              )
            }
          />
          <Route
            path="/settings"
            element={
              useMobileLayout ? (
                <MobileOptimizedLayout title="系统设置">
                  <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载系统设置..." /></div>}>
                    <Settings />
                  </Suspense>
                </MobileOptimizedLayout>
              ) : (
                <ResponsiveLayout pageTitle="系统设置">
                  <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载系统设置..." /></div>}>
                    <Settings />
                  </Suspense>
                </ResponsiveLayout>
              )
            }
          />
          <Route
            path="/help"
            element={
              useMobileLayout ? (
                <MobileOptimizedLayout title="帮助中心">
                  <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载帮助中心..." /></div>}>
                    <HelpCenter />
                  </Suspense>
                </MobileOptimizedLayout>
              ) : (
                <ResponsiveLayout pageTitle="帮助中心">
                  <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载帮助中心..." /></div>}>
                    <HelpCenter />
                  </Suspense>
                </ResponsiveLayout>
              )
            }
          />
        </Routes>
      </Router>
    </ConfigProvider>
  );
};

export default App;
