/**
 * 用户订阅管理组件
 *
 * User Subscription Management Component
 *
 * 提供实时事件订阅管理功能
 * Provides real-time event subscription management functionality
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Form,
  Input,
  Select,
  Switch,
  Checkbox,
  Divider,
  Alert,
  List,
  Tag,
  Space,
  Tooltip,
  Badge,
  Typography,
  Empty,
  message,
  Modal,
  InputNumber,
  Slider
} from 'antd';
import {
  BellOutlined,
  SettingOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
  FilterOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { useWebSocket } from '../hooks/useWebSocket';
import { EVENT_TYPES } from '../services/websocket';

const { Text, Title } = Typography;
const { Option } = Select;
const { Group } = Checkbox;

interface SubscriptionRule {
  id: string;
  name: string;
  eventTypes: string[];
  filters: {
    match_ids?: number[];
    leagues?: string[];
    min_confidence?: number;
    max_matches?: number;
  };
  isActive: boolean;
  createdAt: string;
  lastUsed?: string;
}

interface SubscriptionManagerProps {
  userId?: string;
  className?: string;
}

const SubscriptionManager: React.FC<SubscriptionManagerProps> = ({
  userId,
  className
}) => {
  // 状态管理
  const [form] = Form.useForm();
  const [subscriptions, setSubscriptions] = useState<SubscriptionRule[]>([]);
  const [editingRule, setEditingRule] = useState<SubscriptionRule | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  // WebSocket连接
  const ws = useWebSocket({
    userId,
    autoConnect: true
  });

  // 预设的订阅规则模板
  const presetRules = [
    {
      name: "所有预测事件",
      eventTypes: [EVENT_TYPES.PREDICTION_CREATED, EVENT_TYPES.PREDICTION_COMPLETED],
      filters: {},
      description: "接收所有预测相关的实时通知"
    },
    {
      name: "英超比赛监控",
      eventTypes: [EVENT_TYPES.MATCH_STARTED, EVENT_TYPES.MATCH_SCORE_CHANGED, EVENT_TYPES.MATCH_ENDED],
      filters: { leagues: ["英超"] },
      description: "监控英超联赛的所有比赛状态变化"
    },
    {
      name: "高置信度预测",
      eventTypes: [EVENT_TYPES.PREDICTION_COMPLETED],
      filters: { min_confidence: 80 },
      description: "只接收置信度80%以上的预测结果"
    },
    {
      name: "系统告警",
      eventTypes: [EVENT_TYPES.SYSTEM_ALERT],
      filters: {},
      description: "接收系统级别的所有告警信息"
    }
  ];

  // 监听订阅变化事件
  useEffect(() => {
    if (ws.isConnected && ws.service) {
      // 加载当前订阅
      loadCurrentSubscriptions();
    }
  }, [ws.isConnected]);

  const loadCurrentSubscriptions = async () => {
    try {
      // 模拟从服务器加载订阅规则
      const mockSubscriptions: SubscriptionRule[] = [
        {
          id: "1",
          name: "所有预测事件",
          eventTypes: [EVENT_TYPES.PREDICTION_CREATED, EVENT_TYPES.PREDICTION_COMPLETED],
          filters: {},
          isActive: true,
          createdAt: new Date().toISOString(),
          lastUsed: new Date().toISOString()
        },
        {
          id: "2",
          name: "英超比赛监控",
          eventTypes: [EVENT_TYPES.MATCH_STARTED, EVENT_TYPES.MATCH_SCORE_CHANGED],
          filters: { leagues: ["英超"], max_matches: 10 },
          isActive: true,
          createdAt: new Date(Date.now() - 3600000).toISOString(),
          lastUsed: new Date(Date.now() - 1800000).toISOString()
        }
      ];

      setSubscriptions(mockSubscriptions);
    } catch (error) {
      console.error('加载订阅规则失败:', error);
      message.error('加载订阅规则失败');
    }
  };

  const handleCreateRule = async (values: any) => {
    setLoading(true);
    try {
      const newRule: SubscriptionRule = {
        id: Date.now().toString(),
        name: values.name,
        eventTypes: values.eventTypes,
        filters: {
          match_ids: values.match_ids?.length > 0 ? values.match_ids : undefined,
          leagues: values.leagues?.length > 0 ? values.leagues : undefined,
          min_confidence: values.min_confidence,
          max_matches: values.max_matches
        },
        isActive: values.isActive,
        createdAt: new Date().toISOString()
      };

      setSubscriptions(prev => [...prev, newRule]);

      // 应用订阅
      await applySubscription(newRule);

      message.success('订阅规则创建成功');
      setShowCreateModal(false);
      form.resetFields();
    } catch (error) {
      console.error('创建订阅规则失败:', error);
      message.error('创建订阅规则失败');
    } finally {
      setLoading(false);
    }
  };

  const handleEditRule = async (values: any) => {
    if (!editingRule) return;

    setLoading(true);
    try {
      const updatedRule: SubscriptionRule = {
        ...editingRule,
        name: values.name,
        eventTypes: values.eventTypes,
        filters: {
          match_ids: values.match_ids?.length > 0 ? values.match_ids : undefined,
          leagues: values.leagues?.length > 0 ? values.leagues : undefined,
          min_confidence: values.min_confidence,
          max_matches: values.max_matches
        },
        isActive: values.isActive,
        lastUsed: new Date().toISOString()
      };

      setSubscriptions(prev =>
        prev.map(rule => rule.id === editingRule.id ? updatedRule : rule)
      );

      // 重新应用订阅
      await applySubscription(updatedRule);

      message.success('订阅规则更新成功');
      setShowEditModal(false);
      setEditingRule(null);
      form.resetFields();
    } catch (error) {
      console.error('更新订阅规则失败:', error);
      message.error('更新订阅规则失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    try {
      setSubscriptions(prev => prev.filter(rule => rule.id !== ruleId));

      // 取消订阅
      if (ws.service) {
        const rule = subscriptions.find(r => r.id === ruleId);
        if (rule && rule.isActive) {
          ws.service.unsubscribe(rule.eventTypes);
        }
      }

      message.success('订阅规则删除成功');
    } catch (error) {
      console.error('删除订阅规则失败:', error);
      message.error('删除订阅规则失败');
    }
  };

  const handleToggleRule = async (ruleId: string) => {
    try {
      const rule = subscriptions.find(r => r.id === ruleId);
      if (!rule) return;

      const updatedRule = { ...rule, isActive: !rule.isActive };
      setSubscriptions(prev =>
        prev.map(r => r.id === ruleId ? updatedRule : r)
      );

      if (updatedRule.isActive) {
        await applySubscription(updatedRule);
      } else {
        if (ws.service) {
          ws.service.unsubscribe(updatedRule.eventTypes);
        }
      }

      message.success(updatedRule.isActive ? '订阅已启用' : '订阅已禁用');
    } catch (error) {
      console.error('切换订阅状态失败:', error);
      message.error('切换订阅状态失败');
    }
  };

  const applySubscription = async (rule: SubscriptionRule) => {
    if (!ws.service) return;

    // 构建过滤器
    const filters: Record<string, any> = {};
    if (rule.filters.match_ids) {
      filters.match_ids = rule.filters.match_ids;
    }
    if (rule.filters.leagues) {
      filters.leagues = rule.filters.leagues;
    }
    if (rule.filters.min_confidence) {
      filters.min_confidence = rule.filters.min_confidence / 100;
    }

    // 应用订阅
    ws.service.subscribe(rule.eventTypes, filters);
  };

  const handleUsePreset = (preset: any) => {
    form.setFieldsValue({
      name: preset.name,
      eventTypes: preset.eventTypes,
      ...preset.filters
    });
  };

  const openEditModal = (rule: SubscriptionRule) => {
    setEditingRule(rule);
    form.setFieldsValue({
      name: rule.name,
      eventTypes: rule.eventTypes,
      match_ids: rule.filters.match_ids,
      leagues: rule.filters.leagues,
      min_confidence: rule.filters.min_confidence,
      max_matches: rule.filters.max_matches,
      isActive: rule.isActive
    });
    setShowEditModal(true);
  };

  const getEventTypeColor = (eventType: string) => {
    const colorMap: Record<string, string> = {
      [EVENT_TYPES.PREDICTION_CREATED]: 'purple',
      [EVENT_TYPES.PREDICTION_COMPLETED]: 'purple',
      [EVENT_TYPES.MATCH_STARTED]: 'orange',
      [EVENT_TYPES.MATCH_SCORE_CHANGED]: 'orange',
      [EVENT_TYPES.MATCH_ENDED]: 'orange',
      [EVENT_TYPES.ODDS_UPDATED]: 'cyan',
      [EVENT_TYPES.SYSTEM_ALERT]: 'red',
      [EVENT_TYPES.USER_SUBSCRIPTION_CHANGED]: 'blue'
    };
    return colorMap[eventType] || 'default';
  };

  const formatFilters = (filters: any) => {
    const parts: string[] = [];

    if (filters.match_ids?.length) {
      parts.push(`比赛: ${filters.match_ids.length}个`);
    }
    if (filters.leagues?.length) {
      parts.push(`联赛: ${filters.leagues.join(', ')}`);
    }
    if (filters.min_confidence) {
      parts.push(`最小置信度: ${filters.min_confidence}%`);
    }
    if (filters.max_matches) {
      parts.push(`最大比赛数: ${filters.max_matches}`);
    }

    return parts.length > 0 ? parts.join(' | ') : '无过滤条件';
  };

  return (
    <div className={className}>
      <Row gutter={[16, 16]}>
        {/* 订阅规则管理 */}
        <Col xs={24} sm={24} md={16}>
          <Card
            title={
              <Space>
                <BellOutlined />
                <span>订阅规则管理</span>
                <Badge count={subscriptions.filter(r => r.isActive).length} />
              </Space>
            }
            extra={
              <Space>
                <Tooltip title="显示详情">
                  <Switch
                    size="small"
                    checked={showDetails}
                    onChange={setShowDetails}
                    checkedChildren="详情"
                    unCheckedChildren="简洁"
                  />
                </Tooltip>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setShowCreateModal(true)}
                  disabled={!ws.isConnected}
                >
                  创建规则
                </Button>
              </Space>
            }
          >
            {subscriptions.length > 0 ? (
              <List
                dataSource={subscriptions}
                renderItem={(rule) => (
                  <List.Item
                    actions={[
                      <Tooltip title="编辑">
                        <Button
                          type="text"
                          icon={<EditOutlined />}
                          onClick={() => openEditModal(rule)}
                        />
                      </Tooltip>,
                      <Tooltip title="删除">
                        <Button
                          type="text"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => handleDeleteRule(rule.id)}
                        />
                      </Tooltip>,
                      <Tooltip title={rule.isActive ? "禁用" : "启用"}>
                        <Switch
                          size="small"
                          checked={rule.isActive}
                          onChange={() => handleToggleRule(rule.id)}
                        />
                      </Tooltip>
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          <Text strong>{rule.name}</Text>
                          <Badge
                            status={rule.isActive ? "success" : "default"}
                            text={rule.isActive ? "活跃" : "禁用"}
                          />
                        </Space>
                      }
                      description={
                        <div>
                          <Space wrap>
                            {rule.eventTypes.map(eventType => (
                              <Tag
                                key={eventType}
                                color={getEventTypeColor(eventType)}
                              >
                                {eventType.replace('_', ' ')}
                              </Tag>
                            ))}
                          </Space>
                          {showDetails && (
                            <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
                              <div><strong>过滤条件:</strong> {formatFilters(rule.filters)}</div>
                              <div><strong>创建时间:</strong> {new Date(rule.createdAt).toLocaleString()}</div>
                              {rule.lastUsed && (
                                <div><strong>最后使用:</strong> {new Date(rule.lastUsed).toLocaleString()}</div>
                              )}
                            </div>
                          )}
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty
                description="暂无订阅规则"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              >
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setShowCreateModal(true)}
                  disabled={!ws.isConnected}
                >
                  创建第一个规则
                </Button>
              </Empty>
            )}
          </Card>
        </Col>

        {/* 预设模板和统计 */}
        <Col xs={24} sm={24} md={8}>
          <Card
            title={
              <Space>
                <SettingOutlined />
                <span>快速模板</span>
              </Space>
            }
            size="small"
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              {presetRules.map((preset, index) => (
                <Button
                  key={index}
                  block
                  icon={<PlusOutlined />}
                  onClick={() => {
                    setShowCreateModal(true);
                    setTimeout(() => handleUsePreset(preset), 100);
                  }}
                  disabled={!ws.isConnected}
                >
                  {preset.name}
                </Button>
              ))}
            </Space>
          </Card>

          <Card
            title="订阅统计"
            size="small"
            style={{ marginTop: 16 }}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text type="secondary">总规则数:</Text>
                <Text strong>{subscriptions.length}</Text>
              </div>
              <div>
                <Text type="secondary">活跃规则:</Text>
                <Text strong style={{ color: '#52c41a' }}>
                  {subscriptions.filter(r => r.isActive).length}
                </Text>
              </div>
              <div>
                <Text type="secondary">连接状态:</Text>
                <Text strong style={{ color: ws.isConnected ? '#52c41a' : '#f5222d' }}>
                  {ws.isConnected ? '已连接' : '未连接'}
                </Text>
              </div>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 创建订阅规则模态框 */}
      <Modal
        title="创建订阅规则"
        open={showCreateModal}
        onCancel={() => {
          setShowCreateModal(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateRule}
        >
          <Form.Item
            label="规则名称"
            name="name"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="输入订阅规则名称" />
          </Form.Item>

          <Form.Item
            label="事件类型"
            name="eventTypes"
            rules={[{ required: true, message: '请选择至少一个事件类型' }]}
          >
            <Select
              mode="multiple"
              placeholder="选择要订阅的事件类型"
              style={{ width: '100%' }}
            >
              <Option value={EVENT_TYPES.PREDICTION_CREATED}>预测创建</Option>
              <Option value={EVENT_TYPES.PREDICTION_COMPLETED}>预测完成</Option>
              <Option value={EVENT_TYPES.MATCH_STARTED}>比赛开始</Option>
              <Option value={EVENT_TYPES.MATCH_SCORE_CHANGED}>比分变化</Option>
              <Option value={EVENT_TYPES.MATCH_ENDED}>比赛结束</Option>
              <Option value={EVENT_TYPES.ODDS_UPDATED}>赔率更新</Option>
              <Option value={EVENT_TYPES.SYSTEM_ALERT}>系统告警</Option>
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="比赛ID" name="match_ids">
                <Select
                  mode="tags"
                  placeholder="输入比赛ID，按回车添加"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="联赛" name="leagues">
                <Select
                  mode="multiple"
                  placeholder="选择联赛"
                  style={{ width: '100%' }}
                >
                  <Option value="英超">英超</Option>
                  <Option value="西甲">西甲</Option>
                  <Option value="德甲">德甲</Option>
                  <Option value="意甲">意甲</Option>
                  <Option value="法甲">法甲</Option>
                  <Option value="欧冠">欧冠</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="最小置信度"
            name="min_confidence"
          >
            <Slider
              min={0}
              max={100}
              marks={{
                0: '0%',
                50: '50%',
                70: '70%',
                85: '85%',
                100: '100%'
              }}
              tooltip={{ formatter: (value) => `${value}%` }}
            />
          </Form.Item>

          <Form.Item
            label="最大比赛数"
            name="max_matches"
          >
            <InputNumber
              min={1}
              max={100}
              placeholder="限制最大比赛数量"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item
            name="isActive"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setShowCreateModal(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={loading}>
                创建
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑订阅规则模态框 */}
      <Modal
        title="编辑订阅规则"
        open={showEditModal}
        onCancel={() => {
          setShowEditModal(false);
          setEditingRule(null);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleEditRule}
        >
          <Form.Item
            label="规则名称"
            name="name"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="输入订阅规则名称" />
          </Form.Item>

          <Form.Item
            label="事件类型"
            name="eventTypes"
            rules={[{ required: true, message: '请选择至少一个事件类型' }]}
          >
            <Select
              mode="multiple"
              placeholder="选择要订阅的事件类型"
              style={{ width: '100%' }}
            >
              <Option value={EVENT_TYPES.PREDICTION_CREATED}>预测创建</Option>
              <Option value={EVENT_TYPES.PREDICTION_COMPLETED}>预测完成</Option>
              <Option value={EVENT_TYPES.MATCH_STARTED}>比赛开始</Option>
              <Option value={EVENT_TYPES.MATCH_SCORE_CHANGED}>比分变化</Option>
              <Option value={EVENT_TYPES.MATCH_ENDED}>比赛结束</Option>
              <Option value={EVENT_TYPES.ODDS_UPDATED}>赔率更新</Option>
              <Option value={EVENT_TYPES.SYSTEM_ALERT}>系统告警</Option>
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="比赛ID" name="match_ids">
                <Select
                  mode="tags"
                  placeholder="输入比赛ID，按回车添加"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="联赛" name="leagues">
                <Select
                  mode="multiple"
                  placeholder="选择联赛"
                  style={{ width: '100%' }}
                >
                  <Option value="英超">英超</Option>
                  <Option value="西甲">西甲</Option>
                  <Option value="德甲">德甲</Option>
                  <Option value="意甲">意甲</Option>
                  <Option value="法甲">法甲</Option>
                  <Option value="欧冠">欧冠</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="最小置信度"
            name="min_confidence"
          >
            <Slider
              min={0}
              max={100}
              marks={{
                0: '0%',
                50: '50%',
                70: '70%',
                85: '85%',
                100: '100%'
              }}
              tooltip={{ formatter: (value) => `${value}%` }}
            />
          </Form.Item>

          <Form.Item
            label="最大比赛数"
            name="max_matches"
          >
            <InputNumber
              min={1}
              max={100}
              placeholder="限制最大比赛数量"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item
            name="isActive"
            valuePropName="checked"
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setShowEditModal(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={loading}>
                保存
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SubscriptionManager;