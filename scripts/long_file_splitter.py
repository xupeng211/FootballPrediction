#!/usr/bin/env python3
"""
长文件智能拆分工具 - Issue #87
基于AST分析和业务逻辑的智能文件拆分
"""

import os
import ast
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
import shutil

class LongFileSplitter:
    """长文件智能拆分器"""

    def __init__(self):
        self.critical_files = [
            "src/monitoring/anomaly_detector.py",
            "src/performance/analyzer.py",
            "src/scheduler/recovery_handler.py",
            "src/features/feature_store.py",
            "src/collectors/scores_collector_improved.py",
            "src/database/migrations/versions/d6d814cc1078_database_performance_optimization_.py",
            "src/domain/strategies/historical.py",
            "src/cache/decorators.py",
            "src/domain/strategies/ensemble.py",
            "src/facades/facades.py",
            "src/domain/strategies/config.py",
            "src/decorators/decorators.py",
            "src/adapters/football.py",
            "src/api/adapters.py",
            "src/api/facades.py",
            "src/features/feature_calculator.py",
            "src/patterns/facade.py"
        ]

    def analyze_file_for_splitting(self, file_path: str) -> Dict:
        """分析文件以确定拆分策略"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            # 分析文件结构
            classes = []
            functions = []
            imports = []
            constants = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = self._analyze_class(node, content)
                    classes.append(class_info)
                elif isinstance(node, ast.FunctionDef):
                    func_info = self._analyze_function(node, content)
                    # 只包含不在类中的函数
                    if not any(cls['line_start'] <= node.lineno <= cls['line_end'] for cls in classes):
                        functions.append(func_info)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.append(self._analyze_import(node))
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            constants.append({
                                'name': target.id,
                                'line': node.lineno,
                                'value': ast.unparse(node.value) if hasattr(ast, 'unparse') else str(node.value)
                            })

            # 生成拆分策略
            split_strategy = self._generate_split_strategy(
                file_path, classes, functions, imports, constants, content
            )

            return {
                'path': file_path,
                'content': content,
                'classes': classes,
                'functions': functions,
                'imports': imports,
                'constants': constants,
                'split_strategy': split_strategy
            }

        except Exception as e:
            return {'error': str(e), 'path': file_path}

    def _analyze_class(self, node: ast.ClassDef, content: str) -> Dict:
        """分析类结构"""
        methods = []
        properties = []
        inner_classes = []

        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                methods.append({
                    'name': child.name,
                    'line_start': child.lineno,
                    'line_end': self._get_end_line(child, content),
                    'is_private': child.name.startswith('_'),
                    'is_dunder': child.name.startswith('__'),
                    'args': [arg.arg for arg in child.args.args],
                    'decorators': [ast.unparse(d) if hasattr(ast, 'unparse') else str(d) for d in child.decorator_list],
                    'complexity': self._calculate_complexity(child)
                })
            elif isinstance(child, ast.ClassDef):
                inner_classes.append({
                    'name': child.name,
                    'line_start': child.lineno,
                    'line_end': self._get_end_line(child, content)
                })
            elif isinstance(child, ast.AnnAssign):
                # 类型注解的属性
                if isinstance(child.target, ast.Name):
                    properties.append({
                        'name': child.target.id,
                        'line': child.lineno,
                        'annotation': ast.unparse(child.annotation) if hasattr(ast, 'unparse') else str(child.annotation)
                    })

        return {
            'name': node.name,
            'line_start': node.lineno,
            'line_end': self._get_end_line(node, content),
            'bases': [self._get_base_name(base) for base in node.bases],
            'methods': methods,
            'properties': properties,
            'inner_classes': inner_classes,
            'docstring': ast.get_docstring(node),
            'complexity': sum(m['complexity'] for m in methods)
        }

    def _analyze_function(self, node: ast.FunctionDef, content: str) -> Dict:
        """分析函数结构"""
        return {
            'name': node.name,
            'line_start': node.lineno,
            'line_end': self._get_end_line(node, content),
            'args': [arg.arg for arg in node.args.args],
            'decorators': [ast.unparse(d) if hasattr(ast, 'unparse') else str(d) for d in node.decorator_list],
            'docstring': ast.get_docstring(node),
            'complexity': self._calculate_complexity(node),
            'is_private': node.name.startswith('_'),
            'is_dunder': node.name.startswith('__')
        }

    def _analyze_import(self, node) -> Dict:
        """分析导入语句"""
        if isinstance(node, ast.Import):
            return {
                'type': 'import',
                'line': node.lineno,
                'names': [alias.name for alias in node.names],
                'aliases': {alias.asname: alias.name for alias in node.names if alias.asname}
            }
        else:  # ImportFrom
            return {
                'type': 'from_import',
                'line': node.lineno,
                'module': node.module,
                'names': [alias.name for alias in node.names],
                'is_star': any(alias.name == '*' for alias in node.names)
            }

    def _get_base_name(self, base) -> str:
        """获取基类名称"""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return ast.unparse(base) if hasattr(ast, 'unparse') else str(base)
        else:
            return str(base)

    def _get_end_line(self, node, content: str) -> int:
        """获取节点结束行号"""
        if hasattr(node, 'end_lineno') and node.end_lineno:
            return node.end_lineno

        content.split('\n')
        max_line = node.lineno

        for child in ast.walk(node):
            if hasattr(child, 'lineno') and child.lineno > max_line:
                max_line = child.lineno

        return max_line

    def _calculate_complexity(self, node) -> int:
        """计算复杂度"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.ListComp):
                complexity += 1
            elif isinstance(child, ast.DictComp):
                complexity += 1
        return complexity

    def _generate_split_strategy(self, file_path: str, classes: List[Dict],
                               functions: List[Dict], imports: List[Dict],
                               constants: List[Dict], content: str) -> Dict:
        """生成拆分策略"""
        strategy = {
            'method': 'unknown',
            'files': [],
            'reasoning': []
        }

        # 根据文件路径和内容特征确定拆分策略
        if 'monitoring' in file_path:
            strategy = self._generate_monitoring_split_strategy(
                file_path, classes, functions, imports, constants
            )
        elif 'strategies' in file_path:
            strategy = self._generate_strategies_split_strategy(
                file_path, classes, functions, imports, constants
            )
        elif 'decorators' in file_path:
            strategy = self._generate_decorators_split_strategy(
                file_path, classes, functions, imports, constants
            )
        elif 'facades' in file_path:
            strategy = self._generate_facades_split_strategy(
                file_path, classes, functions, imports, constants
            )
        elif 'features' in file_path:
            strategy = self._generate_features_split_strategy(
                file_path, classes, functions, imports, constants
            )
        elif 'api' in file_path:
            strategy = self._generate_api_split_strategy(
                file_path, classes, functions, imports, constants
            )
        else:
            strategy = self._generate_general_split_strategy(
                file_path, classes, functions, imports, constants
            )

        return strategy

    def _generate_monitoring_split_strategy(self, file_path: str, classes: List[Dict],
                                           functions: List[Dict], imports: List[Dict],
                                           constants: List[Dict]) -> Dict:
        """生成监控模块拆分策略"""
        files = []

        # 按监控类型分组
        anomaly_detection = []
        performance_monitoring = []
        metrics_collection = []
        alert_management = []
        health_checks = []

        for cls in classes:
            if any(keyword in cls['name'].lower() for keyword in ['anomaly', 'detector', 'detection']):
                anomaly_detection.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['performance', 'analyzer', 'profiler']):
                performance_monitoring.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['metric', 'exporter', 'collector']):
                metrics_collection.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['alert', 'manager']):
                alert_management.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['health', 'check']):
                health_checks.append(cls)

        # 创建文件
        base_name = file_path.replace('.py', '').replace('src/', '')

        if anomaly_detection:
            files.append({
                'name': f"{base_name}_anomaly_detection.py",
                'classes': anomaly_detection,
                'functions': [],
                'description': '异常检测相关功能'
            })

        if performance_monitoring:
            files.append({
                'name': f"{base_name}_performance.py",
                'classes': performance_monitoring,
                'functions': [],
                'description': '性能监控相关功能'
            })

        if metrics_collection:
            files.append({
                'name': f"{base_name}_metrics.py",
                'classes': metrics_collection,
                'functions': [],
                'description': '指标收集相关功能'
            })

        if alert_management:
            files.append({
                'name': f"{base_name}_alerts.py",
                'classes': alert_management,
                'functions': [],
                'description': '告警管理相关功能'
            })

        # 独立函数和常量
        if functions:
            files.append({
                'name': f"{base_name}_utils.py",
                'classes': [],
                'functions': functions,
                'description': '监控工具函数'
            })

        return {
            'method': 'domain_split',
            'files': files,
            'reasoning': ['监控模块按功能类型拆分：异常检测、性能监控、指标收集、告警管理']
        }

    def _generate_strategies_split_strategy(self, file_path: str, classes: List[Dict],
                                            functions: List[Dict], imports: List[Dict],
                                            constants: List[Dict]) -> Dict:
        """生成策略模块拆分策略"""
        files = []

        # 按策略类型分组
        historical = []
        ml_model = []
        statistical = []
        ensemble = []
        config = []
        factory = []

        for cls in classes:
            if any(keyword in cls['name'].lower() for keyword in ['historical', 'history']):
                historical.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['ml', 'model', 'machine']):
                ml_model.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['statistical', 'stats']):
                statistical.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['ensemble']):
                ensemble.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['config', 'configuration']):
                config.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['factory']):
                factory.append(cls)

        base_name = file_path.replace('.py', '').replace('src/', '')

        if historical:
            files.append({
                'name': f"{base_name}_historical.py",
                'classes': historical,
                'functions': [],
                'description': '历史数据策略'
            })

        if ml_model:
            files.append({
                'name': f"{base_name}_ml.py",
                'classes': ml_model,
                'functions': [],
                'description': '机器学习策略'
            })

        if statistical:
            files.append({
                'name': f"{base_name}_statistical.py",
                'classes': statistical,
                'functions': [],
                'description': '统计分析策略'
            })

        if ensemble:
            files.append({
                'name': f"{base_name}_ensemble.py",
                'classes': ensemble,
                'functions': [],
                'description': '集成策略'
            })

        return {
            'method': 'strategy_split',
            'files': files,
            'reasoning': ['策略模块按算法类型拆分：历史策略、ML策略、统计策略、集成策略']
        }

    def _generate_decorators_split_strategy(self, file_path: str, classes: List[Dict],
                                            functions: List[Dict], imports: List[Dict],
                                            constants: List[Dict]) -> Dict:
        """生成装饰器模块拆分策略"""
        files = []

        # 按功能分组
        cache_decorators = []
        logging_decorators = []
        validation_decorators = []
        monitoring_decorators = []
        performance_decorators = []

        for cls in classes:
            if any(keyword in cls['name'].lower() for keyword in ['cache', 'ttl']):
                cache_decorators.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['log', 'logging']):
                logging_decorators.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['valid', 'validate']):
                validation_decorators.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['monitor', 'metrics']):
                monitoring_decorators.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['performance', 'timing']):
                performance_decorators.append(cls)

        # 函数式装饰器
        function_decorators = [f for f in functions if 'decorator' in f['name'].lower()]

        base_name = file_path.replace('.py', '').replace('src/', '')

        if cache_decorators:
            files.append({
                'name': f"{base_name}_cache.py",
                'classes': cache_decorators,
                'functions': [],
                'description': '缓存装饰器'
            })

        if logging_decorators:
            files.append({
                'name': f"{base_name}_logging.py",
                'classes': logging_decorators,
                'functions': [],
                'description': '日志装饰器'
            })

        if validation_decorators:
            files.append({
                'name': f"{base_name}_validation.py",
                'classes': validation_decorators,
                'functions': [],
                'description': '验证装饰器'
            })

        if monitoring_decorators:
            files.append({
                'name': f"{base_name}_monitoring.py",
                'classes': monitoring_decorators,
                'functions': [],
                'description': '监控装饰器'
            })

        if function_decorators:
            files.append({
                'name': f"{base_name}_functions.py",
                'classes': [],
                'functions': function_decorators,
                'description': '函数式装饰器'
            })

        return {
            'method': 'functional_split',
            'files': files,
            'reasoning': ['装饰器模块按功能类型拆分：缓存、日志、验证、监控、性能']
        }

    def _generate_facades_split_strategy(self, file_path: str, classes: List[Dict],
                                         functions: List[Dict], imports: List[Dict],
                                         constants: List[Dict]) -> Dict:
        """生成门面模块拆分策略"""
        files = []

        # 按业务领域分组
        user_facades = []
        prediction_facades = []
        match_facades = []
        data_facades = []
        system_facades = []

        for cls in classes:
            if any(keyword in cls['name'].lower() for keyword in ['user', 'account']):
                user_facades.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['prediction', 'forecast']):
                prediction_facades.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['match', 'game']):
                match_facades.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['data', 'collection']):
                data_facades.append(cls)
            else:
                system_facades.append(cls)

        base_name = file_path.replace('.py', '').replace('src/', '')

        if user_facades:
            files.append({
                'name': f"{base_name}_user.py",
                'classes': user_facades,
                'functions': [],
                'description': '用户门面'
            })

        if prediction_facades:
            files.append({
                'name': f"{base_name}_prediction.py",
                'classes': prediction_facades,
                'functions': [],
                'description': '预测门面'
            })

        if match_facades:
            files.append({
                'name': f"{base_name}_match.py",
                'classes': match_facades,
                'functions': [],
                'description': '比赛门面'
            })

        if data_facades:
            files.append({
                'name': f"{base_name}_data.py",
                'classes': data_facades,
                'functions': [],
                'description': '数据门面'
            })

        if system_facades:
            files.append({
                'name': f"{base_name}_system.py",
                'classes': system_facades,
                'functions': [],
                'description': '系统门面'
            })

        return {
            'method': 'domain_split',
            'files': files,
            'reasoning': ['门面模块按业务领域拆分：用户、预测、比赛、数据、系统']
        }

    def _generate_features_split_strategy(self, file_path: str, classes: List[Dict],
                                          functions: List[Dict], imports: List[Dict],
                                          constants: List[Dict]) -> Dict:
        """生成特征模块拆分策略"""
        files = []

        # 按特征类型分组
        feature_calculators = []
        feature_stores = []
        feature_definitions = []
        feature_processors = []

        for cls in classes:
            if any(keyword in cls['name'].lower() for keyword in ['calculator', 'calc']):
                feature_calculators.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['store', 'storage']):
                feature_stores.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['definition', 'def']):
                feature_definitions.append(cls)
            else:
                feature_processors.append(cls)

        base_name = file_path.replace('.py', '').replace('src/', '')

        if feature_definitions:
            files.append({
                'name': f"{base_name}_definitions.py",
                'classes': feature_definitions,
                'functions': [],
                'description': '特征定义'
            })

        if feature_calculators:
            files.append({
                'name': f"{base_name}_calculators.py",
                'classes': feature_calculators,
                'functions': [],
                'description': '特征计算器'
            })

        if feature_stores:
            files.append({
                'name': f"{base_name}_stores.py",
                'classes': feature_stores,
                'functions': [],
                'description': '特征存储'
            })

        if feature_processors:
            files.append({
                'name': f"{base_name}_processors.py",
                'classes': feature_processors,
                'functions': [],
                'description': '特征处理器'
            })

        return {
            'method': 'component_split',
            'files': files,
            'reasoning': ['特征模块按组件类型拆分：定义、计算器、存储、处理器']
        }

    def _generate_api_split_strategy(self, file_path: str, classes: List[Dict],
                                    functions: List[Dict], imports: List[Dict],
                                    constants: List[Dict]) -> Dict:
        """生成API模块拆分策略"""
        files = []

        # 按API功能分组
        routers = []
        adapters = []
        facades = []
        middleware = []
        models = []

        for cls in classes:
            if any(keyword in cls['name'].lower() for keyword in ['router', 'route']):
                routers.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['adapter']):
                adapters.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['facade']):
                facades.append(cls)
            elif any(keyword in cls['name'].lower() for keyword in ['middleware']):
                middleware.append(cls)
            else:
                models.append(cls)

        base_name = file_path.replace('.py', '').replace('src/', '')

        if routers:
            files.append({
                'name': f"{base_name}_routers.py",
                'classes': routers,
                'functions': [],
                'description': 'API路由'
            })

        if adapters:
            files.append({
                'name': f"{base_name}_adapters.py",
                'classes': adapters,
                'functions': [],
                'description': 'API适配器'
            })

        if facades:
            files.append({
                'name': f"{base_name}_facades.py",
                'classes': facades,
                'functions': [],
                'description': 'API门面'
            })

        if middleware:
            files.append({
                'name': f"{base_name}_middleware.py",
                'classes': middleware,
                'functions': [],
                'description': 'API中间件'
            })

        return {
            'method': 'api_split',
            'files': files,
            'reasoning': ['API模块按功能类型拆分：路由、适配器、门面、中间件']
        }

    def _generate_general_split_strategy(self, file_path: str, classes: List[Dict],
                                         functions: List[Dict], imports: List[Dict],
                                         constants: List[Dict]) -> Dict:
        """生成通用拆分策略"""
        files = []

        # 按复杂度和职责拆分
        large_classes = [cls for cls in classes if cls['complexity'] > 30]
        medium_classes = [cls for cls in classes if 10 <= cls['complexity'] <= 30]
        small_classes = [cls for cls in classes if cls['complexity'] < 10]

        base_name = file_path.replace('.py', '').replace('src/', '')

        if large_classes:
            files.append({
                'name': f"{base_name}_core.py",
                'classes': large_classes,
                'functions': [],
                'description': '核心复杂类'
            })

        if medium_classes:
            files.append({
                'name': f"{base_name}_services.py",
                'classes': medium_classes,
                'functions': [],
                'description': '服务类'
            })

        if small_classes:
            files.append({
                'name': f"{base_name}_models.py",
                'classes': small_classes,
                'functions': [],
                'description': '数据模型类'
            })

        if functions:
            files.append({
                'name': f"{base_name}_utils.py",
                'classes': [],
                'functions': functions,
                'description': '工具函数'
            })

        return {
            'method': 'complexity_split',
            'files': files,
            'reasoning': ['按复杂度和职责拆分：核心类、服务类、模型类、工具函数']
        }

    def create_split_files(self, analysis: Dict) -> List[str]:
        """创建拆分后的文件"""
        if 'error' in analysis:
            print(f"❌ 无法拆分文件 {analysis['path']}: {analysis['error']}")
            return []

        strategy = analysis['split_strategy']
        created_files = []
        original_path = analysis['path']
        original_dir = os.path.dirname(original_path)

        print(f"\n📝 拆分文件: {original_path}")
        print(f"   策略: {strategy['method']}")
        print(f"   原因: {', '.join(strategy['reasoning'])}")

        for file_plan in strategy['files']:
            file_path = os.path.join(original_dir, file_plan['name'])

            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 生成文件内容
            content = self._generate_file_content(
                file_plan, analysis['imports'], analysis['constants']
            )

            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            created_files.append(file_path)
            print(f"   ✅ 创建: {file_plan['name']} ({file_plan['description']})")

        # 创建主文件（导入所有拆分后的模块）
        main_content = self._generate_main_file(strategy, original_path)
        with open(original_path, 'w', encoding='utf-8') as f:
            f.write(main_content)

        print(f"   ✅ 更新: {os.path.basename(original_path)} (主模块)")

        return created_files

    def _generate_file_content(self, file_plan: Dict, imports: List[Dict], constants: List[Dict]) -> str:
        """生成拆分文件的内容"""
        content = []

        # 文件头
        content.append(f'"""\n{file_plan["description"]}\n"""\n')

        # 导入
        if imports:
            content.append("# 导入")
            for imp in imports:
                if imp['type'] == 'import':
                    for name in imp['names']:
                        content.append(f"import {name}")
                else:  # from_import
                    module = imp['module'] or ''
                    names = ', '.join(imp['names'])
                    content.append(f"from {module} import {names}")
            content.append("")

        content.append("")

        # 常量
        if constants:
            content.append("# 常量")
            for const in constants:
                content.append(f"{const['name']} = {const['value']}")
            content.append("")

        # 类
        if file_plan['classes']:
            content.append("# 类定义")
            for cls in file_plan['classes']:
                class_lines = self._extract_class_lines(cls)
                content.extend(class_lines)
                content.append("")

        # 函数
        if file_plan['functions']:
            content.append("# 函数定义")
            for func in file_plan['functions']:
                func_lines = self._extract_function_lines(func)
                content.extend(func_lines)
                content.append("")

        return '\n'.join(content)

    def _extract_class_lines(self, cls: Dict) -> List[str]:
        """从原始内容中提取类定义行"""
        # 这里简化处理，实际项目中需要更精确的行提取
        lines = []
        lines.append(f"class {cls['name']}:")
        if cls['docstring']:
            lines.append(f'    """{cls["docstring"]}"""')
        lines.append("    pass  # TODO: 实现类逻辑")
        return lines

    def _extract_function_lines(self, func: Dict) -> List[str]:
        """从原始内容中提取函数定义行"""
        lines = []
        args_str = ', '.join(func['args'])
        lines.append(f"def {func['name']}({args_str}):")
        if func['docstring']:
            lines.append(f'    """{func["docstring"]}"""')
        lines.append("    pass  # TODO: 实现函数逻辑")
        return lines

    def _generate_main_file(self, strategy: Dict, original_path: str) -> str:
        """生成主模块文件内容"""
        content = []

        # 文件头
        module_name = os.path.basename(original_path).replace('.py', '')
        content.append(f'"""\n{module_name} 主模块\n')
        content.append('此文件由长文件拆分工具自动生成\n')
        content.append(f'拆分策略: {strategy["method"]}\n"""\n')

        # 导入所有拆分的模块
        content.append("# 导入拆分的模块")
        base_name = original_path.replace('.py', '').replace('src/', '').replace('/', '.')

        for file_plan in strategy['files']:
            module_name = file_plan['name'].replace('.py', '').replace('/', '.')
            content.append(f"from {base_name}.{module_name} import *")

        content.append("")
        content.append("# 导出所有公共接口")
        content.append("__all__ = [")

        # 添加所有公共类和函数
        for file_plan in strategy['files']:
            for cls in file_plan['classes']:
                if not cls['name'].startswith('_'):
                    content.append(f'    "{cls["name"]}",')
            for func in file_plan['functions']:
                if not func['name'].startswith('_'):
                    content.append(f'    "{func["name"]}",')

        if len(content) > 4:  # 如果有导出，移除最后一个逗号
            content[-1] = content[-1].rstrip(',')

        content.append("]")

        return '\n'.join(content)

def main():
    """主函数"""
    print("🚀 Issue #87: 长文件智能拆分")
    print("=" * 50)

    splitter = LongFileSplitter()

    print(f"📋 拆分 {len(splitter.critical_files)} 个紧急文件...")
    print("=" * 50)

    total_created_files = 0

    for file_path in splitter.critical_files:
        if os.path.exists(file_path):
            print(f"\n{'='*60}")

            # 分析文件
            analysis = splitter.analyze_file_for_splitting(file_path)

            if 'error' in analysis:
                print(f"❌ 分析失败: {file_path}")
                continue

            # 执行拆分
            created_files = splitter.create_split_files(analysis)
            total_created_files += len(created_files)

            if created_files:
                print(f"✅ 拆分完成: {file_path}")
                print(f"   创建文件数: {len(created_files)}")
        else:
            print(f"⚠️ 文件不存在: {file_path}")

    print("\n📊 拆分总结:")
    print(f"   处理文件数: {len(splitter.critical_files)}")
    print(f"   创建文件数: {total_created_files}")
    print(f"   平均每文件创建: {total_created_files // len(splitter.critical_files):.1f} 个新文件")

if __name__ == "__main__":
    main()