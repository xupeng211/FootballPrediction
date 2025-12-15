# 🎨 Frontend Development Guide

## 技术栈概览

### 核心技术
- **React**: 19.2.0 - 现代化UI框架
- **TypeScript**: 4.9.5 - 类型安全的JavaScript
- **Ant Design**: 5.27.6 - 企业级UI组件库
- **Redux Toolkit**: 状态管理
- **ECharts**: 5.4.3 - 数据可视化

### 开发工具
- **Vite**: 快速构建工具
- **Jest**: 单元测试框架
- **React Testing Library**: React组件测试
- **ESLint**: 代码质量检查
- **Prettier**: 代码格式化

## 🚀 快速开始

### 环境准备
```bash
# 确保Node.js版本 >= 16
node --version

# 安装依赖
cd frontend
npm install

# 启动开发服务器
npm start
```

### 开发服务器
- **地址**: http://localhost:3000
- **热重载**: ✅ 自动支持
- **代理配置**: API请求自动代理到后端(8000端口)

## 📁 项目结构

```
frontend/
├── public/              # 静态资源
│   ├── index.html      # HTML模板
│   └── favicon.ico     # 网站图标
├── src/                # 源代码
│   ├── components/     # 可复用组件
│   ├── pages/          # 页面组件
│   ├── store/          # Redux状态管理
│   ├── services/       # API服务
│   ├── utils/          # 工具函数
│   ├── types/          # TypeScript类型定义
│   ├── hooks/          # 自定义Hooks
│   └── styles/         # 样式文件
├── package.json        # 项目配置
└── Dockerfile          # Docker构建配置
```

## 🛠️ 开发工作流

### 1. 组件开发
```typescript
// src/components/ExampleComponent.tsx
import React from 'react';
import { Button, Card } from 'antd';

interface ExampleComponentProps {
  title: string;
  onButtonClick: () => void;
}

const ExampleComponent: React.FC<ExampleComponentProps> = ({
  title,
  onButtonClick
}) => {
  return (
    <Card title={title}>
      <Button type="primary" onClick={onButtonClick}>
        点击我
      </Button>
    </Card>
  );
};

export default ExampleComponent;
```

### 2. 状态管理 (Redux Toolkit)
```typescript
// src/store/features/exampleSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface ExampleState {
  data: any[];
  loading: boolean;
  error: string | null;
}

const initialState: ExampleState = {
  data: [],
  loading: false,
  error: null,
};

const exampleSlice = createSlice({
  name: 'example',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    setData: (state, action: PayloadAction<any[]>) => {
      state.data = action.payload;
      state.loading = false;
      state.error = null;
    },
    setError: (state, action: PayloadAction<string>) => {
      state.error = action.payload;
      state.loading = false;
    },
  },
});

export const { setLoading, setData, setError } = exampleSlice.actions;
export default exampleSlice.reducer;
```

### 3. API服务
```typescript
// src/services/exampleService.ts
import { api } from './api';

export interface ExampleData {
  id: number;
  name: string;
  value: number;
}

export const exampleService = {
  // 获取所有数据
  getAll: async (): Promise<ExampleData[]> => {
    const response = await api.get('/examples');
    return response.data;
  },

  // 获取单个数据
  getById: async (id: number): Promise<ExampleData> => {
    const response = await api.get(`/examples/${id}`);
    return response.data;
  },

  // 创建数据
  create: async (data: Omit<ExampleData, 'id'>): Promise<ExampleData> => {
    const response = await api.post('/examples', data);
    return response.data;
  },

  // 更新数据
  update: async (id: number, data: Partial<ExampleData>): Promise<ExampleData> => {
    const response = await api.put(`/examples/${id}`, data);
    return response.data;
  },

  // 删除数据
  delete: async (id: number): Promise<void> => {
    await api.delete(`/examples/${id}`);
  },
};
```

## 🧪 测试

### 单元测试
```typescript
// src/components/__tests__/ExampleComponent.test.tsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ExampleComponent from '../ExampleComponent';

describe('ExampleComponent', () => {
  const mockOnButtonClick = jest.fn();

  beforeEach(() => {
    mockOnButtonClick.mockClear();
  });

  it('renders title correctly', () => {
    render(
      <ExampleComponent
        title="测试标题"
        onButtonClick={mockOnButtonClick}
      />
    );

    expect(screen.getByText('测试标题')).toBeInTheDocument();
  });

  it('calls onButtonClick when button is clicked', () => {
    render(
      <ExampleComponent
        title="测试标题"
        onButtonClick={mockOnButtonClick}
      />
    );

    const button = screen.getByText('点击我');
    fireEvent.click(button);

    expect(mockOnButtonClick).toHaveBeenCalledTimes(1);
  });
});
```

### 运行测试
```bash
# 运行所有测试
npm test

# 监听模式运行测试
npm test -- --watch

# 生成覆盖率报告
npm test -- --coverage
```

## 🔧 代码规范

### ESLint配置
```json
{
  "extends": [
    "react-app",
    "react-app/jest",
    "@typescript-eslint/recommended"
  ],
  "rules": {
    "@typescript-eslint/no-unused-vars": "error",
    "react-hooks/exhaustive-deps": "warn",
    "prefer-const": "error"
  }
}
```

### Prettier配置
```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 80,
  "tabWidth": 2
}
```

## 📦 构建部署

### 开发构建
```bash
# 开发模式构建
npm run build

# 构建产物预览
npm install -g serve
serve -s build
```

### Docker构建
```bash
# 构建前端Docker镜像
docker build -t football-prediction-frontend ./frontend

# 使用轻量级配置构建全栈应用
docker-compose -f docker-compose.lightweight.yml up frontend
```

### 生产部署
```bash
# 生产环境构建
npm run build

# 构建分析
npm run build -- --analyze
```

## 🔗 与后端集成

### API配置
```typescript
// src/services/api.ts
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 添加认证token
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // 统一错误处理
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

## 🎨 UI组件使用

### Ant Design组件
```typescript
import { Table, Button, Space, Tag } from 'antd';

const ExampleTable: React.FC = () => {
  const columns = [
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'active' ? 'green' : 'red'}>
          {status}
        </Tag>
      ),
    },
  ];

  const data = [
    { key: '1', name: '张三', status: 'active' },
    { key: '2', name: '李四', status: 'inactive' },
  ];

  return (
    <Table
      columns={columns}
      dataSource={data}
      title={() => '用户列表'}
    />
  );
};
```

## 📊 ECharts数据可视化

### 图表示例
```typescript
import React from 'react';
import ReactECharts from 'echarts-for-react';

const ExampleChart: React.FC = () => {
  const option = {
    title: {
      text: '预测准确率趋势',
    },
    xAxis: {
      type: 'category',
      data: ['1月', '2月', '3月', '4月', '5月', '6月'],
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
    },
    series: [
      {
        name: '准确率',
        type: 'line',
        data: [65, 72, 78, 82, 85, 89],
        smooth: true,
        itemStyle: {
          color: '#1890ff',
        },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: '400px' }} />;
};
```

## 🚨 常见问题

### 1. 开发环境跨域问题
在`package.json`中配置代理：
```json
{
  "proxy": "http://localhost:8000"
}
```

### 2. TypeScript类型错误
确保安装了所有必要的类型定义：
```bash
npm install --save-dev @types/react @types/react-dom @types/node
```

### 3. 构建内存不足
增加Node.js内存限制：
```bash
export NODE_OPTIONS="--max-old-space-size=4096"
npm run build
```

## 📝 最佳实践

1. **组件设计**: 遵循单一职责原则，保持组件纯净
2. **状态管理**: 合理使用Redux Toolkit，避免过度状态提升
3. **类型安全**: 充分利用TypeScript，为所有数据和函数定义类型
4. **代码复用**: 提取公共组件和工具函数
5. **性能优化**: 使用React.memo、useMemo、useCallback优化渲染性能
6. **错误处理**: 实现统一的错误边界和错误处理机制
7. **测试覆盖**: 为核心组件和业务逻辑编写单元测试

## 🔗 相关链接

- [React官方文档](https://react.dev/)
- [TypeScript官方文档](https://www.typescriptlang.org/)
- [Ant Design组件库](https://ant.design/)
- [Redux Toolkit文档](https://redux-toolkit.js.org/)
- [ECharts图表库](https://echarts.apache.org/)