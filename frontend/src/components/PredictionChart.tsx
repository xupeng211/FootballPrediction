import React from 'react';
import ReactECharts from 'echarts-for-react';
import { PredictionResponse } from '../services/api';

interface PredictionChartProps {
  prediction: PredictionResponse;
  width?: string | number;
  height?: string | number;
}

const PredictionChart: React.FC<PredictionChartProps> = ({
  prediction,
  width = '100%',
  height = 300,
}) => {
  // 获取预测结果的颜色
  const getPredictionColor = (prediction: string) => {
    switch (prediction) {
      case 'home_win':
        return '#52c41a'; // 绿色
      case 'draw':
        return '#faad14'; // 黄色
      case 'away_win':
        return '#ff4d4f'; // 红色
      default:
        return '#1890ff'; // 蓝色
    }
  };

  // 获取置信度等级
  const getConfidenceLevel = (confidence: number) => {
    if (confidence >= 0.8) return { text: '高', color: '#52c41a' };
    if (confidence >= 0.6) return { text: '中', color: '#faad14' };
    return { text: '低', color: '#ff4d4f' };
  };

  // 图表配置
  const getOption = () => {
    const confidenceLevel = getConfidenceLevel(prediction.confidence);
    const predictionColor = getPredictionColor(prediction.prediction);

    return {
      title: {
        text: '比赛预测结果',
        left: 'center',
        textStyle: {
          fontSize: 18,
          fontWeight: 'bold',
        },
      },
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c}% ({d}%)',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#ccc',
        borderWidth: 1,
        textStyle: {
          color: '#333',
        },
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        top: 'middle',
        data: ['主胜', '平局', '客胜'],
      },
      series: [
        {
          name: '预测概率',
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['60%', '50%'],
          avoidLabelOverlap: false,
          label: {
            show: true,
            position: 'outside',
            formatter: '{b}\n{c}%',
            fontSize: 14,
            fontWeight: 'bold',
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 16,
              fontWeight: 'bold',
            },
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)',
            },
          },
          labelLine: {
            show: true,
            length: 10,
            length2: 20,
          },
          data: [
            {
              value: Math.round(prediction.home_win_prob * 100),
              name: '主胜',
              itemStyle: {
                color: prediction.prediction === 'home_win' ? predictionColor : '#91cc75',
                borderColor: '#fff',
                borderWidth: 2,
              },
            },
            {
              value: Math.round(prediction.draw_prob * 100),
              name: '平局',
              itemStyle: {
                color: prediction.prediction === 'draw' ? predictionColor : '#fac858',
                borderColor: '#fff',
                borderWidth: 2,
              },
            },
            {
              value: Math.round(prediction.away_win_prob * 100),
              name: '客胜',
              itemStyle: {
                color: prediction.prediction === 'away_win' ? predictionColor : '#ee6666',
                borderColor: '#fff',
                borderWidth: 2,
              },
            },
          ],
        },
      ],
      graphic: [
        // 添加推荐箭头指向预测结果
        {
          type: 'group',
          left: '60%',
          top: '50%',
          children: [
            {
              type: 'text',
              left: 0,
              top: -30,
              style: {
                text: '推荐',
                fontSize: 14,
                fontWeight: 'bold',
                fill: predictionColor,
              },
            },
            {
              type: 'text',
              left: -15,
              top: -10,
              style: {
                text: '▼',
                fontSize: 20,
                fill: predictionColor,
              },
            },
          ],
        },
        // 添加置信度信息
        {
          type: 'text',
          left: '60%',
          top: '85%',
          style: {
            text: `置信度: ${Math.round(prediction.confidence * 100)}% (${confidenceLevel.text})`,
            fontSize: 14,
            fill: confidenceLevel.color,
            fontWeight: 'bold',
          },
        },
      ],
    };
  };

  return (
    <div className="prediction-chart">
      <ReactECharts
        option={getOption()}
        style={{ width, height }}
        notMerge={true}
        lazyUpdate={true}
      />
    </div>
  );
};

export default PredictionChart;