/**
 * 前端冒烟测试脚本
 * 验证前端核心功能的连通性和完整性
 */

const fs = require('fs');
const path = require('path');

console.log('🔥 开始前端冒烟测试...\n');

const results = {
  coreFiles: [],
  dependencies: [],
  structure: [],
  components: [],
  views: [],
  api: [],
  types: []
};

let totalTests = 0;
let passedTests = 0;

// 测试核心文件是否存在
const testCoreFile = (filePath, description) => {
  totalTests++;
  const exists = fs.existsSync(filePath);
  results.coreFiles.push({
    file: filePath,
    description,
    status: exists ? '✅' : '❌'
  });
  if (exists) passedTests++;
  return exists;
};

// 测试 package.json 依赖
const testDependencies = () => {
  try {
    const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
    const requiredDeps = [
      'vue',
      'vue-router',
      'pinia',
      'axios',
      'tailwindcss',
      'typescript',
      'vite'
    ];

    const requiredDevDeps = [
      '@vitejs/plugin-vue',
      'vue-tsc',
      'eslint',
      'autoprefixer',
      'postcss'
    ];

    totalTests += requiredDeps.length + requiredDevDeps.length;

    requiredDeps.forEach(dep => {
      const exists = packageJson.dependencies && packageJson.dependencies[dep];
      results.dependencies.push({
        type: 'dependencies',
        dep,
        status: exists ? '✅' : '❌'
      });
      if (exists) passedTests++;
    });

    requiredDevDeps.forEach(dep => {
      const exists = packageJson.devDependencies && packageJson.devDependencies[dep];
      results.dependencies.push({
        type: 'devDependencies',
        dep,
        status: exists ? '✅' : '❌'
      });
      if (exists) passedTests++;
    });

  } catch (error) {
    console.log('❌ 无法读取 package.json');
    results.dependencies.push({
      type: 'error',
      error: 'package.json read failed'
    });
  }
};

// 测试目录结构
const testDirectoryStructure = () => {
  const requiredDirs = [
    'src',
    'src/api',
    'src/components',
    'src/components/auth',
    'src/components/charts',
    'src/components/match',
    'src/components/profile',
    'src/layouts',
    'src/router',
    'src/stores',
    'src/types',
    'src/views',
    'src/views/auth',
    'src/views/match'
  ];

  requiredDirs.forEach(dir => {
    totalTests++;
    const exists = fs.existsSync(dir);
    results.structure.push({
      type: 'directory',
      path: dir,
      status: exists ? '✅' : '❌'
    });
    if (exists) passedTests++;
  });
};

// 测试核心组件文件
const testComponents = () => {
  const requiredComponents = [
    'src/layouts/MainLayout.vue',
    'src/layouts/AuthLayout.vue',
    'src/components/charts/ProbabilityChart.vue',
    'src/components/charts/StatsRadar.vue',
    'src/components/match/MatchHeader.vue',
    'src/components/profile/HistoryTable.vue',
    'src/components/profile/StatsSummary.vue'
  ];

  requiredComponents.forEach(component => {
    totalTests++;
    const exists = fs.existsSync(component);
    results.components.push({
      component,
      status: exists ? '✅' : '❌'
    });
    if (exists) passedTests++;
  });
};

// 测试视图文件
const testViews = () => {
  const requiredViews = [
    'src/views/auth/Login.vue',
    'src/views/auth/Register.vue',
    'src/views/Dashboard.vue',
    'src/views/Profile.vue',
    'src/views/match/MatchDetails.vue'
  ];

  requiredViews.forEach(view => {
    totalTests++;
    const exists = fs.existsSync(view);
    results.views.push({
      view,
      status: exists ? '✅' : '❌'
    });
    if (exists) passedTests++;
  });
};

// 测试 API 和类型文件
const testApiAndTypes = () => {
  const requiredFiles = [
    'src/api/client.ts',
    'src/types/auth.ts',
    'src/types/prediction.ts',
    'src/router/index.ts',
    'src/stores/auth.ts',
    'src/main.ts',
    'src/App.vue'
  ];

  requiredFiles.forEach(file => {
    totalTests++;
    const exists = fs.existsSync(file);
    results.api.push({
      file,
      status: exists ? '✅' : '❌'
    });
    if (exists) passedTests++;
  });
};

// 测试关键文件内容
const testFileContents = () => {
  const criticalChecks = [
    {
      file: 'src/main.ts',
      patterns: ['createApp', 'mount', '#app']
    },
    {
      file: 'src/router/index.ts',
      patterns: ['createRouter', 'routes', 'MainLayout']
    },
    {
      file: 'src/stores/auth.ts',
      patterns: ['defineStore', 'login', 'logout']
    },
    {
      file: 'src/api/client.ts',
      patterns: ['ApiClient', 'login', 'getUserProfile']
    },
    {
      file: 'package.json',
      patterns: ['name', 'version', 'scripts']
    }
  ];

  criticalChecks.forEach(({ file, patterns }) => {
    if (fs.existsSync(file)) {
      try {
        const content = fs.readFileSync(file, 'utf8');
        patterns.forEach(pattern => {
          totalTests++;
          const found = content.includes(pattern);
          if (!found) {
            console.log(`❌ ${file} 缺少关键内容: ${pattern}`);
          } else {
            passedTests++;
          }
        });
      } catch (error) {
        console.log(`❌ 无法读取 ${file}`);
      }
    }
  });
};

// 执行所有测试
console.log('📁 测试核心文件存在性\n');
testCoreFile('package.json', 'Package.json');
testCoreFile('vite.config.ts', 'Vite 配置');
testCoreFile('tailwind.config.js', 'Tailwind 配置');
testCoreFile('tsconfig.json', 'TypeScript 配置');
testCoreFile('index.html', '入口 HTML');

console.log('📦 测试依赖完整性\n');
testDependencies();

console.log('📂 测试目录结构\n');
testDirectoryStructure();

console.log('🧩 测试核心组件\n');
testComponents();

console.log('👁️ 测试视图文件\n');
testViews();

console.log('⚙️ 测试 API 和类型文件\n');
testApiAndTypes();

console.log('🔍 测试关键文件内容\n');
testFileContents();

// 输出测试结果
console.log('\n🎯 冒烟测试结果摘要\n');
console.log(`总测试数: ${totalTests}`);
console.log(`通过测试数: ${passedTests}`);
console.log(`通过率: ${((passedTests / totalTests) * 100).toFixed(1)}%\n`);

if (passedTests === totalTests) {
  console.log('🎉 所有冒烟测试通过！前端应用准备就绪。\n');
} else {
  console.log('❌ 部分冒烟测试失败，请检查上述问题。\n');
}

// 详细结果报告
console.log('📊 详细测试结果:\n');

console.log('🔧 核心文件状态:');
results.coreFiles.forEach(item => {
  console.log(`  ${item.status} ${item.description} (${item.file})`);
});

console.log('\n📦 依赖状态:');
results.dependencies.forEach(item => {
  if (item.type === 'error') {
    console.log(`  ❌ ${item.error}`);
  } else {
    console.log(`  ${item.status} ${item.type}: ${item.dep}`);
  }
});

console.log('\n📂 目录结构:');
results.structure.forEach(item => {
  console.log(`  ${item.status} ${item.path}`);
});

console.log('\n🧩 组件文件:');
results.components.forEach(item => {
  console.log(`  ${item.status} ${item.component}`);
});

console.log('\n👁️ 视图文件:');
results.views.forEach(item => {
  console.log(`  ${item.status} ${item.view}`);
});

console.log('\n⚙️ API 和类型文件:');
results.api.forEach(item => {
  console.log(`  ${item.status} ${item.file}`);
});

console.log('\n🚀 启动建议:');
console.log('1. 确保依赖已安装: npm install');
console.log('2. 启动开发服务器: npm run dev');
console.log('3. 访问应用: http://localhost:5173');
console.log('4. 测试完整流程: 登录 -> 仪表板 -> 用户中心');

console.log('\n🏁 冒烟测试完成！');