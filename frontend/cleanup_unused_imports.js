// 前端代码清理脚本 - 精确清理未使用的导入
const fs = require('fs');

// 需要清理的文件列表和对应的未使用导入
const filesToClean = [
  {
    file: 'src/components/Analytics.tsx',
    unusedImports: ['Space', 'LineChartOutlined']
  },
  {
    file: 'src/components/BettingRecommendation.tsx',
    unusedImports: ['Progress', 'Switch', 'CalculatorOutlined', 'LineChartOutlined']
  },
  {
    file: 'src/components/Dashboard.tsx',
    unusedImports: ['Space', 'RiseOutlined']
  },
  {
    file: 'src/components/Settings.tsx',
    unusedImports: ['Space']
  },
  {
    file: 'src/components/HelpCenter.tsx',
    unusedImports: ['Space']
  },
  {
    file: 'src/components/PerformanceOptimizer.tsx',
    unusedImports: ['Space']
  },
  {
    file: 'src/components/ResponsiveLayout.tsx',
    unusedImports: ['Space']
  }
];

function cleanFile(filePath, unusedImports) {
  if (!fs.existsSync(filePath)) {
    console.log(`文件不存在: ${filePath}`);
    return false;
  }

  let content = fs.readFileSync(filePath, 'utf8');
  let modified = false;
  let originalContent = content;

  unusedImports.forEach(importName => {
    // 精确匹配导入声明
    const importRegex = new RegExp(`,?\\s*${importName},?\\s*\\n`, 'g');
    const usageRegex = new RegExp(`<${importName}`, 'g');

    if (importRegex.test(content) && !usageRegex.test(content)) {
      content = content.replace(importRegex, '\n');
      console.log(`从 ${filePath} 中移除了未使用的导入: ${importName}`);
      modified = true;
    }
  });

  // 清理导入语句末尾的多余逗号
  content = content.replace(/,(\s*\n\s*}\s*from)/g, '$1');

  // 清理连续的空行
  content = content.replace(/\n\s*\n\s*\n/g, '\n\n');

  if (modified && content !== originalContent) {
    fs.writeFileSync(filePath, content);
    return true;
  }
  return false;
}

console.log('🧹 开始精确清理前端代码中未使用的导入...\n');

let cleanedCount = 0;
filesToClean.forEach(({file, unusedImports}) => {
  if (cleanFile(file, unusedImports)) {
    cleanedCount++;
  }
});

console.log(`\n✅ 清理完成！共处理了 ${cleanedCount} 个文件。`);
