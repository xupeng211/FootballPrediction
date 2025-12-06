/**
 * 移动端优化布局组件
 *
 * Mobile Optimized Layout Component
 *
 * 提供移动端优化的响应式布局功能，包括：
 * - 自适应卡片布局
 * - 触摸友好的交互
 * - 折叠式侧边栏
 * - 移动端手势支持
 * - 优化的性能表现
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Layout,
  Row,
  Col,
  Card,
  Button,
  Space,
  Drawer,
  Menu,
  Avatar,
  Badge,
  Typography,
  Switch,
  Tooltip,
  Dropdown,
  Divider,
  Affix,
  BackTop
} from 'antd';
import '../styles/mobile-optimized.css';
import {
  MenuOutlined,
  BellOutlined,
  SettingOutlined,
  UserOutlined,
  HomeOutlined,
  BarChartOutlined,
  TrophyOutlined,
  LineChartOutlined,
  FireOutlined,
  RocketOutlined,
  VerticalAlignTopOutlined,
  DashboardOutlined,
  MobileOutlined,
  TabletOutlined,
  LaptopOutlined
} from '@ant-design/icons';
import { useMediaQuery } from 'react-responsive';

const { Header, Sider, Content } = Layout;
const { Text, Title } = Typography;

interface MobileOptimizedLayoutProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  showBreadcrumb?: boolean;
  breadcrumbItems?: Array<{ title: string; path?: string }>;
  extra?: React.ReactNode;
}

const MobileOptimizedLayout: React.FC<MobileOptimizedLayoutProps> = ({
  children,
  className,
  title = '足球预测系统',
  showBreadcrumb = false,
  breadcrumbItems = [],
  extra
}) => {
  // 响应式断点检测
  const isMobile = useMediaQuery({ maxWidth: 768 });
  const isTablet = useMediaQuery({ minWidth: 769, maxWidth: 1024 });
  const isDesktop = useMediaQuery({ minWidth: 1025 });

  // 状态管理
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [currentView, setCurrentView] = useState('dashboard');
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [notifications, setNotifications] = useState(3);

  // 引用
  const contentRef = useRef<HTMLDivElement>(null);

  // 根据设备类型自动调整布局
  useEffect(() => {
    if (isMobile) {
      setCollapsed(true);
      setDrawerVisible(false);
    } else if (isTablet) {
      setCollapsed(false);
    }
  }, [isMobile, isTablet]);

  // 菜单项配置
  const menuItems = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: '仪表板',
      description: '系统概览和实时数据'
    },
    {
      key: 'predictions',
      icon: <TrophyOutlined />,
      label: '预测分析',
      description: '比赛预测和结果分析'
    },
    {
      key: 'analytics',
      icon: <BarChartOutlined />,
      label: '数据分析',
      description: '深度数据分析和可视化'
    },
    {
      key: 'realtime',
      icon: <LineChartOutlined />,
      label: '实时监控',
      description: 'WebSocket实时数据流'
    },
    {
      key: 'history',
      icon: <FireOutlined />,
      label: '历史记录',
      description: '预测历史和趋势分析'
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
      description: '个性化配置和偏好设置'
    }
  ];

  // 移动端菜单项（简化版）
  const mobileMenuItems = [
    { key: 'dashboard', icon: <HomeOutlined />, label: '首页' },
    { key: 'predictions', icon: <TrophyOutlined />, label: '预测' },
    { key: 'analytics', icon: <BarChartOutlined />, label: '分析' },
    { key: 'realtime', icon: <LineChartOutlined />, label: '实时' },
    { key: 'history', icon: <FireOutlined />, label: '历史' },
    { key: 'settings', icon: <SettingOutlined />, label: '设置' }
  ];

  // 处理菜单点击
  const handleMenuClick = (key: string) => {
    setCurrentView(key);
    if (isMobile) {
      setDrawerVisible(false);
    }
  };

  // 渲染侧边栏菜单
  const renderSidebarMenu = () => (
    <Menu
      mode="inline"
      selectedKeys={[currentView]}
      items={isMobile ? mobileMenuItems : menuItems}
      onClick={({ key }) => handleMenuClick(key)}
      style={{
        border: 'none',
        height: '100%',
        background: theme === 'dark' ? '#001529' : '#fff'
      }}
    />
  );

  // 渲染通知下拉菜单
  const notificationMenu = (
    <Menu style={{ width: 320, maxHeight: 400, overflow: 'auto' }}>
      <Menu.Item key="notif-1">
        <div>
          <Text strong>新预测完成</Text>
          <br />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            曼城 VS 利物浦的预测已完成
          </Text>
          <br />
          <Text type="secondary" style={{ fontSize: '11px' }}>
            2分钟前
          </Text>
        </div>
      </Menu.Item>
      <Menu.Item key="notif-2">
        <div>
          <Text strong>系统提醒</Text>
          <br />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            预测准确率已达到85%
          </Text>
          <br />
          <Text type="secondary" style={{ fontSize: '11px' }}>
            15分钟前
          </Text>
        </div>
      </Menu.Item>
      <Menu.Item key="notif-3">
        <div>
          <Text strong>比赛开始</Text>
          <br />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            拜仁 VS 多特的比赛即将开始
          </Text>
          <br />
          <Text type="secondary" style={{ fontSize: '11px' }}>
            30分钟前
          </Text>
        </div>
      </Menu.Item>
      <Divider style={{ margin: '8px 0' }} />
      <Menu.Item key="view-all">
        <Text style={{ color: '#1890ff' }}>查看所有通知</Text>
      </Menu.Item>
    </Menu>
  );

  // 渲染用户下拉菜单
  const userMenu = (
    <Menu>
      <Menu.Item key="profile" icon={<UserOutlined />}>
        个人资料
      </Menu.Item>
      <Menu.Item key="preferences" icon={<SettingOutlined />}>
        偏好设置
      </Menu.Item>
      <Menu.Divider />
      <Menu.Item key="logout">
        <Text type="danger">退出登录</Text>
      </Menu.Item>
    </Menu>
  );

  // 渲染设备状态指示器
  const renderDeviceIndicator = () => (
    <Space size="small">
      {isMobile && <MobileOutlined style={{ color: '#1890ff' }} />}
      {isTablet && <TabletOutlined style={{ color: '#52c41a' }} />}
      {isDesktop && <LaptopOutlined style={{ color: '#faad14' }} />}
      <Text type="secondary" style={{ fontSize: '12px' }}>
        {isMobile ? '移动端' : isTablet ? '平板端' : '桌面端'}
      </Text>
    </Space>
  );

  // 渲染头部
  const renderHeader = () => (
    <Header
      style={{
        background: theme === 'dark' ? '#001529' : '#fff',
        padding: isMobile ? '0 12px' : '0 24px',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 1000,
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}
    >
      <Space>
        {isMobile && (
          <Button
            type="text"
            icon={<MenuOutlined />}
            onClick={() => setDrawerVisible(true)}
            style={{ fontSize: '18px' }}
          />
        )}
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <RocketOutlined style={{
            fontSize: isMobile ? '20px' : '24px',
            color: '#1890ff',
            marginRight: isMobile ? '8px' : '12px'
          }} />
          {(!isMobile || !collapsed) && (
            <Title
              level={isMobile ? 5 : 4}
              style={{
                margin: 0,
                color: theme === 'dark' ? '#fff' : '#000',
                fontSize: isMobile ? '16px' : '20px'
              }}
            >
              {title}
            </Title>
          )}
        </div>
      </Space>

      <Space size="middle">
        {/* 设备状态指示器 - 仅在桌面端显示 */}
        {!isMobile && renderDeviceIndicator()}

        {/* 主题切换 */}
        <Tooltip title="切换主题">
          <Switch
            checked={theme === 'dark'}
            onChange={(checked) => setTheme(checked ? 'dark' : 'light')}
            size={isMobile ? 'small' : 'default'}
          />
        </Tooltip>

        {/* 通知铃铛 */}
        <Dropdown overlay={notificationMenu} placement="bottomRight" trigger={['click']}>
          <Badge count={notifications} size={isMobile ? 'small' : 'default'}>
            <Button
              type="text"
              icon={<BellOutlined />}
              style={{
                fontSize: isMobile ? '16px' : '18px',
                display: 'flex',
                alignItems: 'center'
              }}
            />
          </Badge>
        </Dropdown>

        {/* 用户菜单 */}
        <Dropdown overlay={userMenu} placement="bottomRight">
          <Button
            type="text"
            icon={<Avatar size={isMobile ? 'small' : 'default'} icon={<UserOutlined />} />}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: isMobile ? '4px 8px' : '4px 12px'
            }}
          >
            {!isMobile && <Text style={{ marginLeft: '8px' }}>用户</Text>}
          </Button>
        </Dropdown>
      </Space>
    </Header>
  );

  // 移动端抽屉侧边栏
  const renderMobileDrawer = () => (
    <Drawer
      title={
        <Space>
          <RocketOutlined style={{ color: '#1890ff' }} />
          <span>功能菜单</span>
        </Space>
      }
      placement="left"
      onClose={() => setDrawerVisible(false)}
      open={drawerVisible}
      bodyStyle={{ padding: 0 }}
      width={280}
    >
      {renderSidebarMenu()}
    </Drawer>
  );

  // 桌面端侧边栏
  const renderDesktopSider = () => (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={setCollapsed}
      theme={theme}
      width={isTablet ? 200 : 250}
      collapsedWidth={isTablet ? 60 : 80}
      style={{
        overflow: 'auto',
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 64, // Header高度
        bottom: 0,
        boxShadow: collapsed ? 'none' : '2px 0 8px rgba(0,0,0,0.15)'
      }}
    >
      {renderSidebarMenu()}
    </Sider>
  );

  // 计算内容区域边距
  const getContentStyle = () => {
    let marginLeft = 0;
    let padding = '24px';

    if (!isMobile) {
      marginLeft = collapsed ? (isTablet ? 60 : 80) : (isTablet ? 200 : 250);
      padding = isTablet ? '16px' : '24px';
    } else {
      padding = '12px';
    }

    return {
      marginLeft,
      padding,
      transition: 'margin-left 0.2s',
      minHeight: 'calc(100vh - 64px)'
    };
  };

  return (
    <Layout className={`${className} mobile-optimized touch-optimized`} style={{ minHeight: '100vh' }}>
      {/* 头部 */}
      {renderHeader()}

      {/* 移动端抽屉 */}
      {isMobile && renderMobileDrawer()}

      {/* 桌面端侧边栏 */}
      {!isMobile && renderDesktopSider()}

      {/* 主内容区域 */}
      <Content style={getContentStyle()}>
        {/* 面包屑导航 */}
        {showBreadcrumb && breadcrumbItems.length > 0 && (
          <Card size="small" style={{ marginBottom: 16 }}>
            <Space>
              <Text type="secondary">当前位置:</Text>
              {breadcrumbItems.map((item, index) => (
                <React.Fragment key={index}>
                  <Text
                    type={index === breadcrumbItems.length - 1 ? undefined : 'secondary'}
                    strong={index === breadcrumbItems.length - 1}
                  >
                    {item.title}
                  </Text>
                  {index < breadcrumbItems.length - 1 && (
                    <Text type="secondary">/</Text>
                  )}
                </React.Fragment>
              ))}
            </Space>
            {extra && <div style={{ float: 'right' }}>{extra}</div>}
          </Card>
        )}

        {/* 页面内容 */}
        <div ref={contentRef}>
          {children}
        </div>
      </Content>

      {/* 返回顶部按钮 */}
      <BackTop>
        <Button
          type="primary"
          shape="circle"
          icon={<VerticalAlignTopOutlined />}
          size={isMobile ? 'small' : 'middle'}
        />
      </BackTop>
    </Layout>
  );
};

export default MobileOptimizedLayout;
