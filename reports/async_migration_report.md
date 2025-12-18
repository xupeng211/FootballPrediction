# 异步化迁移报告

生成时间: 2025-12-06 15:13:12

## 📊 迁移统计

- 🔴 高优先级问题: 3385
- 🟡 中等优先级问题: 6974
- 🟢 低优先级问题: 0
- 📋 总问题数: 10359

## 📁 文件详情

### src/main_simple.py
问题数量: 4

🔴 **第20行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第30行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/app_enhanced.py
问题数量: 14

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第85行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第91行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第92行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第97行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第108行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第130行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第131行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/app_legacy.py
问题数量: 4

🔴 **第20行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第30行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/main.py
问题数量: 27

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第76行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第87行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第201行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第332行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第333行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第342行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第344行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第356行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第357行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第366行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第368行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第385行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第386行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第391行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第392行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第416行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第429行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第443行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第496行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第518行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第534行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第572行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第616行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第658行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第756行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第757行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/bad_example.py
问题数量: 2

🟡 **第15行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/inference/feature_builder.py
问题数量: 29

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第98行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第118行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第126行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第131行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第132行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第139行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第227行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第261行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第288行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第299行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第309行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第332行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第351行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第363行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第382行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第393行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第411行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第424行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第471行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第491行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第502行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第520行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第532行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第551行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/inference/schemas.py
问题数量: 2

🟡 **第110行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第147行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/inference/hot_reload.py
问题数量: 31

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第127行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第159行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第176行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第251行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第267行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第294行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第309行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第320行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第331行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第336行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第347行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第353行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第372行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第393行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第413行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第424行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第428行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第433行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第445行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第455行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第462行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第470行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第492行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第496行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第521行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第539行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/inference/__init__.py
问题数量: 1

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/inference/predictor.py
问题数量: 24

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第189行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第263行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第269行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第319行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第324行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第332行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第419行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第465行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第474行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第497行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第512行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第539行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第559行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第574行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第584行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第600行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第609行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第626行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第655行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第670行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/inference/errors.py
问题数量: 14

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第75行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第89行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第103行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第117行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第130行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第131行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第142行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/inference/cache.py
问题数量: 25

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第118行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第145行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第194行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第226行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第247行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第257行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第288行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第310行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第327行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第349行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第367行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第368行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第369行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第370行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第371行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第388行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第411行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第424行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第428行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第441行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第460行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/inference/loader.py
问题数量: 30

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第131行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第165行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第187行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第189行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第191行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第196行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第208行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第237行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第260行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第276行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第284行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第347行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第360行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第375行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第390行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第401行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/adapters/registry_simple.py
问题数量: 11

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第47行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第61行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/adapters/base.py
问题数量: 12

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第83行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/adapters/factory_simple.py
问题数量: 5

🟡 **第27行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/adapters/factory.py
问题数量: 10

🟡 **第83行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第99行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/adapters/registry.py
问题数量: 8

🟡 **第16行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第60行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/adapters/football.py
问题数量: 16

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第74行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第133行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第144行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第177行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第185行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第194行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第206行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第216行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/adapters/adapters/football_models.py
问题数量: 3

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/config/cors_config.py
问题数量: 2

🟡 **第12行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/config/fastapi_config.py
问题数量: 4

🟡 **第11行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第15行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/config/openapi_config.py
问题数量: 6

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第142行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第148行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第155行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/config/security_config.py
问题数量: 10

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第123行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第143行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第149行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第154行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第159行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/config/config_manager.py
问题数量: 18

🟡 **第16行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第36行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第49行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第54行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第59行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第64行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第69行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第78行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/config/swagger_ui_config.py
问题数量: 12

🟡 **第19行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第488行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第491行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第515行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第516行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第519行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第520行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第529行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第659行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第662行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第663行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第669行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/docs.py
问题数量: 11

🔴 **第22行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第52行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第535行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第536行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第902行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第903行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第927行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第928行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第950行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/data_management.py
问题数量: 12

🔴 **第28行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第85行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第115行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第250行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第251行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第276行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第277行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/auth_dependencies.py
问题数量: 5

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/system.py
问题数量: 10

🔴 **第24行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第46行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第68行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第90行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第112行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/tenant_management.py
问题数量: 41

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第202行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第206行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第211行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第235行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第237行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第242行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第256行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第261行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第273行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第275行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第282行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第288行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第290行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第297行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第303行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第305行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第310行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第319行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第321行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第331行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第348行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第353行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第365行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第367行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第378行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第398行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第402行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第411行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第426行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第428行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第433行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第442行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第444行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第460行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第473行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第474行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第483行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第485行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第490行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第512行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/advanced_predictions.py
问题数量: 6

🔴 **第33行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第58行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第70行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/cqrs.py
问题数量: 20

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第68行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第82行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第83行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第95行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第127行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第140行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第169行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第170行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第182行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第183行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第209行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第210行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/buggy_api.py
问题数量: 7

🔴 **第7行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第8行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第26行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第27行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第57行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/dependencies.py
问题数量: 11

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第62行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第63行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第83行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第102行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第114行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/middleware.py
问题数量: 14

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第107行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第125行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第131行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第134行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第168行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第177行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第211行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/predictions_srs_simple.py
问题数量: 17

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第143行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第213行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第254行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第283行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第344行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第345行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第399行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第400行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第430行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第492行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第493行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第529行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第530行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第541行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第548行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/prediction_api.py
问题数量: 43

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第132行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第171行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第209行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第211行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第240行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第242行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第276行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第278行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第323行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第325行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第349行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第351行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第390行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第429行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第463行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第465行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第480行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第482行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第501行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第503行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第533行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第535行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第563行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第565行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第598行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第600行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第619行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第621行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第650行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第651行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第668行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第670行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第689行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第698行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第720行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/data_router.py
问题数量: 20

🔴 **第121行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第164行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第165行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第191行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第192行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第246行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第247行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第267行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第268行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第299行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第300行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第373行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第374行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第399行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第400行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第430行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第431行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第471行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第472行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/features.py
问题数量: 12

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第74行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第175行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第176行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第209行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第210行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/auth_dependencies_messy.py
问题数量: 9

🟡 **第11行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第52行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第53行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第54行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/predictions.py
问题数量: 2

🔴 **第34行** - requests_get
   - 描述: 检测到将同步GET请求替换为异步
   - 建议: 替换为 'await httpx.AsyncClient().get(' 并确保在异步函数中调用

🔴 **第39行** - requests_post
   - 描述: 检测到将同步POST请求替换为异步
   - 建议: 替换为 'await httpx.AsyncClient().post(' 并确保在异步函数中调用

### src/api/simple_auth.py
问题数量: 22

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第83行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第99行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第126行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第138行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第177行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第193行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第195行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第214行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第241行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第242行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第255行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第256行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第274行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第275行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第280行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第281行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/performance_management.py
问题数量: 43

🔴 **第63行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第112行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第119行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第121行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第234行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第263行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第265行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第270行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第287行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第288行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第289行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第301行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第303行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第330行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第332行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第381行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第383行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第427行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第429行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第435行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第436行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第463行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第465行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第477行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第481行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第486行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第490行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第494行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第498行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第508行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第515行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第527行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第532行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第537行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第548行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第564行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第569行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第579行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第580行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/batch_analytics.py
问题数量: 6

🔴 **第33行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第57行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第69行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/app.py
问题数量: 17

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第199行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第218行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第236行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第237行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第247行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第248行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第264行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第265行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第274行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第275行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第287行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第288行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/analytics.py
问题数量: 7

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第40行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第103行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第166行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第167行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/predictions_enhanced.py
问题数量: 21

🟡 **第16行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第147行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第168行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第194行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第229行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第241行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第299行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第300行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第349行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第350行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第375行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第444行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第445行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第471行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第478行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/data_integration.py
问题数量: 36

🔴 **第32行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第83行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第115行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第157行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第172行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第172行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第177行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第177行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第196行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第197行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第223行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第247行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第248行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第266行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第266行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第286行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第287行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第298行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第298行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第305行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第305行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第310行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第310行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第315行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第315行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第321行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第321行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第326行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第326行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第345行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第346行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/observers.py
问题数量: 43

🔴 **第42行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第73行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第80行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第87行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第106行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第122行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第123行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第151行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第171行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第186行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第187行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第207行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第208行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第219行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第220行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第254行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第255行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第266行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第267行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第289行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第290行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第312行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第313行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第316行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第324行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第325行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第341行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第342行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第358行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第359行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第364行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第365行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第377行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第378行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第390行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第391行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/realtime_streaming.py
问题数量: 6

🔴 **第44行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第62行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第74行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/repositories.py
问题数量: 4

🔴 **第14行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第15行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第20行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/events.py
问题数量: 28

🔴 **第66行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第73行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第88行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第95行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第118行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第130行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第131行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第136行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第137行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第140行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第146行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第147行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第148行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第154行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第155行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第163行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第183行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第192行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第195行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第204行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第205行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第212行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/monitoring.py
问题数量: 34

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第76行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第77行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第78行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第79行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第80行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第161行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第162行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第163行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第176行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第177行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第203行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第204行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第236行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第237行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第296行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第297行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第303行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第330行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第331行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第342行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第343行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第358行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第359行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第369行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第370行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第379行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第380行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第390行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第391行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/prometheus_metrics.py
问题数量: 8

🔴 **第56行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第92行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/features_simple.py
问题数量: 7

🔴 **第22行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第36行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第69行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第83行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/auth.py
问题数量: 8

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第33行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第39行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第51行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第65行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/predictions/health.py
问题数量: 2

🔴 **第17行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/predictions/health_simple.py
问题数量: 2

🔴 **第17行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/predictions/optimized_router.py
问题数量: 47

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第49行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第100行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第125行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第155行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第192行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第229行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第230行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第251行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第329行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第391行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第443行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第524行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第623行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第726行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第826行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第908行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第980行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第1001行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第1062行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1204行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第1308行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第1309行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第1329行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第1330行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第1344行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第1345行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第1361行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第1362行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第1375行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第1376行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第1392行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第1393行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第1406行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第1407行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第1419行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第1420行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第1431行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第1432行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第1443行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第1444行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1456行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1493行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1519行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1554行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1580行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/predictions/router.py
问题数量: 32

🔴 **第110行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第132行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第152行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第153行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第182行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第183行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第216行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第222行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第267行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第268行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第299行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第300行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第326行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第327行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第342行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第344行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第351行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第355行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第356行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第357行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第358行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第359行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第372行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第373行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第421行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第422行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第466行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第467行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/adapters/router.py
问题数量: 9

🔴 **第10行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第11行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第28行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第34行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第67行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/facades/router.py
问题数量: 2

🔴 **第10行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第11行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/middleware/cache_middleware.py
问题数量: 15

🟡 **第19行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第47行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第149行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第163行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第164行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第165行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/health/__init__.py
问题数量: 17

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第50行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第58行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第84行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第123行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第151行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第157行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第171行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第177行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/api/health/utils.py
问题数量: 6

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第76行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第114行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第142行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/health/routes.py
问题数量: 4

🔴 **第8行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第46行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/auth/dependencies.py
问题数量: 10

🟡 **第15行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第145行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第174行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第178行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/auth/__init__.py
问题数量: 15

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第92行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第106行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第162行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第163行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/api/auth/router.py
问题数量: 23

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第70行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第113行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第146行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第168行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第185行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第212行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第243行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第248行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第271行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第276行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第298行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第303行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第322行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第327行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第345行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第350行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/routes/user_management.py
问题数量: 27

🔴 **第42行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第59行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第76行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第89行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第146行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第147行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第156行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第172行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第181行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第195行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第196行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第219行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第220行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第228行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第239行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第240行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第248行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第259行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第260行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第266行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/api/optimization/smart_cache_system.py
问题数量: 31

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第100行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第108行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第109行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第127行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第182行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第212行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第216行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第231行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第247行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第258行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第283行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第300行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第345行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第356行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第373行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第392行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第400行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第402行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第431行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第436行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第441行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第461行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第483行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/optimization/database_query_optimizer.py
问题数量: 25

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第190行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第219行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第249行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第270行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第278行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第286行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第302行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第340行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第379行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第398行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第399行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第403行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第443行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第451行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/optimization/api_performance_optimizer.py
问题数量: 20

🔴 **第65行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第94行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第133行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第156行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第185行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第221行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第222行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第251行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第252行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第318行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第319行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第340行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第355行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第366行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第390行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第391行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/optimization/enhanced_performance_middleware.py
问题数量: 17

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第176行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第266行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第275行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第329行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第342行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第356行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第367行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第376行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第381行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第387行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/optimization/cache_performance_api.py
问题数量: 42

🔴 **第97行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第179行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第245行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第246行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第267行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第268行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第280行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第298行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第331行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第332行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第353行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第354行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第372行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第388行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第389行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第414行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第415行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第437行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第458行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第459行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第481行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第505行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第506行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第527行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第559行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第560行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第600行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第601行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第633行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第662行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第663行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第684行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第685行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第713行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第714行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第780行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第781行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第814行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第853行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第854行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/optimization/database_performance_middleware.py
问题数量: 27

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第167行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第177行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第181行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第187行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第198行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第222行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第254行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第257行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第298行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第335行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第360行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第396行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第415行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第423行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第431行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/optimization/database_performance_api.py
问题数量: 55

🔴 **第58行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第78行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第79行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第80行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第94行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第95行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第95行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第98行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第98行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第105行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第106行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第107行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第118行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第162行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第185行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第186行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第207行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第208行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第235行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第253行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第254行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第279行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第280行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第308行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第309行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第333行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第334行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第367行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第413行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第414行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第435行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第436行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第478行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第479行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第498行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第499行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第500行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第533行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第534行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第535行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第552行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第558行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第567行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第573行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第579行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第580行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第581行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第617行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第639行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第648行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第649行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/optimization/query_execution_analyzer.py
问题数量: 51

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第123行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第180行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第182行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第193行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第193行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第218行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第249行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第258行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第261行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第262行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第263行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第264行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第265行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第266行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第267行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第268行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第269行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第270行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第271行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第272行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第273行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第274行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第275行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第276行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第277行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第288行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第301行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第302行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第335行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第352行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第397行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第416行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第429行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第461行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第504行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第564行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第567行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第616行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第625行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第632行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第640行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第642行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第644行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第649行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第691行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第699行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/optimization/connection_pool_optimizer.py
问题数量: 22

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第205行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第233行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第266行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第283行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第316行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第336行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第383行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第449行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第458行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第466行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/data/models/enhanced_team_models.py
问题数量: 34

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第55行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第56行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第92行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第126行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第148行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第216行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第232行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第242行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第258行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第267行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第287行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第302行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第332行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第344行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第348行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第355行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第360行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第375行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第389行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第408行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第410行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第412行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第421行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第434行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第440行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第461行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/data/models/enhanced_match_models.py
问题数量: 26

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第48行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第49行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第178行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第191行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第192行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第193行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第194行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第195行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第234行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第237行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第238行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第239行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第244行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第255行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第263行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第276行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第289行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第295行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第301行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/data/models/enhanced_odds_models.py
问题数量: 23

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第64行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第65行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第99行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第123行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第153行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第215行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第221行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第228行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第234行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第241行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第274行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第280行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第298行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第307行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第333行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第346行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第352行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/data/models/validation_base.py
问题数量: 14

🟡 **第15行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第165行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第202行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第207行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第212行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第216行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/api/data/models/data_quality.py
问题数量: 15

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第146行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第181行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第191行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第224行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第232行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第249行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第263行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/prediction_validator.py
问题数量: 6

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第148行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/validators.py
问题数量: 5

🟡 **第7行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第92行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/response.py
问题数量: 4

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/string_utils.py
问题数量: 60

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第121行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第181行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第227行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第302行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第373行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第397行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第408行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第431行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第451行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第461行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第480行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第485行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第504行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第541行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第549行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第557行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第572行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第579行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第594行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第601行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第613行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第621行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第628行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第634行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第638行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第643行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第650行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第657行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第662行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第684行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第709行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第742行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第754行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第824行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第832行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第837行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第842行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第875行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第893行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第920行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第939行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第968行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第987行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第994行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1002行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1009行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1034行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1039行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1063行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1074行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1110行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/dict_utils.py
问题数量: 42

🟡 **第13行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第99行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第130行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第143行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第145行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第148行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第153行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第169行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第176行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第181行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第192行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第203行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第206行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第224行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第231行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第238行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第240行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第243行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第248行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第254行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第259行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第264行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第269行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第271行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第274行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第279行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第299行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第319行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第322行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第335行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第349行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第353行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/utils/_retry.py
问题数量: 32

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第148行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第153行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第169行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第185行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第191行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第196行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第205行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第229行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第252行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第267行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第280行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第295行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第308行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第319行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第337行** - time_sleep
   - 描述: 检测到将同步sleep替换为异步
   - 建议: 替换为 'await asyncio.sleep(' 并确保在异步函数中调用

🟡 **第344行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第355行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/formatters.py
问题数量: 4

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第14行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第19行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第27行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/time_utils.py
问题数量: 34

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第112行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第127行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第146行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第168行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第189行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第194行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第199行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第206行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第224行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第239行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第244行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第269行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第276行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第288行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第298行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第303行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第310行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/config_loader.py
问题数量: 1

🟡 **第13行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/helpers.py
问题数量: 5

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第14行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/crypto_utils.py
问题数量: 18

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第99行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第170行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第177行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/data_validator.py
问题数量: 15

🟡 **第19行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第155行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第190行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第200行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第245行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第259行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第264行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/date_utils_broken.py
问题数量: 4

🟡 **第8行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第13行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/file_utils.py
问题数量: 28

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第148行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第153行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第174行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第185行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第190行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第200行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第226行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第235行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第254行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第266行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第282行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第294行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第306行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/fotmob_match_matcher.py
问题数量: 31

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第85行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第86行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第87行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第115行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第116行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第116行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第117行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第117行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第119行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第119行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第120行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第121行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第151行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第155行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第165行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第177行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第177行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第178行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第178行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第179行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第180行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第202行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第237行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第293行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第345行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第361行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第369行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/date_utils.py
问题数量: 28

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第149行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第182行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第198行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第214行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第220行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第229行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第241行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第249行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第258行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第267行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第276行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第288行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第301行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第328行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第342行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第350行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/i18n.py
问题数量: 6

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/warning_filters.py
问题数量: 1

🟡 **第14行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/utils/_retry/__init__.py
问题数量: 26

🟡 **第19行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第83行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第112行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第123行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第127行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第148行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第156行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第170行** - time_sleep
   - 描述: 检测到将同步sleep替换为异步
   - 建议: 替换为 'await asyncio.sleep(' 并确保在异步函数中调用

🟡 **第181行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第189行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第191行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第214行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第224行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第226行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第247行** - time_sleep
   - 描述: 检测到将同步sleep替换为异步
   - 建议: 替换为 'await asyncio.sleep(' 并确保在异步函数中调用

🟡 **第256行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第261行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第265行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/timeseries/influxdb_client.py
问题数量: 5

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第11行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/jobs/data_quality_report.py
问题数量: 8

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第27行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第185行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第231行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/jobs/run_season_backfill.py
问题数量: 63

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第90行** - requests_get
   - 描述: 检测到将同步GET请求替换为异步
   - 建议: 替换为 'await httpx.AsyncClient().get(' 并确保在异步函数中调用

🔴 **第90行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第143行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第143行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第185行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第186行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第189行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第194行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第195行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第199行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第208行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第209行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第232行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第241行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第245行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第255行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第255行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第256行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第256行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第257行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第257行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第267行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第273行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第276行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第285行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第346行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第394行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第431行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第444行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第459行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第463行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第468行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第469行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第484行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第484行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第493行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第497行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第502行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第503行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第503行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第504行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第504行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第505行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第505行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第506行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第506行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第509行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第509行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第515行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第515行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第536行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第536行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第556行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第560行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第570行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第589行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第602行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第603行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第641行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/jobs/run_l2_api_details.py
问题数量: 23

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第161行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第232行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第233行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第263行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第329行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第377行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第378行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第380行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第381行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第383行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第383行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第385行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第386行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第392行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第393行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第394行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第395行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第396行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第398行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/jobs/run_season_fixtures.py
问题数量: 44

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第47行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第48行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第53行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第67行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第86行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第94行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第95行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第95行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第96行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第96行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第99行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第99行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第100行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第100行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第102行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第103行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第112行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第134行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第146行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第177行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第178行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第181行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第190行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第192行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第250行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第288行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第296行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第325行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第359行** - requests_get
   - 描述: 检测到将同步GET请求替换为异步
   - 建议: 替换为 'await httpx.AsyncClient().get(' 并确保在异步函数中调用

🔴 **第359行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第395行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第395行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第396行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第396行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第397行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第406行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第406行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第408行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第408行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第411行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/jobs/inspect_data_quality.py
问题数量: 14

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第114行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第125行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第170行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第259行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第339行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第362行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/jobs/run_l2_details.py
问题数量: 58

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第59行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第60行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第61行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第66行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第68行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第70行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第134行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第147行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第147行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第161行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第189行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第231行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第231行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第234行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第234行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第238行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第239行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第254行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第255行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第258行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第259行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第262行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第263行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第270行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第276行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第299行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第301行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第304行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第309行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第311行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第318行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第321行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第323行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第326行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第332行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第337行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第343行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第345行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第393行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第393行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第425行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🔴 **第468行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第468行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第492行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第495行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第505行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第505行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第510行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第515行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第569行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第570行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第571行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第572行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第583行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/jobs/run_l2_details_fixed.py
问题数量: 47

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第48行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第61行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第61行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第113行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第113行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第116行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第116行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第116行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第116行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第118行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第125行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第125行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第125行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第125行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第131行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第140行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第141行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第142行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第143行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第144行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第145行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第146行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第151行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第152行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第157行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第158行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第159行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第160行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第165行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第166行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第173行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第173行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第175行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第175行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第192行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第192行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第216行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第219行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第229行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第229行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第281行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/jobs/run_l1_fixtures.py
问题数量: 10

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第49行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第57行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第68行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第173行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第201行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第249行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/repositories/base.py
问题数量: 20

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第72行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第97行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第168行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第178行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第178行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第181行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第187行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第187行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/repositories/user_fixed.py
问题数量: 37

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第27行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第30行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第40行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第47行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第48行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第49行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第55行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第71行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第72行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第88行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第94行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第113行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第114行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第115行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第122行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第130行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第147行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第154行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第174行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/repositories/prediction.py
问题数量: 59

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第36行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第55行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第61行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第79行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第140行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第171行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第185行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第185行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第205行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第208行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第208行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第211行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第227行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第227行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第230行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第240行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第240行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第243行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第247行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第254行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第258行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第262行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第268行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第271行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第271行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第274行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第282行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第283行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第288行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第292行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第309行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第309行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第310行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第316行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第319行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第319行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第320行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第323行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第335行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第336行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第342行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第350行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/repositories/user.py
问题数量: 45

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第40行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第50行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第57行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第58行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第59行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第65行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第81行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第82行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第98行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第98行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第104行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第112行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第123行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第124行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第125行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第132行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第174行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第193行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第197行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第201行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第207行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第213行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/repositories/match_fixed.py
问题数量: 40

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第41行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第51行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第51行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第59行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第60行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第61行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第62行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第63行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第69行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第85行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第86行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第99行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第130行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第135行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第148行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第161行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第168行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第182行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第193行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第204行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第218行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第234行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第242行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第249行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第250行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第251行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第252行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第253行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第260行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

### src/repositories/provider.py
问题数量: 18

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第127行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第145行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第153行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第162行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第177行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第191行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/repositories/di.py
问题数量: 7

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/repositories/auth_user.py
问题数量: 7

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第26行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第32行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/repositories/base_fixed.py
问题数量: 20

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第74行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第99行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第99行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第170行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第180行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第180行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第183行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第189行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第189行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/repositories/match.py
问题数量: 45

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第50行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第60行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第68行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第69行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第70行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第71行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第72行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第78行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第94行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第95行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第99行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第108行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第139行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第170行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第177行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第191行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第202行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第213行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第227行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第243行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第251行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第258行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第259行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第260行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第261行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第262行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第269行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第279行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第283行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第287行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/stubs/mocks/feast.py
问题数量: 5

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第11行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/stubs/mocks/confluent_kafka.py
问题数量: 5

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第11行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/facades/base.py
问题数量: 21

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第83行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第95行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第126行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第130行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第140行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第146行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/facades/factory.py
问题数量: 19

🟡 **第15行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第40行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第126行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第135行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第156行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第174行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第193行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/facades/subsystems/database.py
问题数量: 9

🟡 **第19行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第72行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/patterns/decorator.py
问题数量: 59

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第110行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第154行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第178行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第182行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第211行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第224行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第226行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第235行** - time_sleep
   - 描述: 检测到将同步sleep替换为异步
   - 建议: 替换为 'await asyncio.sleep(' 并确保在异步函数中调用

🟡 **第252行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第256行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第268行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第282行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第291行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第304行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第306行** - time_sleep
   - 描述: 检测到将同步sleep替换为异步
   - 建议: 替换为 'await asyncio.sleep(' 并确保在异步函数中调用

🟡 **第311行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第319行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第337行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第376行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第384行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第395行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第405行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第417行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第427行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第439行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第456行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第468行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第481行** - time_sleep
   - 描述: 检测到将同步sleep替换为异步
   - 建议: 替换为 'await asyncio.sleep(' 并确保在异步函数中调用

🟡 **第494行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第504行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第508行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第523行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第534行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第551行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第555行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第566行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第569行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第571行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第583行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第587行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第600行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第603行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第605行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第628行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/patterns/observer.py
问题数量: 65

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第92行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第126行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第130行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第139行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第148行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第156行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第193行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第211行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第249行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第253行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第264行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第275行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第284行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第301行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第305行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第323行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第336行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第351行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第355行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第365行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第380行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第395行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第403行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第425行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第429行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第447行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第457行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第466行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第472行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第486行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第490行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第514行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第525行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第529行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第533行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第537行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第551行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第568行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第569行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第581行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第610行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第621行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第625行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第630行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第635行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第650行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第654行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第659行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第691行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/patterns/facade_simple.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/patterns/adapter.py
问题数量: 33

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第99行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第131行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第149行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第199行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第204行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第210行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第233行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第261行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第282行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第289行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第296行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第303行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第308行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第324行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第332行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第340行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第348行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/monitoring/health_checker.py
问题数量: 16

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第123行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第124行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第127行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第130行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第131行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第154行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第208行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第251行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第311行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第320行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第360行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/monitoring/alert_handlers.py
问题数量: 19

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第105行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第125行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第149行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第160行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第176行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第214行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第216行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/monitoring/metrics_exporter.py
问题数量: 23

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第225行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第254行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第271行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第288行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第301行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第333行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第355行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第374行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第395行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第395行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第412行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第416行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第421行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第421行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第441行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第463行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第472行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第495行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第523行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第550行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/monitoring/metrics_collector_enhanced.py
问题数量: 12

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/monitoring/quality_metrics_collector.py
问题数量: 19

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第27行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第150行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第152行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第155行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第209行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第259行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第290行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第298行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第319行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第348行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第381行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第409行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第423行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第447行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/monitoring/system_monitor.py
问题数量: 11

🟡 **第13行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第92行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第108行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/monitoring/metrics_collector.py
问题数量: 22

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第110行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第162行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第170行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/monitoring/advanced_monitoring_system.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/monitoring/apm_integration.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/monitoring/router.py
问题数量: 2

🔴 **第10行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第11行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/monitoring/system_metrics.py
问题数量: 21

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第159行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第184行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第185行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第186行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第187行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第191行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第192行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第196行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第197行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第198行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第199行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第203行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第204行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第210行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/monitoring/alert_manager.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/monitoring/alert_manager_mod/__init__.py
问题数量: 40

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第135行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第145行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第185行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第191行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第211行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第218行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第229行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第235行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第242行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第270行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第278行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第286行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第297行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第302行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第308行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第319行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第326行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第333行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第347行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第355行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第364行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第378行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第385行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第403行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第416行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第421行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第428行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第442行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第447行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第454行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第461行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第473行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第480行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第487行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第501行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/monitoring/quality/core/monitor/__init__.py
问题数量: 2

🟡 **第14行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/monitoring/quality/core/results/__init__.py
问题数量: 2

🟡 **第14行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/performance/config.py
问题数量: 8

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第190行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第196行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第202行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第213行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/performance/profiler.py
问题数量: 44

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第110行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第123行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第127行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第130行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第155行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第176行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第222行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第232行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第278行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第309行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第339行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第349行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第358行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第364行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第375行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第378行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第396行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第409行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第414行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第446行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第473行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第479行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第488行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第494行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第501行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第511行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第515行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第523行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第528行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第544行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第555行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第559行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第566行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第570行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第582行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第591行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第600行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/performance/middleware.py
问题数量: 18

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第169行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第203行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第220行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第300行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第313行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第323行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第330行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第340行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第347行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第382行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第390行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第397行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第444行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/performance/api.py
问题数量: 14

🔴 **第67行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第116行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第151行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第166行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第167行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第168行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第179行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第224行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第225行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/performance/optimizer.py
问题数量: 24

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第122行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第123行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第146行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第186行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第186行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第202行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第224行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第271行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第271行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第308行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第318行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第322行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第339行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第369行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第384行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第384行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第395行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第395行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第406行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第406行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第434行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/performance/monitoring.py
问题数量: 24

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第112行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第187行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第268行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第321行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第345行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第352行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第352行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第357行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第357行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第362行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第362行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第371行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第371行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第376行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第376行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第387行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第395行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/performance/analyzer.py
问题数量: 13

🟡 **第16行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第37行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第40行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第49行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第52行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/performance/integration.py
问题数量: 26

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第114行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第135行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第149行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第150行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第153行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第155行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第156行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第160行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第161行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第190行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第222行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第238行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第261行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第269行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第295行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第300行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第305行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第310行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/football_prediction_pipeline.py
问题数量: 12

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第154行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第185行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第343行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第372行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第401行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第437行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第469行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第493行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第500行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第512行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/feature_selector.py
问题数量: 11

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第205行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第287行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第365行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第403行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第427行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第451行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第473行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第510行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/enhanced_xgboost_trainer.py
问题数量: 9

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第148行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第159行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第190行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第206行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第237行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/enhanced_feature_engineering.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/experiment_tracking.py
问题数量: 16

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第135行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第170行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第187行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第219行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第235行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第251行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第309行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第322行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第323行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第324行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第351行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/advanced_model_trainer.py
问题数量: 2

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/enhanced_real_model_training.py
问题数量: 6

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/lstm_predictor.py
问题数量: 24

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第174行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第200行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第241行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第337行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第408行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第426行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第427行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第431行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第432行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第436行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第437行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第441行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第442行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第465行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第490行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第519行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第549行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第591行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第596行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第604行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/model_training.py
问题数量: 20

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第99行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第178行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第260行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第292行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第327行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第348行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第351行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第353行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第357行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第376行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第393行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第407行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第448行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第464行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第473行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第475行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第507行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第516行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/test_hyperparameter_optimization.py
问题数量: 2

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第179行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/automl_pipeline.py
问题数量: 8

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第159行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第200行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第212行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第231行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第254行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/router.py
问题数量: 2

🔴 **第10行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第11行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/xgboost_hyperparameter_optimization.py
问题数量: 17

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第156行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第253行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第260行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第284行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第301行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第349行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第369行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第383行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第416行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第432行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第451行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第471行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第481行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第493行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/real_model_training.py
问题数量: 7

🟡 **第11行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/model_performance_monitor.py
问题数量: 8

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第159行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第200行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第212行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第231行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第254行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/models/poisson_model.py
问题数量: 34

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第57行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第58行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第61行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第62行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第63行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第64行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第110行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第111行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第112行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第113行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第114行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第166行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第169行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第171行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第175行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第178行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第180行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第240行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第257行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第297行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第310行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第311行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第326行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第368行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第394行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第459行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第496行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第502行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第508行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第543行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/models/base_model.py
问题数量: 21

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第112行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第139行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第161行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第182行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第198行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第216行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第239行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第267行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第282行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第314行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第326行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第343行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第352行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第360行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/models/elo_model.py
问题数量: 47

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第83行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第113行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第114行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第125行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第148行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第196行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第197行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第199行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第200行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第207行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第261行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第262行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第263行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第264行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第265行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第282行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第304行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第362行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第387行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第406行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第423行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第426行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第427行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第468行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第511行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第526行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第527行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第538行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第603行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第655行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第661行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第667行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第676行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第678行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第687行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第689行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第702行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第737行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第759行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第761行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第775行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml/prediction/prediction_service.py
问题数量: 27

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第92行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第159行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第200行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第216行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第232行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第264行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第311行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第327行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第346行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第354行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第361行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第384行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第390行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第401行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第413行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第425行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第426行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第437行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第484行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/models/prediction_model.py
问题数量: 19

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第211行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第254行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第291行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第298行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第333行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第345行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第346行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第347行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第358行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第364行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第366行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第369行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/common_models.py
问题数量: 7

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第73行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/train_v1_xgboost.py
问题数量: 11

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第168行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第198行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第234行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第288行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第321行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第379行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/train_baseline.py
问题数量: 7

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第270行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第315行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/metrics_exporter.py
问题数量: 8

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第202行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第222行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第240行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/prediction.py
问题数量: 22

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第53行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第125行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第148行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第155行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第178行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第183行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/model_training_broken.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/train_v1_3_realistic.py
问题数量: 17

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第154行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第203行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第290行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第323行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第332行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第426行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第537行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第669行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第691行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第794行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第841行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第902行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第970行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1081行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/train_v1_final.py
问题数量: 10

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第143行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第206行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第290行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第490行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第503行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第600行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第663行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/train_v1_2_hybrid.py
问题数量: 14

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第110行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第179行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第283行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第364行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第383行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第457行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第487行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第544行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第606行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第679行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/raw_data.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/auth_user.py
问题数量: 7

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第204行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/model_training.py
问题数量: 33

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第145行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第210行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第277行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第282行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第286行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第290行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第293行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第311行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第335行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第352行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第361行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第368行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第378行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第468行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第537行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第588行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第613行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/base_models.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/train_pure_realistic.py
问题数量: 13

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第131行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第281行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第303行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第331行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第370行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第431行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第489行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/common/api_models.py
问题数量: 1

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/common/base_models.py
问题数量: 1

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/common/data_models.py
问题数量: 1

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/external/league.py
问题数量: 81

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第147行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第153行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第156行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第157行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第160行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第161行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第165行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第166行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第184行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第197行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第198行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第199行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第200行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第201行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第202行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第203行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第204行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第205行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第220行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第221行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第227行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第233行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第236行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第239行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第242行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第245行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第248行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第253行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第257行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第261行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第262行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第263行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第264行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第267行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第269行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第270行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第271行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第272行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第275行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第277行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第278行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第281行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第284行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第285行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第306行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第326行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第337行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第342行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第347行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第406行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第410行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第415行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第419行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第455行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第460行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第465行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第466行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第467行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第468行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第469行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第470行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第471行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第472行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第473行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第474行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第475行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第476行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第477行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第478行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第479行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第480行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第481行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第482行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第488行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第492行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第493行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/models/external/competition.py
问题数量: 1

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/models/external/team.py
问题数量: 54

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第122行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第126行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第140行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第141行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第142行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第143行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第144行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第145行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第146行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第147行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第148行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第149行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第150行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第151行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第152行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第153行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第161行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第162行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第163行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第171行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第177行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第183行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第187行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第190行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第193行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第196行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第201行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第205行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第209行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第210行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第211行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第212行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第215行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第216行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第217行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第218行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第219行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第222行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第224行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第225行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第226行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第227行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第234行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第254行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第257行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第258行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第259行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/models/external/match.py
问题数量: 55

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第92行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第143行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第147行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第148行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第149行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第150行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第153行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第154行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第155行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第158行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第179行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第189行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第190行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第191行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第192行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第194行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第195行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第196行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第199行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第200行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第201行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第202行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第203行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第204行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第205行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第206行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第211行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第212行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第220行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第221行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第221行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第222行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第222行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第223行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第223行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第239行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第243行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第244行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第247行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第248行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第249行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第252行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第263行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第266行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第277行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第278行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第282行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/middleware/cors_config.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/middleware/performance_monitoring.py
问题数量: 5

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第45行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/middleware/tenant_middleware.py
问题数量: 37

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第89行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第90行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第91行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第114行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第124行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第131行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第136行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第159行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第170行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第177行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第209行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第230行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第240行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第242行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第252行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第274行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第297行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第307行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第309行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第318行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第337行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第364行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第375行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第377行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第386行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第405行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第430行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第435行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第441行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第447行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/middleware/i18n.py
问题数量: 2

🟡 **第12行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第14行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/middleware/i18n_utils.py
问题数量: 3

🟡 **第6行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第9行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第16行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/middleware/router.py
问题数量: 2

🔴 **第10行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第11行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/decorators/service.py
问题数量: 23

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第40行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第143行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第156行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第162行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第188行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第193行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第196行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第208行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第221行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第234行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第246行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第251行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第258行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/decorators/base.py
问题数量: 39

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第144行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第146行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第162行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第167行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第188行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第190行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第205行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第213行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第219行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第221行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第225行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第229行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第233行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第250行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第256行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第260行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第265行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第267行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第269行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第273行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第283行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第287行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/decorators/factory.py
问题数量: 18

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第125行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第127行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第131行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第283行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第291行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第296行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第301行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第306行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/decorators/implementations/logging.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/realtime/prediction_api.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/realtime/prediction_service.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/realtime/match_api.py
问题数量: 22

🔴 **第92行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第224行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第268行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第270行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第294行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第295行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第320行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第321行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第342行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第363行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第364行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第383行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第401行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第402行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第421行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第422行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第459行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第495行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第496行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第549行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/realtime/match_service.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/realtime/subscriptions.py
问题数量: 25

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第90行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第92行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第94行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第97行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第100行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第104行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第143行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第185行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第207行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第218行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第239行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第262行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第268行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第279行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第288行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第319行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第339行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第366行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第388行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第404行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/realtime/quality_monitor_server.py
问题数量: 36

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第76行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第80行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第90行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第142行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第167行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第179行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第180行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第181行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第182行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第183行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第236行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第243行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第244行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第257行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第265行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第273行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第280行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第287行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第288行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第307行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第333行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第353行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第359行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第414行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第423行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第449行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第455行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/realtime/events.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/realtime/handlers.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/realtime/manager.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/realtime/websocket.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/realtime/router.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/entities.py
问题数量: 3

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/models/league.py
问题数量: 39

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第123行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第159行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第224行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第248行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第267行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第286行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第291行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第296行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第304行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第309行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第324行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第329行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第336行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第348行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第355行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第360行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第364行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第370行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第379行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第383行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第387行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第395行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第440行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第446行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第450行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第454行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第463行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第467行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第469行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第474行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/models/prediction.py
问题数量: 36

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第114行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第147行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第201行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第276行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第285行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第293行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第304行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第309行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第345行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第350行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第355行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第360行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第365行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第376行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第403行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第407行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第411行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第419行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第459行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第484行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第486行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第488行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第492行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第497行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/models/team.py
问题数量: 36

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第108行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第131行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第159行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第248行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第269行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第293行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第298行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第303行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第308行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第313行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第337行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第342行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第347行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第354行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第371行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第376行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第384行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第388行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第392行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第400行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第447行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第463行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第470行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第472行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第477行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/models/match.py
问题数量: 32

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第155行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第179行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第187行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第197行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第201行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第205行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第209行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第222行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第229行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第234行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第239行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第244行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第251行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第262行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第266行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第270行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第278行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第306行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第315行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第317行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第319行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第323行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第328行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/strategies/base.py
问题数量: 15

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第120行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第130行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第142行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第146行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第178行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第190行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第193行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第226行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/strategies/ensemble.py
问题数量: 2

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/strategies/statistical.py
问题数量: 11

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第112行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第121行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第135行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第145行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第167行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/strategies/ml_model.py
问题数量: 10

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第110行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第131行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/strategies/factory.py
问题数量: 36

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第123行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第157行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第161行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第162行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第189行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第198行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第200行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第204行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第221行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第235行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第250行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第252行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第255行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第270行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第280行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第285行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第302行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第303行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第314行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第388行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第409行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第431行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第445行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第448行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第471行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第475行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第479行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第505行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第510行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第518行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/strategies/enhanced_ml_model.py
问题数量: 9

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第178行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第189行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/services/prediction_service.py
问题数量: 15

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第127行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第205行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第242行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第271行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第295行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第327行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第331行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/services/match_service.py
问题数量: 25

🟡 **第27行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第159行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第179行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第198行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第226行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第239行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第259行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第270行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第279行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第305行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第337行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第341行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第345行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第349行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/services/scoring_service.py
问题数量: 19

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第169行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第181行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第193行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第219行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第241行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第250行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第258行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第275行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/services/team_service.py
问题数量: 15

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第99行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第153行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第179行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第186行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第212行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第216行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第220行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/services/user_service.py
问题数量: 4

🟡 **第13行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/events/base.py
问题数量: 5

🟡 **第19行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/events/prediction_events.py
问题数量: 20

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第153行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第165行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第169行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第186行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第190行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第201行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第221行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/events/event_data.py
问题数量: 6

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第135行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/events/bus.py
问题数量: 15

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第42行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第58行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第92行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第112行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第125行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/events/handlers.py
问题数量: 21

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第83行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第131行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第139行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第167行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第233行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第238行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第243行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第248行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/events/types.py
问题数量: 10

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第143行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第199行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第220行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain/events/match_events.py
问题数量: 13

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第114行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第121行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cqrs/queries.py
问题数量: 32

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第154行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第181行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第198行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第201行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第218行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第245行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第248行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第265行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第279行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第302行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第305行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第322行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第336行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第356行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第359行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第376行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第388行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第412行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第415行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cqrs/dto.py
问题数量: 7

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第192行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第199行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cqrs/commands.py
问题数量: 20

🟡 **第19行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第93行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第127行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第135行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第183行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第183行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第200行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第214行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第222行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第252行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第278行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第296行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第304行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/cqrs/base.py
问题数量: 12

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第127行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第135行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cqrs/bus.py
问题数量: 17

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第108行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第149行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第185行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第201行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第210行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cqrs/handlers.py
问题数量: 58

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第110行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第115行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第115行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第137行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第175行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第193行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第232行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第237行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第255行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第260行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第273行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第303行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第308行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第312行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第340行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第345行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第375行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第375行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第405行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第410行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第425行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第425行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第455行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第455行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第484行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第484行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第527行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第532行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第558行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第558行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第590行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第604行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第619行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第633行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第646行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第659行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第674行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第678行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第682行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第705行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第709行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第722行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第751行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第755行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第759行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第771行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第800行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第804行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第808行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第835行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第839行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第855行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第855行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/cqrs/router.py
问题数量: 2

🔴 **第10行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第11行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cqrs/application.py
问题数量: 23

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第149行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第156行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第174行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第204行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第235行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第247行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第271行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第276行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第292行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第311行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第316行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第321行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第326行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第332行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/streaming/kafka_components.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/streaming/kafka_producer.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/streaming/kafka_consumer_simple.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/streaming/stream_processor.py
问题数量: 17

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第110行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/streaming/stream_config.py
问题数量: 9

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第147行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第167行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第169行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/streaming/stream_processor_simple.py
问题数量: 24

🟡 **第14行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第27行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第80行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第121行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第196行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第200行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第239行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第247行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第253行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第259行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第261行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第270行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第279行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第285行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第289行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第295行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第299行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/streaming/stream_config_simple.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/streaming/kafka_producer_simple.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/streaming/kafka_components_simple.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/streaming/router.py
问题数量: 2

🔴 **第10行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第11行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/quality_gates/gate_system.py
问题数量: 59

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第171行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第175行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第176行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第199行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第202行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第208行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第219行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第222行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第239行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第248行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第254行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第265行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第270行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第270行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第276行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第287行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第292行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第292行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第293行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第304行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第311行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第344行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第346行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第349行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第349行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第350行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第353行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第353行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第354行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第357行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第357行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第358行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第361行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第361行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第362行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第365行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第365行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第366行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第369行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第369行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第370行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第375行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第405行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第406行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第447行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第466行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第495行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第497行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第500行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/alerting/alert_engine.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/alerting/notification_manager.py
问题数量: 53

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第52行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第53行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第54行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第55行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第56行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第57行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第240行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第289行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第292行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第293行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第294行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第295行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第298行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第306行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第322行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第331行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第386行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第389行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第390行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第393行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第401行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第408行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第422行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第431行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第461行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第472行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第475行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第476行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第477行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第478行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第481行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第489行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第496行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第510行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第519行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第560行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第571行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第606行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第625行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第650行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第684行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第699行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第700行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第706行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第711行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第716行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第728行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第734行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第742行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/config.py
问题数量: 11

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第91行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第142行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第147行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/sql_compatibility.py
问题数量: 9

🟡 **第19行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/compat.py
问题数量: 15

🟡 **第13行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第142行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第156行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第159行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第162行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第165行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第179行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/dependencies.py
问题数量: 10

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第32行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第121行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第130行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/base.py
问题数量: 20

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第108行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第145行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第161行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第162行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第168行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第206行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第212行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第216行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第225行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第232行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第281行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第287行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/definitions.py
问题数量: 24

🟡 **第27行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第114行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第120行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第126行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第147行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第152行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第155行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第156行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第159行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第160行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第167行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/compatibility.py
问题数量: 14

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第59行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第161行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第171行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第194行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第208行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第224行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第234行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/types.py
问题数量: 7

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/async_manager.py
问题数量: 41

🟡 **第16行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第17行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第118行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第119行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第125行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第126行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第127行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第128行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第156行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第161行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第177行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第218行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第225行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第240行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第248行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第262行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第273行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第288行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第296行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第316行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第324行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第325行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第328行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第340行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第355行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第359行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第359行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第363行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第378行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第382行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第382行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第387行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第402行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第406行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第406行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第407行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

### src/database/connection.py
问题数量: 7

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第131行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第174行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/repositories/base.py
问题数量: 36

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第57行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第79行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第84行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第103行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第114行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第133行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第144行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第149行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第161行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第166行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第195行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第216行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第219行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第234行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第248行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第260行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第263行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第282行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第294行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第308行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第320行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第334行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第340行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第352行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第357行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第366行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第380行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第406行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第423行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第427行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/repositories/prediction.py
问题数量: 23

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第130行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第148行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第166行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第169行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第189行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第229行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第266行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第298行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第314行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第326行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第382行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第394行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第460行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第473行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第501行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第528行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第544行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第564行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/database/repositories/user.py
问题数量: 29

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第121行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第139行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第142行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第158行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第175行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第178行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第196行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第214行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第235行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第260行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第278行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第305行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第317行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第334行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第345行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第352行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第368行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第380行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第404行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第420行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第436行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第462行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/database/repositories/team_repository.py
问题数量: 6

🟡 **第15行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第19行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第27行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/repositories/analytics_repository.py
问题数量: 13

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第74行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第121行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第145行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第157行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第197行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第271行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第347行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第422行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第545行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/database/repositories/match.py
问题数量: 26

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第55行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第70行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第112行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第131行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第147行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第165行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第183行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第186行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第204行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第222行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第225行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第243行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第267行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第270行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第296行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第316行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第346行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第390行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第406行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第438行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第449行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/repositories/match_repository/repository.py
问题数量: 13

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第57行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第57行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第67行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第89行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第92行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第118行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/database/repositories/match_repository/match.py
问题数量: 26

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第110行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第112行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第121行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第130行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第143行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第177行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第181行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第183行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第186行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第191行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第196行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

### src/database/models/league.py
问题数量: 1

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/models/audit_log.py
问题数量: 3

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/models/data_quality_log.py
问题数量: 5

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/models/data_collection_log.py
问题数量: 10

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第120行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第154行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/models/user.py
问题数量: 6

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第110行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/models/tenant.py
问题数量: 21

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第163行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第167行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第174行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第180行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第190行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第194行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第198行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第200行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第206行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第216行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第293行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第310行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第370行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第462行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第469行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/models/raw_data.py
问题数量: 4

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/models/odds.py
问题数量: 7

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第114行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第120行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第125行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/models/team.py
问题数量: 1

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/models/match.py
问题数量: 1

🟡 **第83行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/connection/pools/__init__.py
问题数量: 4

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/connection/core/__init__.py
问题数量: 3

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/migrations/env.py
问题数量: 4

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第130行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/migrations/versions/d3bf28af22ff_add_performance_critical_indexes.py
问题数量: 27

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第119行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第131行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第148行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第156行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第160行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第172行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第184行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第197行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第201行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第213行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第226行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第230行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第242行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第255行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第259行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第271行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第286行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第299行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第311行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第324行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第336行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第348行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第362行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第366行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第391行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/database/migrations/versions/09d03cebf664_implement_partitioned_tables_and_indexes.py
问题数量: 26

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第99行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第106行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第107行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第123行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第127行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第155行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第191行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第209行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第217行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第278行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第326行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第349行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第354行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第376行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第380行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第394行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第400行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第401行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第411行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第415行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第416行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第429行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第435行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/migrations/versions/007_improve_phase3_implementations.py
问题数量: 21

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第65行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第76行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第87行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第106行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第126行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第152行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第167行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第177行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第209行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第248行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第249行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第250行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第253行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第254行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第255行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第256行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第259行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第260行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第261行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/database/migrations/versions/d82ea26f05d0_add_mlops_support_to_predictions_table.py
问题数量: 2

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/migrations/versions/a20f91c49306_add_business_constraints.py
问题数量: 14

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第39行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第40行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第135行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第167行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第177行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第194行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第204行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第212行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第215行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第218行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第219行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第222行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第223行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/database/migrations/versions/f48d412852cc_add_data_collection_logs_and_bronze_layer_tables.py
问题数量: 2

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第229行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/migrations/versions/c1d8ae5075f0_add_jsonb_sqlite_compatibility.py
问题数量: 9

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第80行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第141行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第164行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/database/migrations/versions/9ac2aff86228_merge_multiple_migration_heads.py
问题数量: 2

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/migrations/versions/004_configure_database_permissions.py
问题数量: 58

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第145行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第146行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第152行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第158行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第171行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第184行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第197行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第198行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第199行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第202行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第205行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第210行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第215行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第216行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第217行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第222行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第227行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第232行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第243行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第244行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第245行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第248行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第251行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第256行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第259行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第264行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第269行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第274行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第275行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第298行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第314行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第346行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第363行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第364行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第367行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第370行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第375行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第407行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第411行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第412行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第418行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第424行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第425行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第426行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第427行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第428行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第431行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第436行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第441行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第444行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第449行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第454行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第457行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第462行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第467行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第468行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第469行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/database/migrations/versions/9de9a8b8aa92_merge_remaining_heads.py
问题数量: 2

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/migrations/versions/002_add_raw_scores_data_and_upgrade_jsonb.py
问题数量: 10

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第161行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第184行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第219行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第230行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第240行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第245行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第248行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第249行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/database/migrations/versions/005_add_multi_tenant_support.py
问题数量: 6

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第374行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第406行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第413行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第420行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第427行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/migrations/versions/d56c8d0d5aa0_initial_database_schema.py
问题数量: 2

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第491行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/migrations/versions/005_create_audit_logs_table.py
问题数量: 19

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第231行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第232行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第235行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第237行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第238行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第241行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第244行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第249行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第270行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第276行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第294行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第295行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第296行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第299行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第306行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第323行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第327行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第328行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/database/migrations/versions/test_.py
问题数量: 2

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/database/migrations/versions/database/migrations/versions/d6d814cc1078_database_performance_optimization__utils.py
问题数量: 2

🟡 **第7行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第14行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/optimizations/api_optimizations.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/optimizations/database_optimizations.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/distributed_cache_manager.py
问题数量: 68

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第123行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第154行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第182行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第190行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第199行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第209行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第245行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第263行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第268行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第273行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第278行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第286行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第290行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第296行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第309行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第325行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第338行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第355行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第360行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第362行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第363行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第364行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第381行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第385行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第386行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第392行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第398行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第436行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第497行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第520行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第525行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第527行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第530行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第545行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第553行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第561行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第571行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第583行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第587行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第616行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第623行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第638行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第672行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第677行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第688行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第715行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第720行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第723行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第729行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第737行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第739行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第741行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第757行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第767行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第778行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第782行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第787行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第791行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第824行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第830行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/redis_enhanced.py
问题数量: 70

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第196行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第203行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第210行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第212行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第214行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第220行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第241行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第245行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第249行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第253行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第257行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第261行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第265行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第269行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第273行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第277行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第281行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第286行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第290行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第295行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第300行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第302行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第311行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第318行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第325行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第333行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第340行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第347行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第354行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第361行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第368行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第375行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第382行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第389行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第397行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第401行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第405行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第409行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第413行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第417行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第421行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第425行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第429行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第433行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第437行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第441行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第445行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第449行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第453行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第459行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第464行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第469行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第471行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第479行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第484行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第486行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第495行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第503行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第511行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第521行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第528行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第535行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第538行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第541行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第544行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第552行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第562行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/mock_redis.py
问题数量: 67

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第37行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第80行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第84行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第130行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第139行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第141行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第147行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第156行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第159行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第162行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第164行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第174行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第187行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第194行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第199行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第204行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第212行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第215行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第219行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第221行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第227行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第231行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第235行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第239行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第243行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第247行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第251行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第255行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第266行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第271行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第276行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第278行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第281行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第283行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第286行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第293行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第298行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第304行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第309行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第314行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第316行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第319行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第321行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第324行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第331行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第336行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第341行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第346行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/unified_cache.py
问题数量: 23

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第123行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第145行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第179行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第206行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第233行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第277行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第297行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第324行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第346行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第353行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第355行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第368行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第393行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第396行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第398行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/__init__.py
问题数量: 3

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/intelligent_cache_warmup.py
问题数量: 70

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第218行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第226行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第234行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第262行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第303行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第308行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第313行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第321行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第325行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第330行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第331行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第334行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第348行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第350行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第351行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第353行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第354行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第358行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第366行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第380行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第409行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第413行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第419行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第442行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第477行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第508行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第515行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第517行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第519行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第527行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第529行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第543行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第601行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第623行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第630行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第634行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第635行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第644行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第646行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第661行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第673行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第686行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第695行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第697行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第707行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第713行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第715行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第718行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第719行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第720行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第732行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第740行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第744行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第755行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第772行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第852行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第861行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第875行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第896行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第908行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第912行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第921行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第942行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第948行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/consistency_manager.py
问题数量: 32

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第108行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第145行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第176行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第188行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第195行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第212行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第226行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第247行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第260行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第274行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第283行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第293行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第325行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第331行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第347行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第370行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第384行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第395行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第397行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第404行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第406行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第419行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第427行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第434行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第441行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第458行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/ttl_cache.py
问题数量: 2

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/api_cache.py
问题数量: 21

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第135行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第200行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第247行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第276行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第309行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第327行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第342行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第346行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第366行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第377行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第385行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第386行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第388行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第409行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/cache/multi_level_cache.py
问题数量: 6

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第114行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/redis_cluster_manager.py
问题数量: 54

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第120行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第125行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第156行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第167行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第186行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第199行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第201行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第227行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第235行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第277行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第281行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第286行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第287行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第288行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第289行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第314行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第342行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第379行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第387行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第447行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第512行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第542行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第568行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第589行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第600行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第607行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第626行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第659行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第672行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第677行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第691行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第703行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第712行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第723行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第736行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第744行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第769行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第790行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第833行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第838行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第852行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第858行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第863行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第866行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第872行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第873行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第874行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第875行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第879行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/cache/football_data_cache.py
问题数量: 43

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第78行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第78行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第99行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第160行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第160行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第185行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第202行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第244行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第247行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第247行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第264行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第281行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第302行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第323行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第344行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第372行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第386行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第397行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第413行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第432行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第451行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第471行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第487行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第501行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第515行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第548行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第564行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第585行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第594行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第600行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第606行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第612行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第618行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第626行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/examples.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/decorators.py
问题数量: 12

🟡 **第11行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第14行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第16行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/cache_consistency_manager.py
问题数量: 71

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第92行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第97行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第99行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第100行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第103行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第104行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第121行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第127行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第149行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第159行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第174行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第189行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第198行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第203行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第208行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第213行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第273行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第318行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第347行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第357行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第362行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第369行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第378行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第385行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第390行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第414行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第428行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第461行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第466行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第471行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第476行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第486行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第491行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第502行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第506行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第535行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第542行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第558行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第592行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第603行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第640行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第664行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第686行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第706行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第714行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第718行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第722行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第729行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第745行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第758行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第762行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第774行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第778行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第783行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第812行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第816行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第819行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第821行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第826行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第832行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第842行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第848行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/unified_interface.py
问题数量: 75

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第83行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第92行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第96行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第114行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第130行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第162行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第186行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第189行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第192行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第198行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第205行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第211行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第213行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第218行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第226行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第231行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第239行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第243行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第247行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第257行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第267行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第281行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第283行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第285行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第312行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第331行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第335行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第365行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第370行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第374行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第379行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第387行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第396行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第398行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第405行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第409行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第418行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第420行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第426行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第431行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第439行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第446行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第449行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第454行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第462行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第503行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第516行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第544行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第552行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第559行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第561行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第564行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第569行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第574行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第579行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第584行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第589行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/redis/__init__.py
问题数量: 24

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第76行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第129行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第141行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第165行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第186行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第197行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/cache/redis/warmup/warmup_manager.py
问题数量: 3

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/redis/core/key_manager.py
问题数量: 17

🟡 **第13行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第71行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/redis/core/connection_manager.py
问题数量: 4

🟡 **第15行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/redis/operations/sync_operations.py
问题数量: 6

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第34行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/redis/operations/async_operations.py
问题数量: 9

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第45行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/ttl_cache_enhanced/async_cache.py
问题数量: 27

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第50行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第130行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第154行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第177行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第181行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第185行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第193行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第197行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第201行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第207行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第213行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第216行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第218行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第220行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/ttl_cache_enhanced/cache_factory.py
问题数量: 12

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第125行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第143行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第161行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/ttl_cache_enhanced/__init__.py
问题数量: 4

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/ttl_cache_enhanced/ttl_cache.py
问题数量: 38

🟡 **第19行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第85行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第135行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第151行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第155行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第165行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第170行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第181行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第186行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第196行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第211行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第222行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第229行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第240行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第249行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第259行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第266行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第271行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第276行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第292行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第308行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第316行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第324行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第329行** - time_sleep
   - 描述: 检测到将同步sleep替换为异步
   - 建议: 替换为 'await asyncio.sleep(' 并确保在异步函数中调用

🟡 **第333行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第342行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第348行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第351行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第352行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第354行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/ttl_cache_enhanced/cache_entry.py
问题数量: 7

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/ttl_cache_enhanced/cache_instances.py
问题数量: 7

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第71行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/cache/cache/decorators_functions.py
问题数量: 6

🟡 **第12行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第15行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/quality/quality_protocol.py
问题数量: 5

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第201行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/quality/data_quality_monitor.py
问题数量: 21

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第83行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第139行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第207行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第288行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第306行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第335行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第342行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第355行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第403行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第426行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第467行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第482行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第516行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第519行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第540行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第558行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第577行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/quality/rules/type_rule.py
问题数量: 14

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第135行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第225行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第289行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第307行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第324行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第334行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第336行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第350行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第360行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第370行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第392行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第455行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/quality/rules/logical_relation_rule.py
问题数量: 37

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第230行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第247行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第252行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第268行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第279行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第280行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第281行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第282行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第296行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第301行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第304行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第314行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第324行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第334行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第344行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第354行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第366行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第382行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第385行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第399行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第419行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第422行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第423行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第460行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第461行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第483行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第495行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第506行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第517行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第525行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第532行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第534行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第547行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第557行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第568行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第582行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/quality/rules/range_rule.py
问题数量: 11

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第123行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第165行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第221行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第239行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第249行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第251行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第271行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第284行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第294行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第316行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/quality/rules/missing_value_rule.py
问题数量: 10

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第148行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第197行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第230行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第247行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第300行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第310行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第320行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain_simple/league.py
问题数量: 27

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第137行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第138行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第139行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第140行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第141行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第144行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第145行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第146行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第147行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第150行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第151行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第154行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第156行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第161行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain_simple/prediction.py
问题数量: 31

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第130行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第159行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第169行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第203行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第206行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第207行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第208行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第209行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第210行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第211行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第212行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第213行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第217行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第218行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第219行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第220行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第221行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第224行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第225行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第228行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第230行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第232行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第237行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第240行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain_simple/user.py
问题数量: 51

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第108行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第121行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第167行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第176行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第181行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第193行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第238行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第241行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第242行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第243行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第244行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第248行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第249行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第250行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第251行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第254行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第255行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第258行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第259行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第260行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第265行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第266行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第267行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第270行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第273行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第274行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第275行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第278行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第280行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第282行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第287行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第290行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第300行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第309行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第314行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第319行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第324行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第329行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第333行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain_simple/odds.py
问题数量: 36

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第120行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第154行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第169行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第178行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第193行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第222行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第252行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第267行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第274行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第280行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第286行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第291行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第318行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第321行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第322行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第323行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第324行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第325行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第326行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第327行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第331行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第332行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第333行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第336行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第337行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第340行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第342行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第344行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第349行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第352行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain_simple/team.py
问题数量: 29

🟡 **第13行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第189行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第193行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第205行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第235行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第238行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第239行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第240行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第241行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第242行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第243行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第247行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第248行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第249行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第252行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第253行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第256行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第258行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第263行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第266行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain_simple/rules.py
问题数量: 24

🟡 **第15行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第110行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第120行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第167行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第179行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第190行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第201行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第258行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第295行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第339行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain_simple/services.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/domain_simple/match.py
问题数量: 19

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第149行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第152行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第153行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第154行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第155行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第158行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第161行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第177行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/workflows/data_pipeline.py
问题数量: 39

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第112行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第169行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第169行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第193行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第208行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第209行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第268行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第280行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第285行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第286行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第287行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第288行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第293行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第294行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第295行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第296行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第303行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第307行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第310行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第325行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第365行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第384行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第406行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第407行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第408行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第408行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第413行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第413行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第416行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第417行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第422行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第459行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第469行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第475行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第476行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第478行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第479行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/dependencies/optional.py
问题数量: 2

🟡 **第7行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第11行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/oddsportal_integration.py
问题数量: 36

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第71行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第71行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第93行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第93行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第115行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第115行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第123行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第135行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第139行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第140行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第141行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第142行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第143行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第144行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第145行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第153行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第154行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第155行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第156行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第157行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第168行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第175行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第178行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第180行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第183行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第200行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/fotmob_api_collector.py
问题数量: 102

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第120行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第149行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第182行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第231行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第248行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第253行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第254行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第259行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第259行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第260行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第260行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第262行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第262行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第264行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第265行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第265行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第266行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第267行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第267行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第268行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第268行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第269行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第269行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第269行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第269行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第273行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第273行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第273行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第273行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第277行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第277行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第277行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第277行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第281行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第281行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第281行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第281行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第285行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第285行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第286行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第286行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第290行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第290行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第292行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第293行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第296行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第296行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第299行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第300行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第301行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第304行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第305行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第306行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第319行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第320行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第322行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第322行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第325行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第325行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第337行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第340行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第342行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第343行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第345行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第345行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第346行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第346行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第353行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第356行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第358行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第359行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第360行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第361行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第362行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第363行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第364行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第365行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第366行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第367行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第368行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第369行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第370行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第376行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第381行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第381行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第384行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第385行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第386行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第387行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第388行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第389行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第390行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第391行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第392行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第393行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第401行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第415行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第442行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第446行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/dummy_collector.py
问题数量: 12

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第53行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第54行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第55行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第135行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第197行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第233行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第276行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第296行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/match_collector.py
问题数量: 57

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第84行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第87行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第108行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第114行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第121行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第124行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第126行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第135行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第137行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第143行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第148行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第152行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第182行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第198行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第203行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第217行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第221行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第241行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第257行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第262行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第276行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第280行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第291行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第292行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第293行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第294行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第297行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第306行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第307行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第308行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第311行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第312行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第317行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第328行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第329行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第330行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第331行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第334行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第335行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第336行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第337行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第338行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第339行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第340行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第341行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第345行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第346行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第349行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第355行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第360行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/oddsportal_scraper.py
问题数量: 3

🟡 **第7行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第14行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/scores_collector.py
问题数量: 8

🟡 **第27行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第95行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第108行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第126行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/odds_collector.py
问题数量: 2

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/base_collector.py
问题数量: 19

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第123行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第202行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第210行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第219行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第227行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第230行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第238行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第242行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/collectors/enhanced_fixtures_collector.py
问题数量: 14

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第237行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第296行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第317行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第330行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第334行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第348行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第356行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第360行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第374行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第382行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/team_collector.py
问题数量: 90

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第39行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第95行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第127行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第138行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第139行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第140行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第141行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第143行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第144行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第145行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第146行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第147行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第148行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第150行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第150行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第151行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第151行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第152行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第152行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第153行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第153行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第155行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第156行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第158行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第160行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第161行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第167行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第168行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第180行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第181行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第182行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第183行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第184行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第185行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第186行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第192行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第201行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第202行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第203行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第204行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第205行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第216行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第225行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第226行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第227行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第228行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第229行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第238行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第255行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第261行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第274行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第285行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第315行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第320行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第321行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第322行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第325行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第329行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第331行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第332行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第334行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第335行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第338行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第349行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第350行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第351行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第354行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第355行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第356行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第357行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第362行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第363行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第365行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第365行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第366行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第366行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第367行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第367行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第369行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第370行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第377行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第395行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第403行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第404行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第405行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第424行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/collectors/http_client_factory.py
问题数量: 34

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第205行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第214行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第238行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第247行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第251行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第255行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第259行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第268行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第286行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第301行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第350行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第419行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第423行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第425行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第431行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第441行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第470行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第499行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第528行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第557行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第561行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第570行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第578行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第584行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/data_sources.py
问题数量: 87

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第145行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第148行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第172行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第172行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第177行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第178行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第178行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第179行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第179行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第190行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第190行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第191行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第191行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第195行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第196行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第202行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第215行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第218行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第230行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第236行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第237行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第238行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第239行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第240行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第246行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第257行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第276行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第320行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第327行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第340行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第381行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第414行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第431行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第444行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第449行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第471行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第480行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第481行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第491行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第521行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第533行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第544行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第556行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第563行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第564行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第574行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第581行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第590行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第614行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第614行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第619行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第620行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第620行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第621行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第621行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第624行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第625行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第626行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第646行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第647行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第651行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第654行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第665行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第666行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第667行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第668行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第669行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第673行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第676行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第683行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第688行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第700行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第706行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第740行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第750行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第766行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第768行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第770行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第774行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/enhanced_fotmob_collector.py
问题数量: 17

🟡 **第19行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第76行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第110行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第118行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第123行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第132行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第138行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第155行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第173行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第218行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第250行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第264行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第270行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第275行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第281行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/league_collector.py
问题数量: 70

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第39行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第100行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第115行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第147行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第148行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第149行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第150行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第152行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第154行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第154行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第155行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第155行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第156行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第156行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第157行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第157行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第159行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第160行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第166行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第167行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第179行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第180行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第181行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第182行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第183行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第189行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第208行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第209行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第210行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第211行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第217行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第217行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第218行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第218行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第219行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第219行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第222行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第222行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第223行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第223行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第225行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第226行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第227行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第228行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第229行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第230行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第231行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第232行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第233行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第235行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第236行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第237行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第250行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第261行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第274行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第310行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第324行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第338行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第357行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第369行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第398行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第413行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第414行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第419行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第434行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/rate_limiter.py
问题数量: 24

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第126行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第186行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第198行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第199行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第200行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第212行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第224行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第233行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第249行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第277行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第291行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第304行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第309行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第324行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第341行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第354行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第368行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第380行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第388行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/football_data_collector.py
问题数量: 40

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第86行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第90行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第121行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第124行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第152行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第156行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第168行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第169行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第193行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第196行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第203行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第231行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第235行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第238行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第259行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第309行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第317行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第410行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第410行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第412行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第416行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第416行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第418行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第422行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第422行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第424行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第461行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第470行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第474行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第479行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第481行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第482行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/collectors/proxy_pool.py
问题数量: 36

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第146行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第156行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第178行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第187行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第192行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第198行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第219行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第222行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第243行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第253行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第270行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第279行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第283行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第295行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第308行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第339行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第353行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第395行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第405行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第414行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第446行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第479行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第498行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第511行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第522行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第561行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第574行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第595行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第622行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第650行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第656行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第676行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/enhanced_data_collector.py
问题数量: 20

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第167行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第191行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第205行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第219行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第248行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第260行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第282行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第292行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第389行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第403行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第408行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第418行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第423行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第429行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第434行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/user_agent.py
问题数量: 10

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第185行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第238行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第264行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第277行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/html_fotmob_collector.py
问题数量: 24

🔴 **第18行** - requests_import
   - 描述: 检测到将requests导入替换为httpx
   - 建议: 替换为 'import httpx' 并确保在异步函数中调用

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第125行** - requests_get
   - 描述: 检测到将同步GET请求替换为异步
   - 建议: 替换为 'await httpx.AsyncClient().get(' 并确保在异步函数中调用

🔴 **第125行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第196行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第283行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第292行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第297行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第300行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第305行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第329行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第331行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第332行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第333行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第338行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第340行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第342行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第364行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第379行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/interface.py
问题数量: 7

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第126行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第182行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第200行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/fixtures_collector.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/fotmob/collector_v2.py
问题数量: 64

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第147行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第174行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第300行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第330行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第334行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第335行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第335行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第336行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第336行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第337行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第337行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第338行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第338行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第339行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第339行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第354行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第382行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第383行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第387行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第387行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第388行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第388行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第389行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第389行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第390行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第390行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第391行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第391行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第392行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第392行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第396行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第398行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第399行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第402行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第402行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第405行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第405行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第406行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第406行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第410行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第413行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第414行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第418行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第418行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第422行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第424行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第425行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第429行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第429行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第442行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第466行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第466行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第470行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第471行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第472行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第473行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第473行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第474行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第486行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第545行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第569行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第577行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/odds/__init__.py
问题数量: 1

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/models/team.py
问题数量: 8

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第46行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第47行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第48行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第49行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第50行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/collectors/models/match.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/auth/token_manager.py
问题数量: 39

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第146行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第200行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第222行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第277行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第287行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第289行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第317行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第329行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第351行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第382行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第404行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第408行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第441行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第463行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第486行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第495行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第539行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第548行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第557行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第577行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第591行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第595行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第604行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第619行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第632行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第640行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第659行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第672行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/collectors/collectors/scores_collector_improved_utils.py
问题数量: 1

🟡 **第7行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/config.py
问题数量: 22

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第99行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第101行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第249行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第269行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第300行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第305行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第309行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第362行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第377行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第382行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第388行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第394行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第399行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/prediction_engine.py
问题数量: 2

🟡 **第16行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/logger.py
问题数量: 3

🟡 **第16行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/service_lifecycle.py
问题数量: 17

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第177行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第207行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第227行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第260行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第263行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第265行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第270行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第284行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第300行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第322行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第351行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/exceptions.py
问题数量: 5

🟡 **第10行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第179行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第186行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/dependencies.py
问题数量: 13

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第102行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第110行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第131行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第168行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第199行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第209行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/core/auto_binding.py
问题数量: 25

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第139行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第168行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第182行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第203行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第220行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第245行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第252行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第276行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第282行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第296行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第309行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第330行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第340行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第351行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第356行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第365行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第370行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第378行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第383行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/di_setup.py
问题数量: 12

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第126行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第155行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第162行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第194行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/config_di.py
问题数量: 30

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第142行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第151行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第152行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第153行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第154行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第155行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第156行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第157行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第158行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第241行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第248行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第254行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第262行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第268行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第293行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第298行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第312行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第317行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第322行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第327行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第332行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第339行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第347行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/di.py
问题数量: 32

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第112行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第156行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第179行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第207行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第234行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第251行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第315行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第326行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第333行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第349行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第353行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第357行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第371行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第378行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第386行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第400行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第405行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第420行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第434行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第448行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第462行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第470行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第485行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第490行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第495行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第496行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/error_handler.py
问题数量: 3

🟡 **第27行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/logger_simple.py
问题数量: 1

🟡 **第8行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/path_manager.py
问题数量: 23

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第132行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第155行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第170行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第186行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第189行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第190行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第191行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第200行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第212行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第239行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第270行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第298行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第307行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第313行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/event_application.py
问题数量: 15

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第94行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第120行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第139行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第148行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第154行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/async_base.py
问题数量: 28

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第125行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第155行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第246行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第269行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第274行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第294行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第313行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第326行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第331行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第338行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第341行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第348行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第364行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第364行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第367行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第395行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第399行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第418行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第442行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/logging.py
问题数量: 12

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第114行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第130行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/prediction/data_loader.py
问题数量: 4

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/prediction/__init__.py
问题数量: 7

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/prediction/cache_manager.py
问题数量: 6

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第26行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/prediction/config/__init__.py
问题数量: 1

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/core/prediction/statistics/__init__.py
问题数量: 4

🟡 **第16行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第45行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/observers/subjects.py
问题数量: 31

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第41行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第75行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第240行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第251行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第253行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第276行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第290行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第322行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第331行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第372行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第387行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第389行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第394行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第417行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第435行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第449行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第464行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第479行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第485行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第489行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第498行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/observers/base.py
问题数量: 23

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第108行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第112行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第123行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第127行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第134行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第145行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第153行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/observers/__init__.py
问题数量: 3

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/observers/observers.py
问题数量: 40

🟡 **第27行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第66行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第67行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第68行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第90行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第112行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第154行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第206行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第215行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第241行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第245行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第264行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第274行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第300行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第305行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第317行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第349行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第368行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第377行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第398行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第410行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第430行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第448行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第451行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第473行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第483行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第485行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第486行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第492行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第500行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第536行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/observers/manager.py
问题数量: 42

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第114行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第131行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第154行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第162行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第177行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第199行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第203行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第212行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第225行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第253行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第264行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第279行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第293行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第295行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第297行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第299行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第301行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第303行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第305行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第307行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第309行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第326行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第334行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第340行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第347行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第349行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第351行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第353行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第360行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/enhanced_core.py
问题数量: 26

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第153行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第159行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第178行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第224行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第226行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第230行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第232行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第245行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第251行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第261行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第267行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第271行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第280行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/audit_service.py
问题数量: 12

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第84行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第115行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第181行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第185行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第193行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第197行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/services/data.py
问题数量: 13

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第114行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第242行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第244行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第305行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第351行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第355行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第398行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第427行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/data_quality_monitor.py
问题数量: 5

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/feature_service.py
问题数量: 9

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第210行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第269行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/data_processing.py
问题数量: 23

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第27行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第29行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第39行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第49行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第59行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第139行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第146行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第169行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第183行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第190行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第196行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第197行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第206行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第216行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/content_analysis.py
问题数量: 23

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第127行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第129行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第130行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第131行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第133行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第134行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第154行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第183行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第186行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第197行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第213行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第239行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第303行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/analytics_service.py
问题数量: 10

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第125行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第161行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第185行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第220行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第255行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第290行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第336行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第350行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/auth_service.py
问题数量: 23

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第94行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第176行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第205行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第211行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第225行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第231行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第241行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第252行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第267行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第270行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第273行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第282行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第285行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第288行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第297行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/enhanced_data_pipeline.py
问题数量: 5

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/event_prediction_service.py
问题数量: 13

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第155行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第204行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第271行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第283行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第328行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第380行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第392行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第433行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第472行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/prediction_service.py
问题数量: 40

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第57行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第59行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第59行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第79行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第79行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第146行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第161行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第161行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第202行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第217行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第221行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第222行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第249行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第261行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第267行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第271行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第288行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第308行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第318行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第337行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第354行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第385行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第404行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第433行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第450行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第451行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第452行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第453行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第454行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第461行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第482行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第504行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第513行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第530行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第548行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第566行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第585行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/data_sync_service.py
问题数量: 37

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第143行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第147行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第159行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第189行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第193行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第205行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第217行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第221行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第221行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第239行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第254行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第269行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第269行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第284行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第296行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第311行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第311行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第325行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第339行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第353行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第353行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第367行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第386行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第386行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第388行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第397行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第416行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第416行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第426行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第426行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/services/real_data.py
问题数量: 18

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第53行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第58行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第58行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第111行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第158行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第171行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第171行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第214行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第236行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第236行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/content_analysis_service.py
问题数量: 3

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/l2_data_service.py
问题数量: 14

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第75行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第162行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第178行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第209行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第219行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第225行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第236行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第249行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第262行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

### src/services/strategy_prediction_service.py
问题数量: 17

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第146行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第206行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第256行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第302行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第314行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第328行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第342行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第348行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第357行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第363行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第382行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第411行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第431行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第475行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/version.py
问题数量: 3

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/smart_data_validator.py
问题数量: 5

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/inference_service.py
问题数量: 29

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第208行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第249行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第250行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第251行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第252行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第253行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第254行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第259行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第262行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第342行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第372行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第397行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第423行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第427行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第427行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第460行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第480行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第703行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第719行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第751行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第757行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第758行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第760行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第761行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第765行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/monitoring.py
问题数量: 9

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第201行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第210行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第221行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第232行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/tenant_service.py
问题数量: 34

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第178行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第180行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第183行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第185行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第214行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第248行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第312行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第364行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第382行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第425行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第437行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第480行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第519行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第548行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第553行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第598行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第602行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第615行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第619行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第630行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第632行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第639行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第643行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第654行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第662行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第664行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第670行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第680行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第691行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第712行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/base_unified.py
问题数量: 22

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第135行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第137行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第145行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第193行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第203行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第219行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第223行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第232行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第243行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第247行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第258行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第267行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第289行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/manager.py
问题数量: 10

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第60行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第122行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/services/user_management_service.py
问题数量: 17

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第126行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第134行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第156行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第165行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第174行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第179行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第204行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第219行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第234行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第249行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第268行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第280行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第286行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/queue.py
问题数量: 3

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/user_profile.py
问题数量: 23

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第56行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第83行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第99行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第100行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第111行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第142行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第144行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第148行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第151行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第152行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第157行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第158行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第167行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/manager/manager.py
问题数量: 10

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第60行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第122行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/services/manager/data_processing/__init__.py
问题数量: 3

🟡 **第15行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/manager/base/__init__.py
问题数量: 6

🟡 **第15行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/manager/user_profile/__init__.py
问题数量: 3

🟡 **第15行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/manager/content_analysis/__init__.py
问题数量: 3

🟡 **第15行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/audit/__init__.py
问题数量: 5

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/audit_service_mod/audit_service.py
问题数量: 6

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/audit_service_mod/models.py
问题数量: 1

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/processing/processors/match_processor_fixed.py
问题数量: 25

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第129行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第130行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第131行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第132行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第133行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第134行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第135行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第136行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第137行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第138行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第155行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第181行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第185行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第186行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第192行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第205行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第221行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/processing/processors/match_processor.py
问题数量: 25

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第129行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第130行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第131行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第132行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第133行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第134行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第135行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第136行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第137行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第138行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第155行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第181行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第185行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第186行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第192行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第205行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第221行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/processing/processors/odds/transformer.py
问题数量: 1

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/processing/processors/odds/processor.py
问题数量: 1

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/processing/processors/odds/validator.py
问题数量: 1

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/processing/processors/odds/aggregator.py
问题数量: 1

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/processing/processors/features/calculator.py
问题数量: 1

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/processing/processors/features/processor.py
问题数量: 1

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/processing/processors/features/validator.py
问题数量: 1

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/processing/processors/features/aggregator.py
问题数量: 1

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/processing/validators/data_validator_fixed.py
问题数量: 20

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第67行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第121行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第170行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第193行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第213行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第222行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第223行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第233行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第247行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第259行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第303行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第316行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第331行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第353行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第388行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/processing/validators/data_validator.py
问题数量: 20

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第69行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第123行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第182行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第215行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第224行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第225行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第235行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第249行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第261行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第274行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第305行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第318行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第333行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第355行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第390行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/processing/caching/processing_cache.py
问题数量: 31

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第154行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第159行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第182行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第206行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第217行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第222行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第243行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第246行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第255行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第266行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第280行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第281行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第282行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第283行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第297行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第302行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第307行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第328行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第336行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第340行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第347行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第353行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第356行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第357行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第368行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第380行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/processing/caching/config/cache_config.py
问题数量: 3

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第59行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/services/processing/caching/base/base_cache.py
问题数量: 8

🟡 **第13行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/database/database_service.py
问题数量: 7

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第42行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/betting/enhanced_ev_calculator.py
问题数量: 35

🟡 **第165行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第176行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第308行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第320行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第330行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第353行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第372行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第397行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第416行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第457行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第479行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第493行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第593行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第607行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第620行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第643行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第683行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第728行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第775行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第786行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第841行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第852行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第924行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第937行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第971行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第987行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第990行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第1026行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第1027行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第1031行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第1032行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第1042行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第1044行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第1065行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/services/betting/ev_calculator.py
问题数量: 12

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第127行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第167行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第215行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第237行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第242行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第298行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第307行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第336行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第341行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/betting/betting_service_fixed.py
问题数量: 36

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第179行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第291行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第328行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第332行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第333行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第334行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第337行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第338行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第340行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第340行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第345行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第346行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第348行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第348行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第356行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第362行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第363行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第364行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第367行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第368行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第370行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第371行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第376行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第377行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第379行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第380行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第388行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第406行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第419行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第466行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/services/betting/betting_service.py
问题数量: 36

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第179行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第291行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第328行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第332行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第333行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第334行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第337行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第338行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第340行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第340行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第345行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第346行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第348行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第348行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第356行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第362行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第363行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第364行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第367行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第368行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第370行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第371行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第376行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第377行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第379行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第380行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第388行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第406行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第419行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第466行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/ml_ops/auto_entity_resolver.py
问题数量: 10

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第250行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第282行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第288行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第324行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data_science/simple_extract.py
问题数量: 6

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第197行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第266行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data_science/debug_columns.py
问题数量: 3

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第69行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第70行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/data_science/extract_final_score.py
问题数量: 21

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第34行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第56行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第56行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第73行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第86行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第86行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第88行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第89行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第116行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第117行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第130行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第131行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第138行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第144行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第172行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第173行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第174行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第177行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第184行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/data_science/debug_data_structure.py
问题数量: 3

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第24行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data_science/extract_real_scores.py
问题数量: 3

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第62行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第63行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/data_science/extract_features.py
问题数量: 10

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第232行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第238行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第255行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第316行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第322行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第362行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data_science/analyze_fotmob_structure.py
问题数量: 6

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第84行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第144行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第145行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第149行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/features/pipeline.py
问题数量: 13

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第126行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第153行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第196行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第251行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第265行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第283行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第316行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第334行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第361行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/features/feature_builder.py
问题数量: 14

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第83行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第204行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第343行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第363行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第445行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第487行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第531行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第532行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第584行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第589行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第620行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第649行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/features/simple_feature_calculator.py
问题数量: 16

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第43行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第44行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第127行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第199行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第242行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第277行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第307行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第374行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第399行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第465行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第520行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/features/feature_engineer.py
问题数量: 35

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第42行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第77行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第143行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第165行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第187行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第192行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第199行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第206行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第221行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第231行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第283行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第289行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第295行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第301行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第310行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第381行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第401行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第423行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第444行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第464行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第481行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第492行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/features/ewma_calculator.py
问题数量: 10

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第242行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第264行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第288行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第312行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第361行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第404行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/features/feature_store.py
问题数量: 55

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第76行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第78行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第78行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第91行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第91行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第96行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第96行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第101行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第145行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第157行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第157行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第162行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第191行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第198行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第198行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第216行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第242行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第251行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第251行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第275行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第301行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第312行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第312行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第348行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第365行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第372行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第372行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第381行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第391行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第402行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第402行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第417行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第436行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第440行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第440行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第444行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第444行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第446行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第457行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第474行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第482行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第482行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第491行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第527行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第535行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第540行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第545行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第558行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第563行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第586行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第600行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/features/feature_calculator.py
问题数量: 1

🟡 **第16行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/features/entities.py
问题数量: 7

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第101行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第121行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/features/feature_store_interface.py
问题数量: 11

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第82行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第126行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第179行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第196行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第211行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第220行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/features/feature_definitions.py
问题数量: 17

🟡 **第286行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第291行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第295行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第332行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第337行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第341行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第372行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第379行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第391行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第425行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第448行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第486行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第519行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第524行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第529行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第531行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第534行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/features/features/feature_store_processors.py
问题数量: 2

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第78行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/features/features/feature_calculator_calculators.py
问题数量: 21

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第69行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第69行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第180行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第180行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第257行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第305行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第305行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第306行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第306行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第307行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第307行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第348行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第366行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第366行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第419行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第437行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第437行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第469行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/queues/task_scheduler.py
问题数量: 29

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第84行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第87行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第90行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第91行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第149行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第186行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第200行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第222行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第230行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第263行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第299行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第305行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第332行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第356行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第385行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第394行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第406行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第416行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第426行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第431行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第448行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/queues/fifo_queue.py
问题数量: 41

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第99行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第103行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第111行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第137行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第139行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第153行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第178行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第186行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第207行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第225行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第239行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第241行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第260行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第283行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第292行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第303行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第316行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第327行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第363行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第389行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第392行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第411行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第413行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第415行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第423行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第431行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第441行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第448行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第461行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第478行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第489行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/tasks/streaming_tasks.py
问题数量: 11

🟡 **第14行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第27行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/tasks/maintenance_tasks.py
问题数量: 11

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第32行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第32行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第120行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第127行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第127行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第130行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第130行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第137行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

### src/tasks/utils.py
问题数量: 21

🟡 **第16行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第27行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第42行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第42行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第66行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第86行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第86行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第124行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第133行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第145行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第145行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第155行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第196行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第205行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第214行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第214行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第215行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第226行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第241行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/tasks/data_collection_core.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/tasks/error_logger.py
问题数量: 38

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第143行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第166行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第181行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第195行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第201行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第218行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第218行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第221行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第222行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第223行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第224行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第225行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第226行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第227行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第232行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第237行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第251行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第258行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第266行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第266行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第267行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第284行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第289行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第289行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第294行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第294行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第302行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第302行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第325行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第337行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第341行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第341行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第342行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第353行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/tasks/celery_app.py
问题数量: 8

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第58行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第253行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第255行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/tasks/monitoring.py
问题数量: 27

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第133行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第165行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第169行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第183行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第190行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第201行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第228行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第228行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第247行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第260行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第278行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第278行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第297行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第297行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第322行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第405行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第434行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第441行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第444行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第444行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第455行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/tasks/router.py
问题数量: 2

🔴 **第10行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第11行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/tasks/data_collection_tasks.py
问题数量: 46

🟡 **第18行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第104行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第126行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第182行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第225行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第262行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第295行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第331行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第346行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第346行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第366行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第367行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第368行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第371行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第372行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第380行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第381行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第385行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第388行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第390行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第391行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第393行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第394行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第396行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第396行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第398行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第399行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第400行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第403行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第406行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第407行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第424行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🔴 **第434行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第434行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第437行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第437行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第440行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第443行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第444行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第465行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

### src/tasks/pipeline_tasks.py
问题数量: 90

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第79行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第96行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第96行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第125行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第125行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第152行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第200行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第205行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第206行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第206行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第209行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第210行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第242行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第242行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第266行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第266行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第284行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第285行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第289行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第293行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第297行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第304行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第318行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第337行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第337行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第362行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第362行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第373行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第379行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第382行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第384行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第384行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第386行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第393行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第395行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第397行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第397行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第399行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第404行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第407行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第410行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第410行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第414行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第419行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第423行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第424行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第427行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第428行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第429行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第450行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第472行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第473行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第476行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第477行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第481行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第482行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第497行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第499行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第508行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第509行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第529行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第529行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第548行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第548行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第562行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第579行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第580行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第581行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第611行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第620行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第663行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第679行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第699行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第736行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第737行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第796行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第803行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第819行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第840行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第872行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第923行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第945行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第948行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第999行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第1005行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/evaluation/visualizer.py
问题数量: 14

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第255行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第348行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第500行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第517行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第518行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第519行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第520行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第562行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第633行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第698行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/evaluation/calibration.py
问题数量: 27

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第112行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第146行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第182行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第197行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第241行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第279行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第294行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第318行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第321行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第324行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第327行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第352行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第379行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第392行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第496行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第506行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第527行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第533行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第549行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第567行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/evaluation/backtest.py
问题数量: 49

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第121行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第149行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第166行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第174行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第187行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第234行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第247行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第283行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第299行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第316行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第340行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第370行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第449行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第494行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第494行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第495行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第495行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第496行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第496行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第501行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第501行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第502行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第502行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第503行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第503行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第516行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第516行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第521行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第521行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第553行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第651行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第673行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第688行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第721行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第736行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第781行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第805行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第807行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第810行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第811行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第812行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第816行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第817行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第818行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/evaluation/metrics.py
问题数量: 10

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第156行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第237行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第342行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第368行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第413行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第424行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/evaluation/report_builder.py
问题数量: 13

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第401行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第420行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第429行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第482行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第487行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第527行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第595行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第645行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第678行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第739行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/evaluation/flows/backtest_flow.py
问题数量: 22

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第253行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第257行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第261行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第262行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第263行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第271行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第272行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第273行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第292行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第334行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第401行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第430行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第483行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第594行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/evaluation/flows/eval_flow.py
问题数量: 15

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第167行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第198行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第224行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第264行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第327行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第383行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第495行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第496行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第502行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/quality_dashboard/api/main.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/storage/lake.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/processing/missing_data_handler.py
问题数量: 18

🟡 **第22行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第88行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第112行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第161行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第174行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第203行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第225行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第253行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第293行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第301行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第311行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第313行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第320行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第325行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第336行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/processing/data_preprocessor.py
问题数量: 15

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第27行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第216行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第267行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第284行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第292行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第296行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第300行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第304行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第324行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第357行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/processing/football_data_cleaner.py
问题数量: 61

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第108行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第149行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第177行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第190行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第256行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第272行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第297行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第322行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第375行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第393行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第397行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第417行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第418行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第419行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第420行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第421行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第421行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第422行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第423行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第427行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第429行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第432行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第433行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第434行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第447行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第451行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第452行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第453行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第458行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第462行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第463行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第464行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第469行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第473行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第474行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第475行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第480行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第483行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第486行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第486行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第498行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第526行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第540行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第541行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第542行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第547行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第548行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第549行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第555行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第565行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第566行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第571行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第575行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第579行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第585行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/processing/football_data_cleaner_mod/__init__.py
问题数量: 2

🟡 **第7行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第11行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/processors/match_parser.py
问题数量: 27

🟡 **第32行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第199行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第291行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第305行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第309行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第313行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第318行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第319行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第320行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第321行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第322行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第323行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第324行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第325行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第335行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第336行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第337行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第341行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第346行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第354行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第366行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第378行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第394行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第414行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/quality/data_quality_monitor.py
问题数量: 38

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第67行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第118行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第144行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第148行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第148行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第181行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第185行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第185行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第214行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第226行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第232行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第232行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第283行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第289行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第289行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第327行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第333行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第333行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第362行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第388行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第391行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第394行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第416行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第421行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第423行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第427行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第429行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第431行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第439行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第441行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第443行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第445行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第450行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第456行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第460行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/data/quality/great_expectations_config.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/quality/anomaly_detector.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/quality/prometheus.py
问题数量: 6

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第29行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第47行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/quality/exception_handler.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/quality/exception_handler_mod/__init__.py
问题数量: 2

🟡 **第7行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第11行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/fbref_collector.py
问题数量: 32

🔴 **第21行** - requests_import
   - 描述: 检测到将requests导入替换为httpx
   - 建议: 替换为 'import httpx' 并确保在异步函数中调用

🔴 **第21行** - curl_cffi_import
   - 描述: 检测到将curl_cffi导入替换为httpx
   - 建议: 替换为 'import httpx' 并确保在异步函数中调用

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第63行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第88行** - requests_session
   - 描述: 检测到将同步Session替换为异步Client
   - 建议: 替换为 'httpx.AsyncClient(' 并确保在异步函数中调用

🔴 **第98行** - requests_session
   - 描述: 检测到将同步Session替换为异步Client
   - 建议: 替换为 'httpx.AsyncClient(' 并确保在异步函数中调用

🟡 **第108行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第112行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第207行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第271行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第325行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第333行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第401行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第453行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第502行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第560行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第577行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第583行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第592行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第651行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第723行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第873行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第898行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第944行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第997行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1006行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1030行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1182行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第1214行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/fbref_details_collector.py
问题数量: 18

🔴 **第19行** - requests_import
   - 描述: 检测到将requests导入替换为httpx
   - 建议: 替换为 'import httpx' 并确保在异步函数中调用

🔴 **第19行** - curl_cffi_import
   - 描述: 检测到将curl_cffi导入替换为httpx
   - 建议: 替换为 'import httpx' 并确保在异步函数中调用

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第72行** - requests_session
   - 描述: 检测到将同步Session替换为异步Client
   - 建议: 替换为 'httpx.AsyncClient(' 并确保在异步函数中调用

🟡 **第80行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第213行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第275行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第354行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第405行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第437行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第470行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第492行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第524行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第532行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/scores_collector.py
问题数量: 141

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第116行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第135行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第186行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第205行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第221行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第230行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第232行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第233行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第236行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第238行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第238行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第239行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第239行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第240行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第240行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第241行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第242行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第243行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第244行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第245行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第248行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第248行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第249行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第249行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第250行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第250行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第251行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第252行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第253行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第254行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第257行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第257行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第258行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第258行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第259行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第259行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第266行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第268行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第273行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第275行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第275行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第276行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第276行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第278行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第280行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第280行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第281行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第281行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第284行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第284行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第285行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第285行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第289行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第289行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第290行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第290行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第292行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第295行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第296行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第302行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第302行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第308行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第310行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第311行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第313行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第316行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第317行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第320行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第323行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第323行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第324行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第324行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第325行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第325行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第327行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第329行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第329行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第330行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第330行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第331行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第331行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第333行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第334行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第335行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第336行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第337行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第338行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第339行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第347行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第349行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第351行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第353行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第354行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第355行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第358行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第360行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第362行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第362行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第363行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第363行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第370行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第372行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第373行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第374行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第375行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第376行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第381行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第383行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第384行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第385行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第386行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第395行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第406行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第423行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第423行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第432行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第432行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第433行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第433行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第438行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第457行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第468行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第477行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第478行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第478行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第479行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第479行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第481行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第481行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第481行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第484行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第484行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第484行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第488行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第489行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第513行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/odds_collector.py
问题数量: 16

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第73行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第100行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第134行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第146行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第186行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第198行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第206行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第211行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第231行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第272行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

🟡 **第284行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第303行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第324行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/fbref_team_collector.py
问题数量: 14

🔴 **第30行** - requests_import
   - 描述: 检测到将requests导入替换为httpx
   - 建议: 替换为 'import httpx' 并确保在异步函数中调用

🔴 **第30行** - curl_cffi_import
   - 描述: 检测到将curl_cffi导入替换为httpx
   - 建议: 替换为 'import httpx' 并确保在异步函数中调用

🟡 **第52行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第55行** - requests_session
   - 描述: 检测到将同步Session替换为异步Client
   - 建议: 替换为 'httpx.AsyncClient(' 并确保在异步函数中调用

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第128行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第264行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第277行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第301行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第312行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第397行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第436行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第469行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/base_collector.py
问题数量: 9

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第33行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第34行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第123行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第130行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/fotmob_details_collector.py
问题数量: 203

🟡 **第127行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第160行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第199行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第219行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第223行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第233行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第244行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第271行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第323行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第365行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第368行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第368行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第372行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第375行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第377行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第377行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第378行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第378行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第379行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第379行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第380行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第380行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第381行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第382行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第382行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第383行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第383行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第389行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第406行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第406行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第408行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第409行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第416行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第419行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第420行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第423行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第428行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第429行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第430行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第431行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第432行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第437行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第445行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第445行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第446行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第451行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第452行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第453行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第454行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第455行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第456行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第457行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第458行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第459行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第468行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第480行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第481行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第488行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第489行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第515行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第523行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第523行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第524行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第528行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第529行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第534行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第535行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第546行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第550行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第555行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第598行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第603行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第604行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第612行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第613行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第614行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第615行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第616行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第617行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第626行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第630行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第637行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第638行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第641行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第642行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第643行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第644行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第657行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第664行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第665行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第669行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第670行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第671行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第672行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第681行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第692行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第693行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第698行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第699行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第706行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第707行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第718行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第725行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第741行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第750行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第766行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第766行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第767行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第767行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第771行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第772行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第775行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第776行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第784行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第787行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第788行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第792行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第799行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第801行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第803行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第807行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第810行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第814行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第815行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第815行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第816行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第816行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第820行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第821行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第822行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第823行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第824行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第825行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第826行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第827行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第828行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第829行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第830行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第831行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第832行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第833行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第834行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第835行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第836行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第846行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第851行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第851行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第851行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第856行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第857行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第860行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第861行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第862行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第863行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第864行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第865行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第871行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第871行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第874行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第875行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第876行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第877行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第878行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第889行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第894行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第894行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第895行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第898行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第898行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第899行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第899行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第900行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第901行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第902行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第903行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第904行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第905行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第913行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第918行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第918行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第919行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第919行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第920行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第920行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第937行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第944行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第948行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第949行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第951行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第951行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第952行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第953行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第954行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第955行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第955行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第956行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第956行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第957行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第957行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第958行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第968行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第977行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/fbref_collector_stealth.py
问题数量: 13

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第70行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第74行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第303行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第342行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第377行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第388行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第415行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第427行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/fotmob_browser_v2.py
问题数量: 23

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第92行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第101行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第136行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第149行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第216行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第296行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第332行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第335行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第377行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第422行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第487行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第498行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第509行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第520行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第530行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第540行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第558行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第564行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第600行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/fbref_collector_pure.py
问题数量: 16

🔴 **第19行** - requests_import
   - 描述: 检测到将requests导入替换为httpx
   - 建议: 替换为 'import httpx' 并确保在异步函数中调用

🔴 **第19行** - curl_cffi_import
   - 描述: 检测到将curl_cffi导入替换为httpx
   - 建议: 替换为 'import httpx' 并确保在异步函数中调用

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第75行** - requests_session
   - 描述: 检测到将同步Session替换为异步Client
   - 建议: 替换为 'httpx.AsyncClient(' 并确保在异步函数中调用

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第95行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第191行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第226行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第288行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第344行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第416行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第435行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第485行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/fotmob_match_collector.py
问题数量: 10

🟡 **第17行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第61行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第121行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第161行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第225行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第264行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第303行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第345行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第351行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/fotmob_details_browser.py
问题数量: 25

🟡 **第38行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第99行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第112行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第183行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第221行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第251行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第258行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第289行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第349行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第356行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第390行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第426行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第436行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第476行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第483行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第533行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第539行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第574行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第587行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第607行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第637行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第644行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/fotmob_universal_collector.py
问题数量: 25

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第83行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第90行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第145行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第256行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第321行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第328行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第349行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第372行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第395行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第423行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第454行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第488行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第514行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第545行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第570行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第600行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第604行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🟡 **第611行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第617行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第658行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/fbref_team_history_collector.py
问题数量: 12

🟡 **第25行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第39行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第67行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第100行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第125行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第208行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第253行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第361行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第391行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第462行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第491行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第499行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/fotmob_collector.py
问题数量: 36

🟡 **第35行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第53行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第64行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第72行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第95行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第173行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第197行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第235行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第235行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第257行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第270行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第271行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第271行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第272行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第272行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第273行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第274行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第275行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第275行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第276行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第277行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第277行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第278行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第278行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第282行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第313行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第335行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第356行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第356行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第381行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第411行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第443行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第449行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第452行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/fotmob_browser_fixed.py
问题数量: 10

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第46行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第92行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第232行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第336行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第347行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/fotmob_browser.py
问题数量: 17

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第64行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第105行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第118行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第284行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第293行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第322行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第328行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第445行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第451行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第515行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第534行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第552行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第594行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/collectors/fixtures_collector.py
问题数量: 64

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第81行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第83行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第83行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第99行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第157行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第161行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第165行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第167行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第181行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第183行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第185行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第192行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第195行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第197行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第200行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第202行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第208行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第211行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第213行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第216行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第218行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第223行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第226行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第233行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第236行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第243行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第245行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第246行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第256行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第262行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第263行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第265行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第266行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第280行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第447行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第500行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第505行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第562行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第573行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第584行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第608行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第619行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第620行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第620行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第621行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第621行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第622行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第628行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第654行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第654行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第659行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第660行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第660行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第661行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第673行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第691行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第706行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第718行** - session_execute
   - 描述: 检测到数据库操作添加await
   - 建议: 替换为 'await session.execute(' 并确保在异步函数中调用

🔴 **第718行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第742行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第747行** - session_commit
   - 描述: 检测到数据库提交添加await
   - 建议: 替换为 'await session.commit(' 并确保在异步函数中调用

### src/data/features/feature_store.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/features/examples.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/data/features/feature_definitions.py
问题数量: 3

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/lineage/lineage_reporter.py
问题数量: 15

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第117行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第118行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第153行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第176行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第184行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第185行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第239行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第255行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第293行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第320行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第358行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第421行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第429行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/pipeline/config.py
问题数量: 1

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/pipeline/model_registry.py
问题数量: 18

🟡 **第41行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第57行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第121行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第164行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第167行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第170行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第180行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第185行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第208行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第240行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第295行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第306行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第326行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第342行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第351行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第376行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第409行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第417行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/pipeline/trainer.py
问题数量: 13

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第178行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第244行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第248行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第252行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第256行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第294行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第307行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第316行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第316行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第316行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/pipeline/monitoring.py
问题数量: 29

🟡 **第49行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第54行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第109行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第121行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第143行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第165行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第179行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第206行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第229行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第233行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第239行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第240行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第241行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第242行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第253行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第266行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第302行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第310行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第322行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第341行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第346行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/pipeline/feature_loader.py
问题数量: 15

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第120行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第161行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第191行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第224行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第244行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第261行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第275行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第303行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第322行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第342行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第353行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第367行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第382行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/pipeline/flows/train_flow.py
问题数量: 6

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第126行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第198行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第217行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/pipeline/flows/eval_flow.py
问题数量: 10

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第176行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第234行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第274行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第302行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第338行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第356行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/pipeline/evaluators/metrics_calculator.py
问题数量: 8

🟡 **第34行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第106行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第172行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第194行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第225行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第244行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第255行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/scheduler/job_manager.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/events/base.py
问题数量: 33

🟡 **第28行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第43行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第55行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第66行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第76行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第81行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第86行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第91行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第96行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第110行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第119行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第132行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第143行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第155行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第163行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第171行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第175行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第182行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第191行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第199行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第210行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第216行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第222行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第240行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第254行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第264行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第271行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第281行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第288行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第303行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/events/__init__.py
问题数量: 1

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/events/bus.py
问题数量: 28

🟡 **第21行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第33行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第48行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第59行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第68行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第102行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第123行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第129行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第134行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第138行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第144行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第244行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第336行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第342行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第375行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第385行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第392行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第408行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第415行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第437行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第446行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第474行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第493行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第501行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第507行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/events/handlers.py
问题数量: 39

🟡 **第30行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第40行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第45行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第51行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第56行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第65行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第94行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第117行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第127行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第135行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第141行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第177行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第186行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第194行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第201行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第213行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第233行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第243行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第250行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第254行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第269行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第280行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第292行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第301行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第333行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第342行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第351行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第356行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第363行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第371行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第385行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第394行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第398行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第403行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第410行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/events/types.py
问题数量: 76

🟡 **第19行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第45行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第71行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第98行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第152行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第183行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第201行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第228行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第259行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第265行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第268行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第289行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第291行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第293行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第294行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第295行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第301行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第302行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第303行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第304行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第305行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第313行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第319行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第322行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第343行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第345行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第347行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第348行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第349行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第355行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第356行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第357行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第358行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第359行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第367行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第373行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第376行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第396行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第398行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第400行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第401行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第402行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第409行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第410行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第411行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第419行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第425行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第428行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第448行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第450行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第452行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第453行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第454行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第461行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第462行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第463行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第471行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第477行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第480行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第498行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第500行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第502行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第503行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第504行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第509行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第510行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第511行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第519行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第525行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第528行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第549行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第551行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第553行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第554行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第555行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/metrics/advanced_analyzer.py
问题数量: 2

🟡 **第5行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第9行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/metrics/quality_integration.py
问题数量: 46

🟡 **第24行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第31行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第65行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第69行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第69行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第75行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第79行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第93行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第100行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第100行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第103行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第106行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第109行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第112行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第113行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第114行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第118行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第121行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第122行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第123行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第124行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第125行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第126行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第130行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第132行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第134行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第135行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第135行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第136行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第136行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第137行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第145行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第150行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第151行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第160行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第171行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第180行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第190行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第191行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第200行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第212行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第221行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第243行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第251行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

### src/security/rbac_system.py
问题数量: 3

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/security/middleware.py
问题数量: 27

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第44行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第62行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第79行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第87行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第107行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第110行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第115行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第131行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第151行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第158行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第184行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第209行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第216行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第219行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第230行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第241行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第244行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第253行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第260行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第283行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第294行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第340行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第345行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第392行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第413行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/security/key_manager.py
问题数量: 16

🟡 **第23行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第37行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第60行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第75行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第83行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第97行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第113行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第129行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第140行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第150行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第165行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第178行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第183行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第188行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第193行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/security/encryption_service.py
问题数量: 3

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/security/advanced_auth.py
问题数量: 3

🟡 **第20行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第26行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第36行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

### src/security/jwt_auth.py
问题数量: 32

🟡 **第50行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第85行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第89行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第122行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第153行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第170行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第174行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第178行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第179行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第180行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第181行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第182行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第183行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第184行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第203行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第223行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第242行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第265行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第271行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第285行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第300行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第331行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第348行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第369行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第386行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第410行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🔴 **第424行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🔴 **第425行** - missing_await
   - 描述: 异步函数调用缺少await关键字
   - 建议: 在函数调用前添加'await '

🟡 **第440行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第445行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第483行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'

🟡 **第491行** - def_to_async
   - 描述: 检测到将函数定义转换为异步
   - 建议: 将 'def' 改为 'async def'
