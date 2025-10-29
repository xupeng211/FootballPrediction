import React, { useState, useEffect } from 'react';
import {
  Layout,
  Menu,
  Button,
  Space,
  Drawer,
  Typography,
  Row,
  Col,
} from 'antd';
import {
  MenuOutlined,
  DashboardOutlined,
  BarChartOutlined,
  TrophyOutlined,
  SettingOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';

const { Header, Content, Sider } = Layout;
const { Title, Text } = Typography;

interface ResponsiveLayoutProps {
  children: React.ReactNode;
  pageTitle?: string;
}

const ResponsiveLayout: React.FC<ResponsiveLayoutProps> = ({
  children,
  pageTitle = '足球预测系统',
}) => {
  const [isMobile, setIsMobile] = useState<boolean>(false);
  const [drawerVisible, setDrawerVisible] = useState<boolean>(false);
  const [collapsed, setCollapsed] = useState<boolean>(false);
  const navigate = useNavigate();
  const location = useLocation();

  // 检测移动端
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth < 768) {
        setCollapsed(true);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // 菜单项配置
  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '仪表板',
    },
    {
      key: '/matches',
      icon: <TrophyOutlined />,
      label: '比赛预测',
    },
    {
      key: '/analytics',
      icon: <BarChartOutlined />,
      label: '数据分析',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
    {
      key: '/help',
      icon: <QuestionCircleOutlined />,
      label: '帮助中心',
    },
  ];

  // 处理菜单点击
  const handleMenuClick = (key: string) => {
    navigate(key);
    if (isMobile) {
      setDrawerVisible(false);
    }
  };

  // 获取当前选中的菜单项
  const getSelectedKey = () => {
    const path = location.pathname;
    return menuItems.find(item => path.startsWith(item.key))?.key || '/dashboard';
  };

  // 移动端菜单
  const MobileMenu = () => (
    <Drawer
      title="菜单"
      placement="left"
      onClose={() => setDrawerVisible(false)}
      open={drawerVisible}
      bodyStyle={{ padding: 0 }}
      width={250}
    >
      <Menu
        mode="inline"
        selectedKeys={[getSelectedKey()]}
        items={menuItems}
        onClick={({ key }) => handleMenuClick(key)}
      />
    </Drawer>
  );

  // 桌面端侧边栏
  const DesktopSidebar = () => (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={setCollapsed}
      width={200}
      style={{
        overflow: 'auto',
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 64,
        bottom: 0,
      }}
    >
      <Menu
        mode="inline"
        selectedKeys={[getSelectedKey()]}
        items={menuItems}
        onClick={({ key }) => handleMenuClick(key)}
        style={{ height: '100%', borderRight: 0 }}
      />
    </Sider>
  );

  // 移动端头部
  const MobileHeader = () => (
    <Header
      style={{
        position: 'fixed',
        zIndex: 100,
        width: '100%',
        padding: '0 16px',
        background: '#fff',
        borderBottom: '1px solid #f0f0f0',
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Button
            type="text"
            icon={<MenuOutlined />}
            onClick={() => setDrawerVisible(true)}
            style={{ marginRight: 12 }}
          />
          <Title level={4} style={{ margin: 0, color: '#000' }}>
            ⚽ 预测系统
          </Title>
        </div>
        <Space>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {pageTitle}
          </Text>
        </Space>
      </div>
    </Header>
  );

  // 桌面端头部
  const DesktopHeader = () => (
    <Header
      style={{
        padding: '0 24px',
        background: '#fff',
        borderBottom: '1px solid #f0f0f0',
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        position: 'fixed',
        zIndex: 100,
        width: '100%',
        left: collapsed ? 80 : 200,
        transition: 'left 0.2s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Button
            type="text"
            icon={<MenuOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ marginRight: 16 }}
          />
          <Title level={3} style={{ margin: 0, color: '#000' }}>
            ⚽ 足球预测系统
          </Title>
        </div>
        <Space>
          <Text type="secondary">
            {pageTitle}
          </Text>
        </Space>
      </div>
    </Header>
  );

  // 移动端内容区域
  const MobileContent = () => (
    <div style={{ paddingTop: 64, minHeight: '100vh' }}>
      <Content style={{ padding: '16px' }}>
        <div style={{
          background: '#fff',
          borderRadius: '8px',
          padding: '16px',
          boxShadow: '0 1px 2px 0 rgba(0,0,0,0.03)',
        }}>
          {children}
        </div>
      </Content>
    </div>
  );

  // 桌面端内容区域
  const DesktopContent = () => (
    <Layout style={{ minHeight: '100vh' }}>
      <DesktopSidebar />
      <DesktopHeader />
      <Layout style={{ marginLeft: collapsed ? 80 : 200, transition: 'margin-left 0.2s' }}>
        <Content style={{
          margin: '80px 16px 16px 16px',
          padding: '24px',
          background: '#fff',
          borderRadius: '8px',
          boxShadow: '0 1px 2px 0 rgba(0,0,0,0.03)',
          overflow: 'auto',
        }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );

  // 移动端底部导航
  const MobileBottomNav = () => (
    <div style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      background: '#fff',
      borderTop: '1px solid #f0f0f0',
      padding: '8px 0',
      zIndex: 100,
    }}>
      <Row justify="space-around" align="middle">
        {menuItems.slice(0, 4).map(item => (
          <Col key={item.key} span={6}>
            <div
              style={{
                textAlign: 'center',
                padding: '8px',
                cursor: 'pointer',
                color: getSelectedKey() === item.key ? '#1890ff' : '#666',
              }}
              onClick={() => handleMenuClick(item.key)}
            >
              <div style={{ fontSize: '18px', marginBottom: '4px' }}>
                {item.icon}
              </div>
              <div style={{ fontSize: '12px' }}>
                {item.label}
              </div>
            </div>
          </Col>
        ))}
      </Row>
    </div>
  );

  if (isMobile) {
    return (
      <div className="mobile-layout">
        <MobileHeader />
        <MobileMenu />
        <MobileContent />
        <MobileBottomNav />
      </div>
    );
  }

  return <DesktopContent />;
};

export default ResponsiveLayout;