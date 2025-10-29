/**
 * 质量趋势图表组件
 * Quality Trends Chart Component
 */

import React, { useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { Empty, Card, Space, Tag, Tooltip } from 'antd';
import {
  TrendingUpOutlined,
  TrendingDownOutlined,
  MinusOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';

// 注册Chart.js组件
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const QualityTrendsChart = ({ trends }) => {
  // 处理趋势数据
  const chartData = useMemo(() => {
    if (!trends || !trends.trend || trends.trend.length === 0) {
      return null;
    }

    const trendData = trends.trend.slice(-50); // 只显示最近50个数据点

    // 格式化时间标签
    const labels = trendData.map(item => {
      try {
        const date = new Date(item.timestamp);
        return format(date, 'MM/dd HH:mm', { locale: zhCN });
      } catch (error) {
        return 'Unknown';
      }
    });

    // 质量分数数据
    const scoreData = trendData.map(item => item.score || 0);

    // 状态映射为数值
    const statusToValue = {
      'PASSED': 3,
      'WARNING': 2,
      'FAILED': 1,
      'UNKNOWN': 0
    };

    const statusData = trendData.map(item => statusToValue[item.status] || 0);

    return {
      labels,
      datasets: [
        {
          label: '质量分数',
          data: scoreData,
          borderColor: 'rgb(75, 192, 192)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          tension: 0.4,
          fill: true,
          pointRadius: 3,
          pointHoverRadius: 6,
          pointBackgroundColor: 'rgb(75, 192, 192)',
          pointBorderColor: '#fff',
          pointBorderWidth: 2
        },
        {
          label: '状态等级',
          data: statusData,
          borderColor: 'rgb(255, 99, 132)',
          backgroundColor: 'rgba(255, 99, 132, 0.1)',
          tension: 0.4,
          fill: false,
          pointRadius: 2,
          pointHoverRadius: 5,
          pointBackgroundColor: 'rgb(255, 99, 132)',
          pointBorderColor: '#fff',
          pointBorderWidth: 1,
          borderDash: [5, 5] // 虚线
        }
      ]
    };
  }, [trends]);

  // 计算趋势统计
  const trendStats = useMemo(() => {
    if (!chartData || !chartData.datasets[0].data.length) {
      return null;
    }

    const scores = chartData.datasets[0].data;
    const latestScore = scores[scores.length - 1];
    const previousScore = scores[scores.length - 2] || latestScore;

    // 计算平均分
    const averageScore = scores.reduce((sum, score) => sum + score, 0) / scores.length;

    // 计算最高分和最低分
    const maxScore = Math.max(...scores);
    const minScore = Math.min(...scores);

    // 趋势方向
    let trendDirection = 'stable';
    let trendIcon = <MinusOutlined />;
    let trendColor = '#faad14';

    if (latestScore > previousScore + 0.1) {
      trendDirection = 'up';
      trendIcon = <TrendingUpOutlined />;
      trendColor = '#52c41a';
    } else if (latestScore < previousScore - 0.1) {
      trendDirection = 'down';
      trendIcon = <TrendingDownOutlined />;
      trendColor = '#ff4d4f';
    }

    return {
      latestScore,
      previousScore,
      averageScore,
      maxScore,
      minScore,
      trendDirection,
      trendIcon,
      trendColor,
      dataPoints: scores.length
    };
  }, [chartData]);

  // Chart.js配置选项
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          usePointStyle: true,
          padding: 15,
          font: {
            size: 11
          }
        }
      },
      title: {
        display: false
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: '#fff',
        bodyColor: '#fff',
        borderColor: '#ddd',
        borderWidth: 1,
        cornerRadius: 6,
        displayColors: true,
        callbacks: {
          title: function(context) {
            const index = context[0].dataIndex;
            const label = context[0].label;
            const dataPoint = trends?.trend?.[trends.trend.length - (trends.trend.length > 50 ? 50 : trends.trend.length) + index];
            const status = dataPoint?.status || 'UNKNOWN';
            return `${label} - ${status}`;
          },
          label: function(context) {
            const label = context.dataset.label || '';
            const value = context.parsed.y;

            if (context.datasetIndex === 0) {
              return `${label}: ${value.toFixed(2)}/10`;
            } else {
              const statusNames = ['未知', '失败', '警告', '通过'];
              const statusValue = Math.round(value);
              return `${label}: ${statusNames[statusValue] || '未知'}`;
            }
          }
        }
      }
    },
    scales: {
      x: {
        display: true,
        grid: {
          display: false
        },
        ticks: {
          maxTicksLimit: 10,
          font: {
            size: 10
          },
          autoSkip: true,
          maxRotation: 45,
          minRotation: 45
        }
      },
      y: {
        display: true,
        position: 'left',
        min: 0,
        max: 10,
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        },
        ticks: {
          stepSize: 2,
          font: {
            size: 10
          },
          callback: function(value) {
            return value.toFixed(1);
          }
        },
        title: {
          display: true,
          text: '质量分数',
          font: {
            size: 11
          }
        }
      },
      y1: {
        display: false, // 隐藏右侧Y轴
        position: 'right',
        min: 0,
        max: 3,
        grid: {
          drawOnChartArea: false
        },
        ticks: {
          stepSize: 1,
          callback: function(value) {
            const statusNames = ['失败', '警告', '通过'];
            return statusNames[value] || '';
          }
        }
      }
    },
    elements: {
      point: {
        hoverBackgroundColor: '#fff',
        hoverBorderWidth: 2
      }
    }
  };

  if (!chartData) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无趋势数据"
        />
      </div>
    );
  }

  return (
    <div>
      {/* 趋势统计信息 */}
      {trendStats && (
        <div style={{ marginBottom: '16px' }}>
          <Space wrap>
            <Tooltip title={`当前分数: ${trendStats.latestScore.toFixed(2)}`}>
              <Tag color="blue">
                当前: {trendStats.latestScore.toFixed(1)}
              </Tag>
            </Tooltip>
            <Tooltip title={`平均分数: ${trendStats.averageScore.toFixed(2)}`}>
              <Tag color="green">
                平均: {trendStats.averageScore.toFixed(1)}
              </Tag>
            </Tooltip>
            <Tooltip title={`最高分数: ${trendStats.maxScore.toFixed(2)}`}>
              <Tag color="cyan">
                最高: {trendStats.maxScore.toFixed(1)}
              </Tag>
            </Tooltip>
            <Tooltip title={`最低分数: ${trendStats.minScore.toFixed(2)}`}>
              <Tag color="orange">
                最低: {trendStats.minScore.toFixed(1)}
              </Tag>
            </Tooltip>
            <Tooltip title={`数据点: ${trendStats.dataPoints}个`}>
              <Tag color="default">
                <InfoCircleOutlined /> {trendStats.dataPoints}个点
              </Tag>
            </Tooltip>
            <Tooltip title={`趋势: ${trendStats.trendDirection}`}>
              <Tag color={trendStats.trendColor}>
                {trendStats.trendIcon} {
                  trendStats.trendDirection === 'up' ? '上升' :
                  trendStats.trendDirection === 'down' ? '下降' : '稳定'
                }
              </Tag>
            </Tooltip>
          </Space>
        </div>
      )}

      {/* 图表容器 */}
      <div style={{ height: '300px', position: 'relative' }}>
        <Line data={chartData} options={options} />
      </div>

      {/* 图表说明 */}
      <div style={{ marginTop: '16px', fontSize: '11px', color: '#666' }}>
        <div style={{ marginBottom: '4px' }}>
          <strong>说明:</strong>
        </div>
        <div style={{ marginBottom: '2px' }}>
          • 蓝色实线: 质量分数趋势 (0-10分)
        </div>
        <div style={{ marginBottom: '2px' }}>
          • 红色虚线: 状态等级 (失败=1, 警告=2, 通过=3)
        </div>
        <div>
          • 数据更新: 每5分钟自动刷新
        </div>
      </div>
    </div>
  );
};

export default QualityTrendsChart;