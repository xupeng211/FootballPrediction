import React, { useState, useEffect } from 'react';
import { Card, Select, Space, Spin } from 'antd';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';

const { Option } = Select;

interface TrendDataPoint {
  timestamp: string;
  overall_score: number;
  coverage_percentage: number;
  code_quality_score: number;
  security_score: number;
}

const QualityTrendChart: React.FC = () => {
  const [trendData, setTrendData] = useState<TrendDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState(24); // 小时

  useEffect(() => {
    fetchTrendData();
  }, [timeRange]);

  const fetchTrendData = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/quality/trends?hours=${timeRange}`);
      const data = await response.json();

      // 模拟趋势数据（实际应该从API获取）
      const mockData: TrendDataPoint[] = generateMockTrendData(timeRange);
      setTrendData(mockData);
    } catch (error) {
      console.error('获取趋势数据失败:', error);
      // 使用模拟数据
      const mockData: TrendDataPoint[] = generateMockTrendData(timeRange);
      setTrendData(mockData);
    } finally {
      setLoading(false);
    }
  };

  const generateMockTrendData = (hours: number): TrendDataPoint[] => {
    const data: TrendDataPoint[] = [];
    const now = dayjs();

    for (let i = hours; i >= 0; i -= 2) { // 每2小时一个数据点
      const timestamp = now.subtract(i, 'hour').toISOString();
      const baseScore = 9.5 + Math.random() * 0.4;
      const baseCoverage = 80 + Math.random() * 10;
      const baseCodeQuality = 9.5 + Math.random() * 0.5;
      const baseSecurity = 9.8 + Math.random() * 0.2;

      data.push({
        timestamp,
        overall_score: Math.min(10, Math.max(8, baseScore + (Math.random() - 0.5) * 0.3)),
        coverage_percentage: Math.min(95, Math.max(70, baseCoverage + (Math.random() - 0.5) * 5)),
        code_quality_score: Math.min(10, Math.max(8, baseCodeQuality + (Math.random() - 0.5) * 0.4)),
        security_score: Math.min(10, Math.max(9, baseSecurity + (Math.random() - 0.5) * 0.2))
      });
    }

    return data;
  };

  const getChartOption = () => {
    const timestamps = trendData.map(d => dayjs(d.timestamp).format('HH:mm'));

    return {
      title: {
        text: '质量趋势分析',
        left: 'center',
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold'
        }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        },
        formatter: (params: any[]) => {
          let html = `<div style="font-weight: bold;">${params[0].axisValue}</div>`;
          params.forEach((param: any) => {
            const value = typeof param.value === 'number' ? param.value.toFixed(2) : param.value;
            html += `<div style="color: ${param.color};">
              ${param.seriesName}: ${value}${param.seriesName.includes('率') ? '%' : ''}
            </div>`;
          });
          return html;
        }
      },
      legend: {
        data: ['综合分数', '代码质量', '安全评分', '测试覆盖率'],
        top: 30
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: timestamps,
        axisLabel: {
          rotate: 45
        }
      },
      yAxis: {
        type: 'value',
        min: 7,
        max: 10,
        axisLabel: {
          formatter: '{value}'
        }
      },
      series: [
        {
          name: '综合分数',
          type: 'line',
          data: trendData.map(d => d.overall_score),
          smooth: true,
          lineStyle: {
            width: 3,
            color: '#1890ff'
          },
          itemStyle: {
            color: '#1890ff'
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
                { offset: 1, color: 'rgba(24, 144, 255, 0.05)' }
              ]
            }
          }
        },
        {
          name: '代码质量',
          type: 'line',
          data: trendData.map(d => d.code_quality_score),
          smooth: true,
          lineStyle: {
            width: 2,
            color: '#52c41a'
          },
          itemStyle: {
            color: '#52c41a'
          }
        },
        {
          name: '安全评分',
          type: 'line',
          data: trendData.map(d => d.security_score),
          smooth: true,
          lineStyle: {
            width: 2,
            color: '#faad14'
          },
          itemStyle: {
            color: '#faad14'
          }
        },
        {
          name: '测试覆盖率',
          type: 'line',
          data: trendData.map(d => d.coverage_percentage / 10), // 缩放到0-10范围
          smooth: true,
          lineStyle: {
            width: 2,
            color: '#722ed1'
          },
          itemStyle: {
            color: '#722ed1'
          }
        }
      ]
    };
  };

  return (
    <Card
      title={
        <Space>
          <span>质量趋势</span>
          <Select
            value={timeRange}
            onChange={setTimeRange}
            style={{ width: 120 }}
            size="small"
          >
            <Option value={6}>6小时</Option>
            <Option value={12}>12小时</Option>
            <Option value={24}>24小时</Option>
            <Option value={72}>3天</Option>
            <Option value={168}>7天</Option>
          </Select>
        </Space>
      }
      className="trend-chart-card"
      extra={
        <span style={{ fontSize: '12px', color: '#999' }}>
          每2小时更新
        </span>
      }
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Spin size="large" />
        </div>
      ) : (
        <ReactECharts
          option={getChartOption()}
          style={{ height: '300px' }}
          notMerge={true}
          lazyUpdate={true}
        />
      )}
    </Card>
  );
};

export default QualityTrendChart;
