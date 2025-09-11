"""
任务依赖解析器

负责处理任务间的依赖关系，确保任务按正确顺序执行。
支持循环依赖检测、依赖链解析、条件依赖等功能。

基于 DATA_DESIGN.md 第3节调度策略设计。
"""

import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class DependencyError(Exception):
    """依赖关系错误异常"""

    pass


class CircularDependencyError(DependencyError):
    """循环依赖错误异常"""

    pass


class DependencyNode:
    """依赖节点类"""

    def __init__(self, task_id: str, dependencies: List[str]):
        """
        初始化依赖节点

        Args:
            task_id: 任务ID
            dependencies: 依赖的任务ID列表
        """
        self.task_id = task_id
        self.dependencies = set(dependencies)
        self.dependents: Set[str] = set()  # 依赖此任务的其他任务
        self.last_success_time: Optional[datetime] = None
        self.is_running = False

    def add_dependency(self, dep_task_id: str) -> None:
        """添加依赖关系"""
        self.dependencies.add(dep_task_id)

    def remove_dependency(self, dep_task_id: str) -> None:
        """移除依赖关系"""
        self.dependencies.discard(dep_task_id)

    def add_dependent(self, dependent_task_id: str) -> None:
        """添加依赖此任务的任务"""
        self.dependents.add(dependent_task_id)

    def remove_dependent(self, dependent_task_id: str) -> None:
        """移除依赖此任务的任务"""
        self.dependents.discard(dependent_task_id)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "dependencies": list(self.dependencies),
            "dependents": list(self.dependents),
            "last_success_time": self.last_success_time.isoformat()
            if self.last_success_time
            else None,
            "is_running": self.is_running,
        }


class DependencyResolver:
    """
    任务依赖解析器主类

    负责管理和解析任务间的依赖关系，提供以下功能：
    - 依赖关系图构建和维护
    - 循环依赖检测
    - 执行顺序计算
    - 依赖条件检查
    - 依赖链路分析
    """

    def __init__(self):
        """初始化依赖解析器"""
        self.nodes: Dict[str, DependencyNode] = {}
        self.dependency_cache: Dict[str, List[str]] = {}  # 缓存依赖链
        self.cache_ttl = timedelta(minutes=5)  # 缓存过期时间
        self.cache_updated_at: Dict[str, datetime] = {}

        logger.info("任务依赖解析器初始化完成")

    def add_task(self, task_id: str, dependencies: List[str]) -> bool:
        """
        添加任务及其依赖关系

        Args:
            task_id: 任务ID
            dependencies: 依赖的任务ID列表

        Returns:
            bool: 添加是否成功
        """
        try:
            # 创建或更新节点
            if task_id in self.nodes:
                node = self.nodes[task_id]
                # 清理旧的依赖关系
                for old_dep in node.dependencies:
                    if old_dep in self.nodes:
                        self.nodes[old_dep].remove_dependent(task_id)
                node.dependencies = set(dependencies)
            else:
                node = DependencyNode(task_id, dependencies)
                self.nodes[task_id] = node

            # 建立依赖关系
            for dep_task_id in dependencies:
                # 确保依赖的任务存在
                if dep_task_id not in self.nodes:
                    self.nodes[dep_task_id] = DependencyNode(dep_task_id, [])

                # 添加反向依赖关系
                self.nodes[dep_task_id].add_dependent(task_id)

            # 检查循环依赖
            if self._has_circular_dependency():
                # 回滚更改
                self.remove_task(task_id)
                raise CircularDependencyError(f"添加任务 {task_id} 会产生循环依赖")

            # 清除相关缓存
            self._clear_dependency_cache(task_id)

            logger.info(f"任务依赖关系添加成功: {task_id} -> {dependencies}")
            return True

        except Exception as e:
            logger.error(f"添加任务依赖关系失败: {task_id} - {e}")
            return False

    def remove_task(self, task_id: str) -> bool:
        """
        移除任务及其所有依赖关系

        Args:
            task_id: 任务ID

        Returns:
            bool: 移除是否成功
        """
        if task_id not in self.nodes:
            logger.warning(f"任务不存在，无法移除: {task_id}")
            return False

        try:
            node = self.nodes[task_id]

            # 清理与其他任务的依赖关系
            for dep_task_id in node.dependencies:
                if dep_task_id in self.nodes:
                    self.nodes[dep_task_id].remove_dependent(task_id)

            for dependent_task_id in node.dependents:
                if dependent_task_id in self.nodes:
                    self.nodes[dependent_task_id].remove_dependency(task_id)

            # 移除节点
            del self.nodes[task_id]

            # 清除相关缓存
            self._clear_dependency_cache(task_id)

            logger.info(f"任务依赖关系移除成功: {task_id}")
            return True

        except Exception as e:
            logger.error(f"移除任务依赖关系失败: {task_id} - {e}")
            return False

    def can_execute(self, task_id: str, task_states: Dict[str, Any]) -> bool:
        """
        检查任务是否可以执行（所有依赖已满足）

        Args:
            task_id: 任务ID
            task_states: 任务状态字典，包含每个任务的状态信息

        Returns:
            bool: 是否可以执行
        """
        if task_id not in self.nodes:
            logger.warning(f"任务不存在: {task_id}")
            return False

        node = self.nodes[task_id]

        # 检查是否正在运行
        if node.is_running:
            return False

        # 检查所有依赖任务
        for dep_task_id in node.dependencies:
            if not self._is_dependency_satisfied(dep_task_id, task_states):
                logger.debug(f"任务 {task_id} 的依赖 {dep_task_id} 未满足")
                return False

        return True

    def _is_dependency_satisfied(
        self, dep_task_id: str, task_states: Dict[str, Any]
    ) -> bool:
        """
        检查单个依赖是否已满足

        Args:
            dep_task_id: 依赖任务ID
            task_states: 任务状态字典

        Returns:
            bool: 依赖是否已满足
        """
        # 检查依赖任务是否存在
        if dep_task_id not in task_states:
            return False

        task_state = task_states[dep_task_id]

        # 检查依赖任务是否最近执行成功
        if hasattr(task_state, "last_run_time") and hasattr(task_state, "last_error"):
            # 如果有最近执行时间且没有错误，认为依赖满足
            if task_state.last_run_time and not task_state.last_error:
                # 检查执行时间是否在合理范围内（24小时内）
                time_diff = datetime.now() - task_state.last_run_time
                if time_diff <= timedelta(hours=24):
                    return True

        return False

    def get_execution_order(self, task_ids: Optional[List[str]] = None) -> List[str]:
        """
        获取任务的推荐执行顺序（拓扑排序）

        Args:
            task_ids: 要排序的任务ID列表，为空时排序所有任务

        Returns:
            List[str]: 排序后的任务ID列表
        """
        if task_ids is None:
            task_ids = list(self.nodes.keys())

        # 使用Kahn算法进行拓扑排序
        in_degree: Dict[str, int] = defaultdict(int)
        adj_list: Dict[str, List[str]] = defaultdict(list)

        # 构建邻接表和入度统计
        for task_id in task_ids:
            if task_id not in self.nodes:
                continue

            node = self.nodes[task_id]
            for dep_id in node.dependencies:
                if dep_id in task_ids:
                    adj_list[dep_id].append(task_id)
                    in_degree[task_id] += 1

        # 初始化队列（入度为0的节点）
        queue = deque([task_id for task_id in task_ids if in_degree[task_id] == 0])
        result = []

        while queue:
            current = queue.popleft()
            result.append(current)

            # 更新相邻节点的入度
            for neighbor in adj_list[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # 检查是否存在循环依赖
        if len(result) != len(task_ids):
            remaining_tasks = [task_id for task_id in task_ids if task_id not in result]
            logger.warning(f"存在循环依赖，无法排序的任务: {remaining_tasks}")

        return result

    def _has_circular_dependency(self) -> bool:
        """
        检查是否存在循环依赖

        Returns:
            bool: 是否存在循环依赖
        """
        # 使用深度优先搜索检测环
        visited = set()
        rec_stack = set()

        def dfs(task_id: str) -> bool:
            if task_id in rec_stack:
                return True  # 发现环
            if task_id in visited:
                return False

            visited.add(task_id)
            rec_stack.add(task_id)

            # 检查所有依赖
            if task_id in self.nodes:
                for dep_id in self.nodes[task_id].dependencies:
                    if dfs(dep_id):
                        return True

            rec_stack.remove(task_id)
            return False

        # 检查所有任务
        for task_id in self.nodes:
            if task_id not in visited:
                if dfs(task_id):
                    return True

        return False

    def get_dependency_chain(self, task_id: str, max_depth: int = 10) -> List[str]:
        """
        获取任务的完整依赖链

        Args:
            task_id: 任务ID
            max_depth: 最大搜索深度

        Returns:
            List[str]: 依赖链（从最底层依赖到目标任务）
        """
        # 检查缓存
        cache_key = f"{task_id}_{max_depth}"
        if cache_key in self.dependency_cache:
            if self._is_cache_valid(cache_key):
                return self.dependency_cache[cache_key]

        if task_id not in self.nodes:
            return []

        dependency_chain = []
        visited = set()

        def collect_dependencies(current_id: str, depth: int) -> None:
            if depth > max_depth or current_id in visited:
                return

            visited.add(current_id)

            if current_id in self.nodes:
                node = self.nodes[current_id]
                for dep_id in node.dependencies:
                    collect_dependencies(dep_id, depth + 1)
                    if dep_id not in dependency_chain:
                        dependency_chain.append(dep_id)

            if current_id not in dependency_chain:
                dependency_chain.append(current_id)

        collect_dependencies(task_id, 0)

        # 缓存结果
        self.dependency_cache[cache_key] = dependency_chain
        self.cache_updated_at[cache_key] = datetime.now()

        return dependency_chain

    def get_dependent_tasks(self, task_id: str) -> List[str]:
        """
        获取依赖指定任务的所有任务

        Args:
            task_id: 任务ID

        Returns:
            List[str]: 依赖此任务的任务ID列表
        """
        if task_id not in self.nodes:
            return []

        return list(self.nodes[task_id].dependents)

    def update_task_status(
        self, task_id: str, is_running: bool, success: bool = False
    ) -> None:
        """
        更新任务执行状态

        Args:
            task_id: 任务ID
            is_running: 是否正在运行
            success: 是否执行成功
        """
        if task_id not in self.nodes:
            logger.warning(f"任务不存在，无法更新状态: {task_id}")
            return

        node = self.nodes[task_id]
        node.is_running = is_running

        if success and not is_running:
            node.last_success_time = datetime.now()

        logger.debug(f"任务状态已更新: {task_id}, running={is_running}, success={success}")

    def get_dependency_graph(self) -> Dict[str, Any]:
        """
        获取完整的依赖关系图

        Returns:
            Dict[str, Any]: 依赖关系图数据
        """
        return {
            "nodes": {task_id: node.to_dict() for task_id, node in self.nodes.items()},
            "total_tasks": len(self.nodes),
            "dependency_count": sum(
                len(node.dependencies) for node in self.nodes.values()
            ),
            "execution_order": self.get_execution_order(),
        }

    def _clear_dependency_cache(self, task_id: str) -> None:
        """
        清除与指定任务相关的依赖缓存

        Args:
            task_id: 任务ID
        """
        keys_to_remove = []
        for cache_key in self.dependency_cache:
            if task_id in cache_key:
                keys_to_remove.append(cache_key)

        for key in keys_to_remove:
            del self.dependency_cache[key]
            if key in self.cache_updated_at:
                del self.cache_updated_at[key]

    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        检查缓存是否有效

        Args:
            cache_key: 缓存键

        Returns:
            bool: 缓存是否有效
        """
        if cache_key not in self.cache_updated_at:
            return False

        time_diff = datetime.now() - self.cache_updated_at[cache_key]
        return time_diff <= self.cache_ttl

    def validate_dependencies(self) -> Tuple[bool, List[str]]:
        """
        验证所有依赖关系的有效性

        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []

        # 检查循环依赖
        if self._has_circular_dependency():
            errors.append("存在循环依赖")

        # 检查悬空依赖（依赖不存在的任务）
        for task_id, node in self.nodes.items():
            for dep_id in node.dependencies:
                if dep_id not in self.nodes:
                    errors.append(f"任务 {task_id} 依赖不存在的任务 {dep_id}")

        is_valid = len(errors) == 0
        return is_valid, errors

    def optimize_execution_plan(self, available_workers: int = 5) -> List[List[str]]:
        """
        优化执行计划，支持并行执行

        Args:
            available_workers: 可用工作线程数

        Returns:
            List[List[str]]: 分层执行计划，每层内的任务可以并行执行
        """
        execution_order = self.get_execution_order()
        execution_levels = []
        remaining_tasks = set(execution_order)

        while remaining_tasks:
            current_level = []

            # 找出当前可以执行的任务（没有未满足的依赖）
            for task_id in list(remaining_tasks):
                if task_id not in self.nodes:
                    current_level.append(task_id)
                    continue

                node = self.nodes[task_id]
                can_execute = True

                for dep_id in node.dependencies:
                    if dep_id in remaining_tasks:
                        can_execute = False
                        break

                if can_execute:
                    current_level.append(task_id)

            # 限制并行数量
            if len(current_level) > available_workers:
                current_level = current_level[:available_workers]

            if not current_level:
                # 如果没有可执行的任务，说明存在问题
                logger.error(f"无法继续执行，剩余任务: {remaining_tasks}")
                break

            execution_levels.append(current_level)

            # 从剩余任务中移除已安排的任务
            for task_id in current_level:
                remaining_tasks.discard(task_id)

        return execution_levels
