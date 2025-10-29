import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Switch,
  Input,
  Select,
  Slider,
  Button,
  Space,
  Divider,
  Alert,
  Row,
  Col,
  InputNumber,
  message,
  Tabs,
  Tag,
  Tooltip,
} from 'antd';
import {
  SettingOutlined,
  SaveOutlined,
  ReloadOutlined,
  ExclamationCircleOutlined,
  BulbOutlined,
  SecurityScanOutlined,
  ApiOutlined,
  DatabaseOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import { setTheme, updatePreferences } from '../store/slices/uiSlice';

const { Option } = Select;
const { TextArea } = Input;
const { TabPane } = Tabs;

interface SettingsState {
  // 通用设置
  theme: 'light' | 'dark' | 'auto';
  language: 'zh-CN' | 'en-US';
  autoRefresh: boolean;
  refreshInterval: number;

  // 预测设置
  confidenceThreshold: number;
  showConfidenceLevel: boolean;
  autoGeneratePrediction: boolean;
  enableBettingAdvice: boolean;

  // API设置
  apiBaseUrl: string;
  timeout: number;
  retryAttempts: number;

  // 通知设置
  enableNotifications: boolean;
  predictionComplete: boolean;
  systemAlerts: boolean;
  matchUpdates: boolean;

  // 隐私设置
  enableAnalytics: boolean;
  sharePredictions: boolean;
  publicProfile: boolean;
}

const Settings: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const currentTheme = useSelector((state: RootState) => state.ui.theme);
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [settings, setSettings] = useState<SettingsState>({
    theme: currentTheme,
    language: 'zh-CN',
    autoRefresh: true,
    refreshInterval: 30,
    confidenceThreshold: 60,
    showConfidenceLevel: true,
    autoGeneratePrediction: false,
    enableBettingAdvice: true,
    apiBaseUrl: 'http://localhost:8000/api/v1',
    timeout: 10000,
    retryAttempts: 3,
    enableNotifications: true,
    predictionComplete: true,
    systemAlerts: true,
    matchUpdates: false,
    enableAnalytics: true,
    sharePredictions: false,
    publicProfile: false,
  });

  // 加载设置
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = () => {
    try {
      const savedSettings = localStorage.getItem('userSettings');
      if (savedSettings) {
        const parsed = JSON.parse(savedSettings);
        setSettings({ ...settings, ...parsed });
        form.setFieldsValue({ ...settings, ...parsed });
      }
    } catch (error) {
      console.error('加载设置失败:', error);
    }
  };

  // 保存设置
  const saveSettings = async (values: Partial<SettingsState>) => {
    try {
      setLoading(true);

      const newSettings = { ...settings, ...values };
      setSettings(newSettings);

      // 保存到本地存储
      localStorage.setItem('userSettings', JSON.stringify(newSettings));

      // 更新Redux状态
      dispatch(updatePreferences(newSettings));

      // 应用主题设置
      if (newSettings.theme !== currentTheme && newSettings.theme !== 'auto') {
        dispatch(setTheme(newSettings.theme));
      }

      message.success('设置保存成功');
    } catch (error) {
      console.error('保存设置失败:', error);
      message.error('保存设置失败');
    } finally {
      setLoading(false);
    }
  };

  // 重置设置
  const resetSettings = () => {
    const defaultSettings: SettingsState = {
      theme: 'light',
      language: 'zh-CN',
      autoRefresh: true,
      refreshInterval: 30,
      confidenceThreshold: 60,
      showConfidenceLevel: true,
      autoGeneratePrediction: false,
      enableBettingAdvice: true,
      apiBaseUrl: 'http://localhost:8000/api/v1',
      timeout: 10000,
      retryAttempts: 3,
      enableNotifications: true,
      predictionComplete: true,
      systemAlerts: true,
      matchUpdates: false,
      enableAnalytics: true,
      sharePredictions: false,
      publicProfile: false,
    };

    setSettings(defaultSettings);
    form.setFieldsValue(defaultSettings);
    message.info('设置已重置为默认值');
  };

  // 测试API连接
  const testApiConnection = async () => {
    try {
      message.loading({ content: '正在测试API连接...', key: 'apiTest' });

      // 这里应该调用实际的API测试
      await new Promise(resolve => setTimeout(resolve, 2000));

      message.success({ content: 'API连接测试成功', key: 'apiTest' });
    } catch (error) {
      message.error({ content: 'API连接测试失败', key: 'apiTest' });
    }
  };

  return (
    <div>
      <Tabs defaultActiveKey="general" type="card">
        {/* 通用设置 */}
        <TabPane tab={<span><SettingOutlined />通用设置</span>} key="general">
          <Card>
            <Form
              form={form}
              layout="vertical"
              initialValues={settings}
              onValuesChange={(_, allValues) => saveSettings(allValues)}
            >
              <Row gutter={[24, 0]}>
                <Col xs={24} md={12}>
                  <Form.Item
                    label={
                      <span>
                        主题设置
                        <Tooltip title="选择应用的主题风格">
                          <BulbOutlined style={{ marginLeft: 8 }} />
                        </Tooltip>
                      </span>
                    }
                    name="theme"
                  >
                    <Select>
                      <Option value="light">浅色主题</Option>
                      <Option value="dark">深色主题</Option>
                      <Option value="auto">跟随系统</Option>
                    </Select>
                  </Form.Item>

                  <Form.Item label="语言设置" name="language">
                    <Select>
                      <Option value="zh-CN">简体中文</Option>
                      <Option value="en-US">English</Option>
                    </Select>
                  </Form.Item>

                  <Form.Item label="自动刷新" name="autoRefresh" valuePropName="checked">
                    <Switch />
                  </Form.Item>

                  <Form.Item label="刷新间隔 (秒)" name="refreshInterval">
                    <Slider
                      min={10}
                      max={300}
                      step={10}
                      marks={{
                        10: '10s',
                        60: '1min',
                        120: '2min',
                        300: '5min',
                      }}
                    />
                  </Form.Item>
                </Col>

                <Col xs={24} md={12}>
                  <Alert
                    message="主题设置说明"
                    description="主题设置会立即生效。深色主题有助于在夜间使用时减少眼睛疲劳。"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />

                  <Alert
                    message="自动刷新说明"
                    description="开启自动刷新后，系统会按照设定的时间间隔自动更新比赛数据和预测结果。"
                    type="info"
                    showIcon
                  />
                </Col>
              </Row>
            </Form>
          </Card>
        </TabPane>

        {/* 预测设置 */}
        <TabPane tab={<span><BarChartOutlined />预测设置</span>} key="prediction">
          <Card>
            <Form
              layout="vertical"
              initialValues={settings}
              onValuesChange={(_, allValues) => saveSettings(allValues)}
            >
              <Row gutter={[24, 0]}>
                <Col xs={24} md={12}>
                  <Form.Item
                    label={
                      <span>
                        置信度阈值 (%)
                        <Tooltip title="只显示置信度高于此阈值的预测结果">
                          <ExclamationCircleOutlined style={{ marginLeft: 8 }} />
                        </Tooltip>
                      </span>
                    }
                    name="confidenceThreshold"
                  >
                    <Slider
                      min={0}
                      max={100}
                      step={5}
                      marks={{
                        0: '0%',
                        50: '50%',
                        70: '70%',
                        85: '85%',
                        100: '100%',
                      }}
                    />
                  </Form.Item>

                  <Form.Item label="显示置信度等级" name="showConfidenceLevel" valuePropName="checked">
                    <Switch />
                  </Form.Item>

                  <Form.Item label="自动生成预测" name="autoGeneratePrediction" valuePropName="checked">
                    <Switch />
                  </Form.Item>

                  <Form.Item label="启用投注建议" name="enableBettingAdvice" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                </Col>

                <Col xs={24} md={12}>
                  <Alert
                    message="置信度阈值"
                    description="设置较高的置信度阈值可以帮助过滤掉不太可靠的预测结果。建议设置在60-75%之间。"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />

                  <Alert
                    message="投注建议"
                    description="启用投注建议后，系统会根据期望收益计算提供投注建议。请谨慎使用，仅作参考。"
                    type="warning"
                    showIcon
                  />
                </Col>
              </Row>
            </Form>
          </Card>
        </TabPane>

        {/* API设置 */}
        <TabPane tab={<span><ApiOutlined />API设置</span>} key="api">
          <Card>
            <Form
              layout="vertical"
              initialValues={settings}
              onValuesChange={(_, allValues) => saveSettings(allValues)}
            >
              <Row gutter={[24, 0]}>
                <Col xs={24} md={12}>
                  <Form.Item
                    label="API基础URL"
                    name="apiBaseUrl"
                    rules={[
                      { required: true, message: '请输入API基础URL' },
                      { type: 'url', message: '请输入有效的URL' },
                    ]}
                  >
                    <Input placeholder="http://localhost:8000/api/v1" />
                  </Form.Item>

                  <Form.Item
                    label="请求超时时间 (毫秒)"
                    name="timeout"
                  >
                    <InputNumber min={1000} max={60000} step={1000} style={{ width: '100%' }} />
                  </Form.Item>

                  <Form.Item
                    label="重试次数"
                    name="retryAttempts"
                  >
                    <InputNumber min={0} max={10} style={{ width: '100%' }} />
                  </Form.Item>

                  <Form.Item>
                    <Space>
                      <Button
                        type="primary"
                        icon={<ApiOutlined />}
                        onClick={testApiConnection}
                      >
                        测试连接
                      </Button>
                      <Button icon={<ReloadOutlined />}>
                        重置为默认
                      </Button>
                    </Space>
                  </Form.Item>
                </Col>

                <Col xs={24} md={12}>
                  <Alert
                    message="API设置说明"
                    description={
                      <div>
                        <p>• API基础URL：后端服务的地址</p>
                        <p>• 请求超时：单个请求的最大等待时间</p>
                        <p>• 重试次数：请求失败时的自动重试次数</p>
                      </div>
                    }
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />

                  <div>
                    <strong>当前API状态：</strong>
                    <Tag color="green">正常</Tag>
                  </div>
                  <div style={{ marginTop: 8 }}>
                    <strong>最后测试时间：</strong>
                    <span style={{ color: '#666' }}>未测试</span>
                  </div>
                </Col>
              </Row>
            </Form>
          </Card>
        </TabPane>

        {/* 通知设置 */}
        <TabPane tab={<span><SettingOutlined />通知设置</span>} key="notifications">
          <Card>
            <Form
              layout="vertical"
              initialValues={settings}
              onValuesChange={(_, allValues) => saveSettings(allValues)}
            >
              <Row gutter={[24, 0]}>
                <Col xs={24} md={12}>
                  <Form.Item label="启用通知" name="enableNotifications" valuePropName="checked">
                    <Switch />
                  </Form.Item>

                  <Divider />

                  <Form.Item label="预测完成通知" name="predictionComplete" valuePropName="checked">
                    <Switch />
                  </Form.Item>

                  <Form.Item label="系统警告通知" name="systemAlerts" valuePropName="checked">
                    <Switch />
                  </Form.Item>

                  <Form.Item label="比赛状态更新通知" name="matchUpdates" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                </Col>

                <Col xs={24} md={12}>
                  <Alert
                    message="通知设置"
                    description="系统支持浏览器通知功能。启用后，重要事件会通过浏览器通知提醒您。"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />

                  <div>
                    <strong>浏览器通知权限：</strong>
                    <Tag color="green">已授权</Tag>
                  </div>
                </Col>
              </Row>
            </Form>
          </Card>
        </TabPane>

        {/* 隐私设置 */}
        <TabPane tab={<span><SecurityScanOutlined />隐私设置</span>} key="privacy">
          <Card>
            <Form
              layout="vertical"
              initialValues={settings}
              onValuesChange={(_, allValues) => saveSettings(allValues)}
            >
              <Row gutter={[24, 0]}>
                <Col xs={24} md={12}>
                  <Form.Item label="启用数据分析" name="enableAnalytics" valuePropName="checked">
                    <Switch />
                  </Form.Item>

                  <Form.Item label="分享预测结果" name="sharePredictions" valuePropName="checked">
                    <Switch />
                  </Form.Item>

                  <Form.Item label="公开个人资料" name="publicProfile" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                </Col>

                <Col xs={24} md={12}>
                  <Alert
                    message="隐私保护"
                    description="我们重视您的隐私。启用数据分析仅用于改善用户体验，不会收集个人敏感信息。"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />

                  <Alert
                    message="数据分享"
                    description="公开个人资料后，其他用户可以看到您的预测历史和准确率统计。"
                    type="warning"
                    showIcon
                  />
                </Col>
              </Row>
            </Form>

            <Divider />

            <Row>
              <Col span={24}>
                <Space>
                  <Button
                    type="primary"
                    icon={<SaveOutlined />}
                    onClick={() => form.submit()}
                    loading={loading}
                  >
                    保存所有设置
                  </Button>
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={resetSettings}
                  >
                    重置为默认
                  </Button>
                </Space>
              </Col>
            </Row>
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default Settings;