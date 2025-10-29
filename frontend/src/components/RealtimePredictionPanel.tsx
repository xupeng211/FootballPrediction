/**
 * 实时预测面板组件
 *
 * Realtime Prediction Panel Component
 *
 * 提供实时预测请求和结果显示功能
 * Provides real-time prediction request and result display functionality
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  InputNumber,
  Select,
  Form,
  Alert,
  Spin,
  Progress,
  Tag,
  Statistic,
  List,
  Typography,
  Space,
  Tooltip,
  Badge,
  Switch,
  Divider,
  Empty,
  message
} from 'antd';
import {
  ThunderboltOutlined,
  ReloadOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  EyeOutlined,
  BarChartOutlined,
  FireOutlined,
  RocketOutlined
} from '@ant-design/icons';
import { useWebSocket, useRealtimeEvent } from '../hooks/useWebSocket';
import { EVENT_TYPES } from '../services/websocket';

const { Text, Title } = Typography;
const { Option } = Select;

interface PredictionTask {
  task_id: string;
  match_id: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  result?: any;
  error?: string;
}

interface RealtimePredictionPanelProps {
  userId?: string;
  className?: string;
}

const RealtimePredictionPanel: React.FC<RealtimePredictionPanelProps> = ({
  userId,
  className
}) => {
  // 状态管理
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState<PredictionTask[]>([]);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showDetails, setShowDetails] = useState(false);
  const [selectedMatchId, setSelectedMatchId] = useState<number | null>(null);

  // WebSocket连接
  const ws = useWebSocket({
    userId,
    autoConnect: true
  });

  // 监听预测事件
  useRealtimeEvent(EVENT_TYPES.PREDICTION_CREATED, (event) => {
    const taskData = event.data;
    setTasks(prev => {
      // 检查是否已存在
      const existingIndex = prev.findIndex(t => t.task_id === taskData.task_id);
      if (existingIndex >= 0) {
        const updated = [...prev];
        updated[existingIndex] = taskData;
        return updated;
      }
      return [taskData, ...prev];
    });
  });

  useRealtimeEvent(EVENT_TYPES.PREDICTION_UPDATED, (event) => {
    const taskData = event.data;
    setTasks(prev => {
      const index = prev.findIndex(t => t.task_id === taskData.task_id);
      if (index >= 0) {
        const updated = [...prev];
        updated[index] = taskData;
        return updated;
      }
      return prev;
    });
  });

  useRealtimeEvent(EVENT_TYPES.PREDICTION_COMPLETED, (event) => {
    const taskData = event.data;
    setTasks(prev => {
      const index = prev.findIndex(t => t.task_id === taskData.task_id);
      if (index >= 0) {
        const updated = [...prev];
        updated[index] = {
          ...updated[index],
          ...taskData,
          status: 'completed'
        };
        return updated;
      }
      return [taskData, ...prev];
    });

    // 显示完成通知
    if (taskData.user_id === userId) {
      message.success(`预测完成！比赛ID: ${taskData.match_id}`);
    }
  });

  // 提交预测请求
  const handleSubmit = async (values: any) => {
    if (!ws.isConnected) {
      message.error('请先连接WebSocket');
      return;
    }

    setLoading(true);
    try {
      // 模拟API调用
      const response = await fetch('/api/v1/realtime/predictions/request', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          match_id: values.match_id,
          user_id: userId,
          model_version: values.model_version,
          priority: values.priority,
          include_details: true
        })
      });

      if (!response.ok) {
        throw new Error('预测请求失败');
      }

      const result = await response.json();

      // 添加到任务列表
      const newTask: PredictionTask = {
        task_id: result.task_id,
        match_id: values.match_id,
        status: 'pending',
        created_at: result.created_at
      };

      setTasks(prev => [newTask, ...prev]);

      message.success('预测请求已提交');
      form.resetFields(['match_id']);

    } catch (error) {
      console.error('提交预测请求失败:', error);
      message.error('提交预测请求失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取任务状态
  const refreshTaskStatus = async (taskId: string) => {
    try {
      const response = await fetch(`/api/v1/realtime/predictions/status/${taskId}`);
      if (response.ok) {
        const status = await response.json();
        setTasks(prev => {
          const index = prev.findIndex(t => t.task_id === taskId);
          if (index >= 0) {
            const updated = [...prev];
            updated[index] = status;
            return updated;
          }
          return prev;
        });
      }
    } catch (error) {
      console.error('刷新任务状态失败:', error);
    }
  };

  // 批量提交预测
  const handleBatchSubmit = async () => {
    if (!selectedMatchId) {
      message.warning('请先选择比赛ID');
      return;
    }

    setLoading(true);
    try {
      const matchIds = Array.from({ length: 5 }, (_, i) => selectedMatchId + i);

      const response = await fetch('/api/v1/realtime/predictions/batch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          match_ids: matchIds,
          user_id: userId,
          model_version: 'default',
          priority: false
        })
      });

      if (!response.ok) {
        throw new Error('批量预测请求失败');
      }

      const result = await response.json();
      message.success(`批量提交成功，共${result.match_count}个预测请求`);

    } catch (error) {
      console.error('批量提交失败:', error);
      message.error('批量提交失败');
    } finally {
      setLoading(false);
    }
  };

  // 清空任务列表
  const clearTasks = () => {
    setTasks([]);
  };

  // 获取状态图标和颜色
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
      case 'processing':
        return <Spin size="small" />;
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <ExclamationCircleOutlined style={{ color: '#f5222d' }} />;
      default:
        return <ClockCircleOutlined />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'warning';
      case 'processing': return 'processing';
      case 'completed': return 'success';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  // 格式化预测结果
  const formatPredictionResult = (result: any) => {
    if (!result) return null;

    return (
      <div style={{ fontSize: '12px' }}>
        <div>
          <strong>预测结果:</strong>
          <Tag color={result.predicted_outcome === 'home_win' ? 'green' :
                      result.predicted_outcome === 'draw' ? 'orange' : 'red'}>
            {result.predicted_outcome === 'home_win' ? '主胜' :
             result.predicted_outcome === 'draw' ? '平局' : '客胜'}
          </Tag>
        </div>
        <div>
          <strong>置信度:</strong> {Math.round(result.confidence * 100)}%
        </div>
        <div>
          <strong>概率分布:</strong>
          <div style={{ marginTop: '4px' }}>
            主胜: {Math.round(result.home_win_prob * 100)}% |
            平局: {Math.round(result.draw_prob * 100)}% |
            客胜: {Math.round(result.away_win_prob * 100)}%
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className={className}>
      <Row gutter={[16, 16]}>
        {/* 预测请求表单 */}
        <Col xs={24} sm={24} md={12}>
          <Card
            title={
              <Space>
                <ThunderboltOutlined />
                <span>实时预测请求</span>
                <Badge count={tasks.filter(t => t.status === 'pending' || t.status === 'processing').length} />
              </Space>
            }
            extra={
              <Space>
                <Tooltip title="自动刷新">
                  <Switch
                    size="small"
                    checked={autoRefresh}
                    onChange={setAutoRefresh}
                  />
                </Tooltip>
                <Tooltip title="显示详情">
                  <Switch
                    size="small"
                    checked={showDetails}
                    onChange={setShowDetails}
                  />
                </Tooltip>
              </Space>
            }
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSubmit}
            >
              <Form.Item
                label="比赛ID"
                name="match_id"
                rules={[{ required: true, message: '请输入比赛ID' }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="输入比赛ID"
                  min={1}
                  onChange={(value) => setSelectedMatchId(value)}
                />
              </Form.Item>

              <Form.Item
                label="模型版本"
                name="model_version"
                initialValue="default"
              >
                <Select>
                  <Option value="default">默认模型</Option>
                  <Option value="v2.1">模型 v2.1</Option>
                  <Option value="v2.0">模型 v2.0</Option>
                  <Option value="experimental">实验模型</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="priority"
                valuePropName="checked"
              >
                <Switch checkedChildren="优先处理" unCheckedChildren="普通处理" />
              </Form.Item>

              <Form.Item>
                <Space style={{ width: '100%' }} direction="vertical">
                  <Button
                    type="primary"
                    htmlType="submit"
                    icon={<RocketOutlined />}
                    loading={loading}
                    disabled={!ws.isConnected}
                    block
                  >
                    提交预测请求
                  </Button>

                  <Button
                    icon={<FireOutlined />}
                    onClick={handleBatchSubmit}
                    loading={loading}
                    disabled={!ws.isConnected || !selectedMatchId}
                    block
                  >
                    批量预测 (5个)
                  </Button>
                </Space>
              </Form.Item>
            </Form>

            <Divider />

            {/* 统计信息 */}
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="总任务数"
                  value={tasks.length}
                  prefix={<BarChartOutlined />}
                  valueStyle={{ fontSize: '16px' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="已完成"
                  value={tasks.filter(t => t.status === 'completed').length}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ fontSize: '16px', color: '#52c41a' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="失败"
                  value={tasks.filter(t => t.status === 'failed').length}
                  prefix={<ExclamationCircleOutlined />}
                  valueStyle={{ fontSize: '16px', color: '#f5222d' }}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        {/* 任务列表 */}
        <Col xs={24} sm={24} md={12}>
          <Card
            title={
              <Space>
                <EyeOutlined />
                <span>预测任务列表</span>
                {tasks.length > 0 && (
                  <Button
                    size="small"
                    type="text"
                    icon={<ReloadOutlined />}
                    onClick={() => tasks.forEach(t => refreshTaskStatus(t.task_id))}
                    disabled={!ws.isConnected}
                  />
                )}
              </Space>
            }
            extra={
              tasks.length > 0 && (
                <Button
                  size="small"
                  type="text"
                  onClick={clearTasks}
                  disabled={loading}
                >
                  清空
                </Button>
              )
            }
            bodyStyle={{ maxHeight: 500, overflow: 'auto' }}
          >
            {tasks.length > 0 ? (
              <List
                size="small"
                dataSource={tasks}
                renderItem={(task) => (
                  <List.Item style={{ padding: '8px 0' }}>
                    <div style={{ width: '100%' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Space>
                          {getStatusIcon(task.status)}
                          <Text strong>比赛 #{task.match_id}</Text>
                          <Tag color={getStatusColor(task.status)}>
                            {task.status}
                          </Tag>
                        </Space>
                        <Text type="secondary" style={{ fontSize: '11px' }}>
                          {new Date(task.created_at).toLocaleTimeString()}
                        </Text>
                      </div>

                      {/* 进度条 */}
                      {task.status === 'processing' && (
                        <Progress
                          percent={50}
                          showInfo={false}
                          size="small"
                          style={{ margin: '4px 0' }}
                        />
                      )}

                      {/* 预测结果 */}
                      {task.status === 'completed' && task.result && (
                        <div style={{ marginTop: '8px' }}>
                          {formatPredictionResult(task.result)}
                        </div>
                      )}

                      {/* 错误信息 */}
                      {task.status === 'failed' && task.error && (
                        <Alert
                          message={task.error}
                          type="error"
                          style={{ marginTop: '8px' }}
                        />
                      )}

                      {/* 详细信息 */}
                      {showDetails && (
                        <div style={{ marginTop: '8px', fontSize: '11px', color: '#666' }}>
                          <div>任务ID: {task.task_id}</div>
                          {task.started_at && (
                            <div>开始时间: {new Date(task.started_at).toLocaleTimeString()}</div>
                          )}
                          {task.completed_at && (
                            <div>完成时间: {new Date(task.completed_at).toLocaleTimeString()}</div>
                          )}
                        </div>
                      )}
                    </div>
                  </List.Item>
                )}
              />
            ) : (
              <Empty
                description={ws.isConnected ? "暂无预测任务" : "请先连接WebSocket"}
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default RealtimePredictionPanel;