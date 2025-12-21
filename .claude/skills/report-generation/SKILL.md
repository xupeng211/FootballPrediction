---
name: report-generation
description: Generate professional football analysis reports in PDF, Word, and Excel formats. Use when creating match analysis reports, data visualizations, or exporting prediction results. Includes professional charts and statistical analysis.
---

# Report Generation Skill

## 技能概述
专业的足球分析报告生成系统，支持多种格式的报告输出，包括PDF、Word、Excel等，为不同用户提供定制化的分析报告。

## 核心能力
- **赛前分析报告**: 详细的比赛前瞻和预测分析
- **赛后总结**: 深度的比赛结果分析和复盘
- **数据可视化**: 专业的图表和统计分析
- **批量报告生成**: 支持多场比赛同时生成报告
- **模板化输出**: 统一的品牌形象和专业格式

## 报告类型

### 1. 赛前分析报告 (Pre-Match Report)
**用途**: 媒体、投资机构、球队战术分析
**格式**: PDF (8-10页)
**包含内容**:
- 执行摘要 (1页)
- 比赛概况 (1页)
- 深度数据分析 (2-3页)
- 预测模型分析 (1页)
- 风险评估 (1页)
- 投资建议 (1页)

### 2. Excel数据分析表
**用途**: 数据分析师、量化交易、研究团队
**格式**: XLSX (多工作表)
**包含工作表**:
- 原始预测数据
- 概率分布表
- 历史准确率统计
- 收益率分析
- 图表数据源

### 3. 可视化仪表板数据
**用途**: 实时监控、决策支持、展示演示
**格式**: JSON + HTML
**数据结构**:
- 实时预测流
- 性能指标
- 趋势分析
- 对比图表

## 技术实现

### 核心依赖
```python
# PDF生成
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4

# Word文档
from docx import Document
from docx.shared import Inches

# Excel处理
import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.chart import BarChart, Reference

# 图表可视化
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
```

### 报告生成流程
```python
def generate_pre_match_report(home_team: str, away_team: str) -> str:
    # 1. 获取预测数据
    prediction = get_match_prediction(home_team, away_team)

    # 2. 收集分析数据
    analysis_data = collect_analysis_data(home_team, away_team)

    # 3. 生成可视化图表
    charts = generate_charts(analysis_data)

    # 4. 渲染PDF报告
    report_path = render_pdf_report(prediction, analysis_data, charts)

    return report_path
```

## 模板系统

### PDF模板结构
```
templates/
├── pre_match_report.html     # Jinja2模板
├── styles.css               # 样式定义
├── header_footer.html       # 页眉页脚
└── charts/                  # 图表模板
    ├── radar_chart.html
    ├── probability_chart.html
    └── trend_analysis.html
```

### Excel模板配置
```python
EXCEL_TEMPLATE = {
    'pre_match_analysis': {
        'worksheets': [
            {'name': '预测结果', 'columns': ['日期', '主队', '客队', '预测', '概率']},
            {'name': '历史数据', 'columns': ['交锋记录', '胜负统计']},
            {'name': '图表数据', 'chart_type': 'bar_chart'}
        ]
    }
}
```

## 可视化组件

### 1. 实力雷达图
```python
def create_strength_radar(home_stats, away_stats):
    """五维实力对比雷达图"""
    categories = ['进攻', '防守', '中场', '体能', '战术']

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=home_stats,
        theta=categories,
        fill='toself',
        name=home_team
    ))

    fig.add_trace(go.Scatterpolar(
        r=away_stats,
        theta=categories,
        fill='toself',
        name=away_team
    ))

    return fig
```

### 2. 概率分布图
```python
def create_probability_chart(probabilities):
    """胜负概率分布柱状图"""
    labels = ['主胜', '平局', '客胜']
    values = [probabilities['home'], probabilities['draw'], probabilities['away']]

    colors = ['#2E8B57', '#FFD700', '#DC143C']

    fig = go.Figure(data=[
        go.Bar(x=labels, y=values, marker_color=colors)
    ])

    fig.update_layout(
        title='比赛结果概率分布',
        yaxis_title='概率 (%)'
    )

    return fig
```

### 3. 趋势分析图
```python
def create_trend_chart(team_name, matches_history):
    """球队近期表现趋势"""
    dates = [match['date'] for match in matches_history]
    results = [match['result'] for match in matches_history]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates,
        y=results,
        mode='lines+markers',
        name=team_name,
        line=dict(color='blue', width=2)
    ))

    return fig
```

## 报告使用示例

### 生成单场比赛报告
```bash
# 使用CLI工具
python scripts/generate_report.py \
    --home "Manchester United" \
    --away "Arsenal" \
    --type pre_match \
    --format pdf \
    --output reports/manu_vs_arsenal.pdf
```

### 批量生成周报
```bash
python scripts/batch_reports.py \
    --week "2024-W03" \
    --league "Premier League" \
    --format_all \
    --output_dir weekly_reports/
```

### API集成
```python
import requests

# 请求报告生成
response = requests.post('/api/v2/reports', json={
    'home_team': 'Manchester United',
    'away_team': 'Arsenal',
    'report_type': 'pre_match',
    'format': 'pdf'
})

report_url = response.json()['report_url']
```

## 质量标准

### 报告格式规范
- **PDF**: A4纸张，专业排版，品牌标识
- **Excel**: 标准化表头，数据验证，条件格式
- **图表**: 统一配色，清晰标注，响应式设计

### 内容质量要求
- **数据准确性**: 100%数据源验证
- **分析深度**: 至少3个维度的分析
- **可视化**: 每个报告至少3个专业图表
- **语言规范**: 专业术语，表达准确

## 性能优化

### 生成速度优化
- **模板缓存**: Jinja2模板预编译
- **图表缓存**: 相同数据图表复用
- **异步处理**: 大批量报告异步生成
- **并行渲染**: 多进程图表生成

### 存储优化
- **压缩存储**: PDF文件压缩
- **CDN分发**: 报告文件CDN加速
- **缓存策略**: Redis缓存热点报告
- **清理机制**: 定期清理过期报告

## 扩展功能

### 多语言支持
- 中文报告模板
- 英文报告模板
- 动态语言切换

### 自定义品牌
- Logo水印
- 品牌色彩
- 自定义页眉页脚

### 交互式报告
- 可点击图表
- 数据筛选
- 导出功能

## 最佳实践

### 报告设计原则
1. **信息层次**: 重要信息突出显示
2. **视觉一致**: 统一的设计语言
3. **数据准确**: 多重验证机制
4. **用户友好**: 清晰的导航和说明

### 使用建议
1. **定期更新**: 模板和样式定期优化
2. **用户反馈**: 收集使用反馈持续改进
3. **性能监控**: 报告生成时间和成功率
4. **版本控制**: 报告模板版本管理

## 技术栈
- **PDF生成**: ReportLab, WeasyPrint
- **Word处理**: python-docx
- **Excel处理**: openpyxl, pandas
- **图表库**: matplotlib, plotly, seaborn
- **模板引擎**: Jinja2
- **任务队列**: Celery + Redis
- **文件存储**: AWS S3 / 本地文件系统