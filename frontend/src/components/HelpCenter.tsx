import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Collapse,
  Alert,
  Typography,
  Button,
  Space,
  Tag,
  Divider,
  List,
  Avatar,
} from 'antd';
import {
  BookOutlined,
  PhoneOutlined,
  MailOutlined,
  MessageOutlined,
  VideoCameraOutlined,
  FileTextOutlined,
  ApiOutlined,
  TrophyOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;
const { Panel } = Collapse;

const HelpCenter: React.FC = () => {
  const [activeKey, setActiveKey] = useState<string | string[]>(['1']);

  const handlePanelChange = (key: string | string[]) => {
    setActiveKey(key);
  };

  const faqData = [
    {
      key: '1',
      question: '如何查看比赛预测？',
      answer: '在"比赛预测"页面，您可以浏览所有即将开始和正在进行的比赛。点击比赛左侧的展开按钮可以查看详细的预测结果，包括胜平负概率、置信度和投注建议。',
      category: '基础功能',
    },
    {
      key: '2',
      question: '预测的准确率如何？',
      answer: '我们的预测模型基于历史数据和机器学习算法，整体准确率约为65-75%。置信度高于80%的预测通常更加可靠。请注意，任何预测都不能保证100%准确，请理性参考。',
      category: '预测说明',
    },
    {
      key: '3',
      question: '什么是期望收益(EV)？',
      answer: '期望收益(Expected Value)是评估投注价值的重要指标。计算公式为：EV = (预测概率 × 赔率) - 1。当EV > 0时，表示该投注具有正期望值，可能带来长期收益。',
      category: '投注相关',
    },
    {
      key: '4',
      question: '如何设置置信度阈值？',
      answer: '在"系统设置"页面的"预测设置"中，您可以调整置信度阈值。建议设置在60-75%之间，这样可以帮助过滤掉不太可靠的预测结果。',
      category: '设置相关',
    },
    {
      key: '5',
      question: '数据更新频率是怎样的？',
      answer: '比赛数据和预测结果通常每15-30分钟更新一次。您可以在设置中调整自动刷新间隔，也可以手动点击刷新按钮获取最新数据。',
      category: '数据相关',
    },
    {
      key: '6',
      question: '系统支持哪些联赛？',
      answer: '目前系统支持英超、西甲、德甲、意甲、法甲、欧冠等主要联赛。我们正在逐步扩展支持更多的联赛和赛事。',
      category: '数据相关',
    },
  ];

  const tutorialData = [
    {
      title: '新手入门指南',
      description: '了解系统基本功能和操作流程',
      icon: <BookOutlined />,
      tags: ['基础', '入门'],
      estimatedTime: '5分钟',
    },
    {
      title: '预测结果解读',
      description: '学习如何理解和分析预测结果',
      icon: <TrophyOutlined />,
      tags: ['预测', '分析'],
      estimatedTime: '8分钟',
    },
    {
      title: '投注策略入门',
      description: '了解基本的投注概念和策略',
      icon: <FileTextOutlined />,
      tags: ['投注', '策略'],
      estimatedTime: '10分钟',
    },
    {
      title: 'API使用说明',
      description: '开发者API接口使用指南',
      icon: <ApiOutlined />,
      tags: ['API', '开发'],
      estimatedTime: '15分钟',
    },
  ];

  const contactData = [
    {
      type: '技术支持',
      description: '系统使用问题和故障排除',
      contact: 'support@football-prediction.com',
      icon: <PhoneOutlined />,
      responseTime: '24小时内',
    },
    {
      type: '商务合作',
      description: '商业合作和赞助事宜',
      contact: 'business@football-prediction.com',
      icon: <MailOutlined />,
      responseTime: '48小时内',
    },
    {
      type: '用户反馈',
      description: '功能建议和意见反馈',
      contact: 'feedback@football-prediction.com',
      icon: <MessageOutlined />,
      responseTime: '72小时内',
    },
  ];

  const quickActions = [
    {
      title: '观看视频教程',
      description: '通过视频快速了解系统功能',
      icon: <VideoCameraOutlined />,
      action: '观看教程',
      color: '#1890ff',
    },
    {
      title: '下载用户手册',
      description: '获取详细的PDF版用户手册',
      icon: <FileTextOutlined />,
      action: '下载手册',
      color: '#52c41a',
    },
    {
      title: '在线客服咨询',
      description: '与客服人员实时交流',
      icon: <MessageOutlined />,
      action: '开始咨询',
      color: '#faad14',
    },
  ];

  return (
    <div>
      {/* 欢迎信息 */}
      <Alert
        message="欢迎使用足球预测系统帮助中心"
        description="这里是您解决疑问和获取帮助的中心。如果您找不到需要的信息，请联系我们的客服团队。"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      {/* 快速操作 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {quickActions.map((action, index) => (
          <Col xs={24} sm={8} key={index}>
            <Card
              hoverable
              style={{ textAlign: 'center' }}
              bodyStyle={{ padding: '20px' }}
            >
              <div style={{ fontSize: 32, color: action.color, marginBottom: 16 }}>
                {action.icon}
              </div>
              <Title level={5}>{action.title}</Title>
              <Paragraph type="secondary" style={{ marginBottom: 16 }}>
                {action.description}
              </Paragraph>
              <Button type="primary" ghost>
                {action.action}
              </Button>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[24, 24]}>
        {/* 常见问题 */}
        <Col xs={24} lg={16}>
          <Card title="常见问题" style={{ marginBottom: 24 }}>
            <Collapse
              activeKey={activeKey}
              onChange={handlePanelChange}
              ghost
            >
              {faqData.map((faq) => (
                <Panel
                  header={
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span>{faq.question}</span>
                      <Tag color="blue" style={{ fontSize: '12px' }}>
                        {faq.category}
                      </Tag>
                    </div>
                  }
                  key={faq.key}
                >
                  <Paragraph>{faq.answer}</Paragraph>
                </Panel>
              ))}
            </Collapse>
          </Card>

          {/* 教程资源 */}
          <Card title="教程资源">
            <List
              grid={{ gutter: 16, xs: 1, sm: 2, md: 2, lg: 2, xl: 2, xxl: 3 }}
              dataSource={tutorialData}
              renderItem={(item) => (
                <List.Item>
                  <Card
                    hoverable
                    size="small"
                    bodyStyle={{ padding: '16px' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start' }}>
                      <div style={{ fontSize: 24, color: '#1890ff', marginRight: 12, marginTop: 4 }}>
                        {item.icon}
                      </div>
                      <div style={{ flex: 1 }}>
                        <Title level={5} style={{ marginBottom: 8 }}>
                          {item.title}
                        </Title>
                        <Paragraph type="secondary" style={{ fontSize: '12px', marginBottom: 8 }}>
                          {item.description}
                        </Paragraph>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Space size={4}>
                            {item.tags.map((tag, index) => (
                              <Tag key={index} color="blue" style={{ fontSize: '10px' }}>
                                {tag}
                              </Tag>
                            ))}
                          </Space>
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            {item.estimatedTime}
                          </Text>
                        </div>
                      </div>
                    </div>
                  </Card>
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* 联系信息 */}
        <Col xs={24} lg={8}>
          <Card title="联系我们" style={{ marginBottom: 24 }}>
            <List
              dataSource={contactData}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={
                      <Avatar
                        icon={item.icon}
                        style={{ backgroundColor: '#1890ff' }}
                      />
                    }
                    title={
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>{item.type}</span>
                        <Tag color="green" style={{ fontSize: '10px' }}>
                          {item.responseTime}
                        </Tag>
                      </div>
                    }
                    description={
                      <div>
                        <div style={{ marginBottom: 8 }}>{item.description}</div>
                        <Text code>{item.contact}</Text>
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>

          {/* 系统状态 */}
          <Card title="系统状态">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>预测服务</span>
                <Tag color="green">正常</Tag>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>数据更新</span>
                <Tag color="green">正常</Tag>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>API响应</span>
                <Tag color="green">{'< 200ms'}</Tag>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>系统可用性</span>
                <Tag color="green">99.9%</Tag>
              </div>
            </Space>

            <Divider />

            <Alert
              message="系统维护通知"
              description="系统将于每周日凌晨2:00-4:00进行例行维护，期间可能影响服务使用。"
              type="info"
              showIcon
              style={{ marginTop: 16 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 安全提示 */}
      <Card
        title={
          <span>
            <SafetyCertificateOutlined style={{ marginRight: 8 }} />
            安全提示
          </span>
        }
        style={{ marginTop: 24 }}
      >
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Alert
              message="理性预测"
              description="足球预测仅供参考，不构成投资建议。请理性对待预测结果，控制风险。"
              type="warning"
              showIcon
            />
          </Col>
          <Col xs={24} md={8}>
            <Alert
              message="保护隐私"
              description="不要在公共设备上保存个人信息，定期修改密码，确保账户安全。"
              type="warning"
              showIcon
            />
          </Col>
          <Col xs={24} md={8}>
            <Alert
              message="合法使用"
              description="请遵守当地法律法规，仅将本系统用于合法的娱乐和分析目的。"
              type="warning"
              showIcon
            />
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default HelpCenter;