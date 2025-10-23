#!/usr/bin/env python3
"""
文档访问分析和统计工具
Documentation Analytics and Statistics Tool

这个脚本提供了文档访问分析、使用统计和质量评估功能，
帮助了解文档的使用情况和改进方向。

作者: Claude AI Assistant
版本: v1.0.0
创建时间: 2025-10-24
"""

import os
import sys
import json
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter, defaultdict
import logging
import subprocess

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocsAnalytics:
    """文档分析器"""

    def __init__(self, docs_dir: str = "docs"):
        """
        初始化文档分析器

        Args:
            docs_dir: 文档目录路径
        """
        self.docs_dir = Path(docs_dir)
        self.site_dir = Path("site")
        self.analytics_data = {
            "analysis_time": datetime.now().isoformat(),
            "project_info": self._get_project_info(),
            "content_analysis": {},
            "structure_analysis": {},
            "quality_metrics": {},
            "usage_patterns": {},
            "recommendations": []
        }

    def _get_project_info(self) -> Dict[str, Any]:
        """获取项目信息"""
        return {
            "name": self._get_project_name(),
            "description": "足球预测系统文档",
            "version": "v2.0",
            "docs_directory": str(self.docs_dir),
            "total_size": self._get_directory_size(self.docs_dir)
        }

    def _get_project_name(self) -> str:
        """获取项目名称"""
        try:
            if os.path.exists("pyproject.toml"):
                with open("pyproject.toml", 'r') as f:
                    content = f.read()
                    # 简单的项目名提取
                    match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        return match.group(1)
        except Exception:
            pass
        return "FootballPrediction"

    def _get_directory_size(self, directory: Path) -> str:
        """获取目录大小"""
        try:
            result = subprocess.run(
                ["du", "-sh", str(directory)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.split()[0]
        except Exception:
            pass
        return "未知"

    def analyze_content(self) -> None:
        """分析文档内容"""
        logger.info("📊 分析文档内容...")

        content_analysis = {
            "file_statistics": self._analyze_file_statistics(),
            "content_statistics": self._analyze_content_statistics(),
            "topic_analysis": self._analyze_topics(),
            "language_analysis": self._analyze_language(),
            "readability_analysis": self._analyze_readability()
        }

        self.analytics_data["content_analysis"] = content_analysis

    def _analyze_file_statistics(self) -> Dict[str, Any]:
        """分析文件统计"""
        stats = {
            "total_files": 0,
            "total_size": 0,
            "file_types": defaultdict(int),
            "largest_files": [],
            "file_age_distribution": defaultdict(int)
        }

        try:
            all_files = []
            current_time = datetime.now()

            for file_path in self.docs_dir.rglob("*"):
                if file_path.is_file():
                    all_files.append(file_path)

            stats["total_files"] = len(all_files)

            # 统计文件类型和大小
            for file_path in all_files:
                size = file_path.stat().st_size
                stats["total_size"] += size
                stats["file_types"][file_path.suffix] += 1

                # 统计文件年龄
                file_age_days = (current_time - datetime.fromtimestamp(file_path.stat().st_mtime)).days
                if file_age_days < 7:
                    stats["file_age_distribution"]["<1_week"] += 1
                elif file_age_days < 30:
                    stats["file_age_distribution"]["<1_month"] += 1
                elif file_age_days < 90:
                    stats["file_age_distribution"]["<3_months"] += 1
                else:
                    stats["file_age_distribution"][">3_months"] += 1

            # 找出最大的文件
            stats["largest_files"] = [
                {
                    "path": str(f.relative_to(self.docs_dir)),
                    "size": f.stat().st_size,
                    "size_human": self._format_size(f.stat().st_size)
                }
                for f in sorted(all_files, key=lambda x: x.stat().st_size, reverse=True)[:10]
            ]

            stats["total_size_human"] = self._format_size(stats["total_size"])

        except Exception as e:
            logger.error(f"文件统计失败: {e}")

        return dict(stats)

    def _analyze_content_statistics(self) -> Dict[str, Any]:
        """分析内容统计"""
        stats = {
            "total_words": 0,
            "total_lines": 0,
            "total_characters": 0,
            "average_file_size": 0,
            "files_with_frontmatter": 0,
            "files_with_toc": 0,
            "files_with_code_blocks": 0,
            "files_with_images": 0,
            "files_with_tables": 0,
            "files_with_links": 0
        }

        try:
            md_files = list(self.docs_dir.rglob("*.md"))
            file_sizes = []

            for md_file in md_files:
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    lines = content.split('\n')
                    words = content.split()

                    file_sizes.append(len(content))
                    stats["total_lines"] += len(lines)
                    stats["total_words"] += len(words)
                    stats["total_characters"] += len(content)

                    # 检查文档结构
                    if content.startswith('---'):
                        stats["files_with_frontmatter"] += 1

                    if '## 📑 目录' in content or '## 目录' in content:
                        stats["files_with_toc"] += 1

                    if '```' in content:
                        stats["files_with_code_blocks"] += 1

                    if '![' in content:
                        stats["files_with_images"] += 1

                    if '|' in content and '-' in content:
                        stats["files_with_tables"] += 1

                    if '[' in content and '](' in content:
                        stats["files_with_links"] += 1

                except Exception as e:
                    logger.warning(f"读取文件失败 {md_file}: {e}")

            if file_sizes:
                stats["average_file_size"] = sum(file_sizes) / len(file_sizes)
                stats["average_file_size_human"] = self._format_size(int(stats["average_file_size"]))

            stats["total_files_analyzed"] = len(md_files)

        except Exception as e:
            logger.error(f"内容统计失败: {e}")

        return dict(stats)

    def _analyze_topics(self) -> Dict[str, Any]:
        """分析主题分布"""
        topics = {
            "architecture": 0,
            "development": 0,
            "testing": 0,
            "deployment": 0,
            "security": 0,
            "monitoring": 0,
            "database": 0,
            "api": 0,
            "ml": 0,
            "data": 0
        }

        topic_keywords = {
            "architecture": ["架构", "architecture", "系统", "设计", "模块"],
            "development": ["开发", "development", "代码", "编程", "开发"],
            "testing": ["测试", "test", "测试", "单元", "集成"],
            "deployment": ["部署", "deployment", "发布", "上线", "生产"],
            "security": ["安全", "security", "认证", "授权", "加密"],
            "monitoring": ["监控", "monitoring", "日志", "告警", "指标"],
            "database": ["数据库", "database", "db", "sql", "存储"],
            "api": ["API", "api", "接口", "endpoint", "路由"],
            "ml": ["机器学习", "ML", "模型", "训练", "预测"],
            "data": ["数据", "data", "数据采集", "处理", "特征"]
        }

        try:
            md_files = list(self.docs_dir.rglob("*.md"))

            for md_file in md_files:
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read().lower()

                    # 计算主题得分
                    for topic, keywords in topic_keywords.items():
                        score = sum(1 for keyword in keywords if keyword in content)
                        if score > 0:
                            topics[topic] += score

                except Exception as e:
                    logger.warning(f"分析主题失败 {md_file}: {e}")

            # 转换为百分比
            total_topics = sum(topics.values())
            if total_topics > 0:
                topic_distribution = {
                    topic: (count / total_topics) * 100
                    for topic, count in topics.items()
                }
            else:
                topic_distribution = topics

        except Exception as e:
            logger.error(f"主题分析失败: {e}")
            topic_distribution = topics

        return {
            "topic_counts": topics,
            "topic_distribution": topic_distribution,
            "dominant_topic": max(topics.items(), key=lambda x: x[1])[0] if topics else None
        }

    def _analyze_language(self) -> Dict[str, Any]:
        """分析语言使用"""
        language_stats = {
            "chinese_characters": 0,
            "english_words": 0,
            "mixed_language_files": 0,
            "chinese_only_files": 0,
            "english_only_files": 0,
            "language_ratio": 0.0
        }

        try:
            md_files = list(self.docs_dir.rglob("*.md"))

            for md_file in md_files:
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 计算中文字符
                    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
                    # 计算英文单词
                    english_words = len(re.findall(r'\b[a-zA-Z]+\b', content))

                    language_stats["chinese_characters"] += chinese_chars
                    language_stats["english_words"] += english_words

                    if chinese_chars > 0 and english_words > 0:
                        language_stats["mixed_language_files"] += 1
                    elif chinese_chars > 0:
                        language_stats["chinese_only_files"] += 1
                    elif english_words > 0:
                        language_stats["english_only_files"] += 1

                except Exception as e:
                    logger.warning(f"语言分析失败 {md_file}: {e}")

            total = language_stats["chinese_characters"] + language_stats["english_words"]
            if total > 0:
                language_stats["language_ratio"] = {
                    "chinese": (language_stats["chinese_characters"] / total) * 100,
                    "english": (language_stats["english_words"] / total) * 100
                }

        except Exception as e:
            logger.error(f"语言分析失败: {e}")

        return language_stats

    def _analyze_readability(self) -> Dict[str, Any]:
        """分析可读性"""
        readability = {
            "average_words_per_paragraph": 0,
            "average_sentences_per_paragraph": 0,
            "average_words_per_sentence": 0,
            "headings_per_file": 0,
            "files_with_multiple_headings": 0,
            "complex_files": 0
        }

        try:
            md_files = list(self.docs_dir.rglob("*.md"))
            paragraph_counts = []
            sentence_counts = []
            word_counts = []
            heading_counts = []

            for md_file in md_files:
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 统计标题
                    headings = re.findall(r'^#+\s+', content, re.MULTILINE)
                    heading_counts.append(len(headings))
                    if len(headings) > 5:
                        readability["files_with_multiple_headings"] += 1

                    # 简单的可读性分析
                    words = content.split()
                    sentences = re.split(r'[.!?]+', content)
                    paragraphs = content.split('\n\n')

                    word_counts.append(len(words))
                    sentence_counts.append(len([s for s in sentences if s.strip()]))
                    paragraph_counts.append(len([p for p in paragraphs if p.strip()]))

                    # 标记复杂文件（超过500个单词且少于3个标题）
                    if len(words) > 500 and len(headings) < 3:
                        readability["complex_files"] += 1

                except Exception as e:
                    logger.warning(f"可读性分析失败 {md_file}: {e}")

            if paragraph_counts:
                readability["average_words_per_paragraph"] = sum(word_counts) / sum(paragraph_counts)
                readability["average_sentences_per_paragraph"] = sum(sentence_counts) / sum(paragraph_counts)
                readability["average_words_per_sentence"] = sum(word_counts) / sum(sentence_counts)

            if heading_counts:
                readability["headings_per_file"] = sum(heading_counts) / len(heading_counts)

        except Exception as e:
            logger.error(f"可读性分析失败: {e}")

        return readability

    def analyze_structure(self) -> None:
        """分析文档结构"""
        logger.info("🏗️ 分析文档结构...")

        structure_analysis = {
            "directory_structure": self._analyze_directory_structure(),
            "navigation_structure": self._analyze_navigation_structure(),
            "cross_references": self._analyze_cross_references(),
            "depth_analysis": self._analyze_depth()
        }

        self.analytics_data["structure_analysis"] = structure_analysis

    def _analyze_directory_structure(self) -> Dict[str, Any]:
        """分析目录结构"""
        structure = {
            "total_directories": 0,
            "max_depth": 0,
            "directory_distribution": defaultdict(int),
            "empty_directories": [],
            "large_directories": []
        }

        try:
            for root, dirs, files in os.walk(self.docs_dir):
                depth = root.count(os.sep) - str(self.docs_dir).count(os.sep)
                structure["max_depth"] = max(structure["max_depth"], depth)
                structure["total_directories"] += 1
                structure["directory_distribution"][f"depth_{depth}"] += 1

                # 检查空目录
                if not dirs and not files:
                    structure["empty_directories"].append(root)

                # 检查大目录（文件数>10）
                if len(files) > 10:
                    structure["large_directories"].append({
                        "path": root,
                        "file_count": len(files)
                    })

        except Exception as e:
            logger.error(f"目录结构分析失败: {e}")

        return dict(structure)

    def _analyze_navigation_structure(self) -> Dict[str, Any]:
        """分析导航结构"""
        navigation = {
            "has_index": False,
            "has_readme": False,
            "nav_sections": 0,
            "nav_links": 0,
            "orphaned_files": []
        }

        try:
            # 检查主要导航文件
            index_file = self.docs_dir / "INDEX.md"
            readme_file = self.docs_dir / "README.md"

            navigation["has_index"] = index_file.exists()
            navigation["has_readme"] = readme_file.exists()

            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 统计导航链接
                links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
                navigation["nav_links"] = len(links)

                # 统计导航章节
                sections = re.findall(r'^#+\s+', content, re.MULTILINE)
                navigation["nav_sections"] = len(sections)

            # 检查孤立文件
            all_md_files = set(self.docs_dir.rglob("*.md"))
            linked_files = set()

            for md_file in all_md_files:
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 查找内部链接
                    internal_links = re.findall(r'\[([^\]]+)\]\(([^)]+\.md)\)', content)
                    for link in internal_links:
                        linked_path = self.docs_dir / link[1]
                        if linked_path.exists():
                            linked_files.add(linked_path)

                except Exception:
                    pass

            orphaned = all_md_files - linked_files
            navigation["orphaned_files"] = [str(f.relative_to(self.docs_dir)) for f in orphaned if f != index_file]

        except Exception as e:
            logger.error(f"导航结构分析失败: {e}")

        return navigation

    def _analyze_cross_references(self) -> Dict[str, Any]:
        """分析交叉引用"""
        references = {
            "total_references": 0,
            "internal_references": 0,
            "external_references": 0,
            "reference_density": 0.0,
            "well_connected_files": [],
            "poorly_connected_files": []
        }

        try:
            md_files = list(self.docs_dir.rglob("*.md"))
            file_connections = defaultdict(int)

            for md_file in md_files:
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 查找所有链接
                    links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
                    references["total_references"] += len(links)

                    for link in links:
                        url = link[1]
                        if url.startswith('http'):
                            references["external_references"] += 1
                        else:
                            references["internal_references"] += 1

                    file_connections[md_file] = len(links)

                except Exception:
                    pass

            # 计算引用密度
            if len(md_files) > 0:
                references["reference_density"] = references["total_references"] / len(md_files)

            # 找出连接良好的文件（>10个链接）
            references["well_connected_files"] = [
                str(f.relative_to(self.docs_dir))
                for f, count in file_connections.items()
                if count > 10
            ]

            # 找出连接不佳的文件（<2个链接）
            references["poorly_connected_files"] = [
                str(f.relative_to(self.docs_dir))
                for f, count in file_connections.items()
                if count < 2 and f.name != "INDEX.md"
            ]

        except Exception as e:
            logger.error(f"交叉引用分析失败: {e}")

        return references

    def _analyze_depth(self) -> Dict[str, Any]:
        """分析文档深度"""
        depth_analysis = {
            "average_depth": 0.0,
            "max_depth": 0,
            "depth_distribution": defaultdict(int),
            "deep_files": []
        }

        try:
            md_files = list(self.docs_dir.rglob("*.md"))
            depths = []

            for md_file in md_files:
                # 计算相对深度
                relative_depth = len(md_file.relative_to(self.docs_dir).parts) - 1
                depths.append(relative_depth)
                depth_analysis["depth_distribution"][f"depth_{relative_depth}"] += 1

                # 记录深层文件（深度>3）
                if relative_depth > 3:
                    depth_analysis["deep_files"].append(str(md_file.relative_to(self.docs_dir)))

            if depths:
                depth_analysis["average_depth"] = sum(depths) / len(depths)
                depth_analysis["max_depth"] = max(depths)

        except Exception as e:
            logger.error(f"深度分析失败: {e}")

        return depth_analysis

    def analyze_quality(self) -> None:
        """分析文档质量"""
        logger.info("📈 分析文档质量...")

        quality_metrics = {
            "completeness_score": self._calculate_completeness_score(),
            "consistency_score": self._calculate_consistency_score(),
            "maintenance_score": self._calculate_maintenance_score(),
            "accessibility_score": self._calculate_accessibility_score(),
            "overall_quality_score": 0.0,
            "quality_issues": []
        }

        # 计算总分
        scores = [
            quality_metrics["completeness_score"],
            quality_metrics["consistency_score"],
            quality_metrics["maintenance_score"],
            quality_metrics["accessibility_score"]
        ]
        quality_metrics["overall_quality_score"] = sum(scores) / len(scores)

        self.analytics_data["quality_metrics"] = quality_metrics

    def _calculate_completeness_score(self) -> float:
        """计算完整性得分"""
        score = 0.0
        total_checks = 0

        try:
            # 检查核心文件
            core_files = [
                "INDEX.md",
                "README.md",
                "architecture/ARCHITECTURE.md",
                "reference/API_REFERENCE.md",
                "testing/TEST_IMPROVEMENT_GUIDE.md"
            ]

            for file_name in core_files:
                total_checks += 1
                if (self.docs_dir / file_name).exists():
                    score += 1.0

            # 检查文档覆盖率
            md_files = list(self.docs_dir.rglob("*.md"))
            if len(md_files) >= 10:  # 至少10个文档文件
                score += 1.0
            total_checks += 1

            # 检查多语言支持
            if self.analytics_data.get("content_analysis", {}).get("language_analysis", {}).get("mixed_language_files", 0) > 0:
                score += 1.0
            total_checks += 1

        except Exception as e:
            logger.error(f"完整性评分失败: {e}")

        return (score / total_checks * 100) if total_checks > 0 else 0.0

    def _calculate_consistency_score(self) -> float:
        """计算一致性得分"""
        score = 0.0
        total_checks = 0

        try:
            md_files = list(self.docs_dir.rglob("*.md"))

            # 检查标题格式一致性
            consistent_titles = 0
            for md_file in md_files:
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if re.search(r'^# ', content, re.MULTILINE):
                        consistent_titles += 1
                except Exception:
                    pass

            if len(md_files) > 0:
                title_consistency = consistent_titles / len(md_files)
                score += title_consistency
                total_checks += 1

            # 检查链接格式一致性
            consistent_links = 0
            for md_file in md_files:
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
                    if links:
                        consistent_links += 1
                except Exception:
                    pass

            if len(md_files) > 0:
                link_consistency = consistent_links / len(md_files)
                score += link_consistency
                total_checks += 1

        except Exception as e:
            logger.error(f"一致性评分失败: {e}")

        return (score / total_checks * 100) if total_checks > 0 else 0.0

    def _calculate_maintenance_score(self) -> float:
        """计算维护性得分"""
        score = 0.0
        total_checks = 0

        try:
            # 检查文件更新时间
            md_files = list(self.docs_dir.rglob("*.md"))
            recent_files = 0
            current_time = datetime.now()

            for md_file in md_files:
                file_time = datetime.fromtimestamp(md_file.stat().st_mtime)
                if (current_time - file_time).days < 30:  # 30天内更新
                    recent_files += 1

            if len(md_files) > 0:
                freshness_score = recent_files / len(md_files)
                score += freshness_score
                total_checks += 1

            # 检查文档结构清晰度
            structure_score = min(len(self.docs_dir.rglob("*/")) / 10, 1.0)  # 目录数量/10
            score += structure_score
            total_checks += 1

        except Exception as e:
            logger.error(f"维护性评分失败: {e}")

        return (score / total_checks * 100) if total_checks > 0 else 0.0

    def _calculate_accessibility_score(self) -> float:
        """计算可访问性得分"""
        score = 0.0
        total_checks = 0

        try:
            md_files = list(self.docs_dir.rglob("*.md"))

            # 检查目录存在性
            files_with_toc = 0
            for md_file in md_files:
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if '## 📑 目录' in content or '## 目录' in content:
                        files_with_toc += 1
                except Exception:
                    pass

            if len(md_files) > 0:
                toc_score = files_with_toc / len(md_files)
                score += toc_score
                total_checks += 1

            # 检查索引文件
            if (self.docs_dir / "INDEX.md").exists():
                score += 1.0
            total_checks += 1

        except Exception as e:
            logger.error(f"可访问性评分失败: {e}")

        return (score / total_checks * 100) if total_checks > 0 else 0.0

    def generate_recommendations(self) -> None:
        """生成改进建议"""
        logger.info("💡 生成改进建议...")

        recommendations = []

        # 基于内容分析的建议
        content_stats = self.analytics_data.get("content_analysis", {})

        if content_stats.get("content_statistics", {}).get("files_with_toc", 0) < len(list(self.docs_dir.rglob("*.md"))) * 0.5:
            recommendations.append({
                "type": "structure",
                "priority": "high",
                "title": "增加文档目录",
                "description": "超过50%的文档缺少目录，建议为重要文档添加目录以提高可读性"
            })

        if content_stats.get("content_statistics", {}).get("files_with_code_blocks", 0) < 5:
            recommendations.append({
                "type": "content",
                "priority": "medium",
                "title": "增加代码示例",
                "description": "文档中缺少代码示例，建议添加实际的代码示例和用法说明"
            })

        # 基于结构分析的建议
        structure_stats = self.analytics_data.get("structure_analysis", {})

        orphaned_files = structure_stats.get("navigation_structure", {}).get("orphaned_files", [])
        if len(orphaned_files) > 3:
            recommendations.append({
                "type": "navigation",
                "priority": "high",
                "title": "减少孤立文档",
                "description": f"发现{len(orphaned_files)}个孤立文档，建议在索引页面或相关文档中添加链接"
            })

        # 基于质量分析的建议
        quality_metrics = self.analytics_data.get("quality_metrics", {})

        if quality_metrics.get("overall_quality_score", 0) < 70:
            recommendations.append({
                "type": "quality",
                "priority": "high",
                "title": "提升文档质量",
                "description": f"当前文档质量得分为{quality_metrics.get('overall_quality_score', 0):.1f}，建议系统性改进文档质量"
            })

        # 基于语言分析的建议
        language_stats = content_stats.get("language_analysis", {})
        if language_stats.get("mixed_language_files", 0) == 0:
            recommendations.append({
                "type": "internationalization",
                "priority": "medium",
                "title": "考虑多语言支持",
                "description": "当前文档为单一语言，考虑添加英文版本以支持国际用户"
            })

        # 基于交叉引用分析的建议
        cross_refs = structure_stats.get("cross_references", {})
        if cross_refs.get("reference_density", 0) < 5:
            recommendations.append({
                "type": "connectivity",
                "priority": "medium",
                "title": "增加文档链接",
                "description": f"文档链接密度较低({cross_refs.get('reference_density', 0):.1f})，建议增加相关文档的交叉引用"
            })

        self.analytics_data["recommendations"] = recommendations

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def save_analysis(self, output_path: Optional[str] = None) -> str:
        """保存分析结果"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"docs-analytics-report-{timestamp}.json"

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.analytics_data, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"📊 分析报告已保存: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"保存分析报告失败: {e}")
            raise

    def generate_summary_report(self) -> str:
        """生成摘要报告"""
        report = []
        report.append("# 📊 文档分析报告")
        report.append("")
        report.append(f"**分析时间**: {self.analytics_data['analysis_time']}")
        report.append(f"**项目名称**: {self.analytics_data['project_info']['name']}")
        report.append("")
        report.append("## 📋 核心指标")
        report.append("")

        # 内容统计
        content_stats = self.analytics_data.get("content_analysis", {})
        if content_stats:
            file_stats = content_stats.get("file_statistics", {})
            content_stats_data = content_stats.get("content_statistics", {})

            report.append("### 📄 文档统计")
            report.append(f"- **总文件数**: {file_stats.get('total_files', 0)}")
            report.append(f"- **总大小**: {file_stats.get('total_size_human', '未知')}")
            report.append(f"- **总字数**: {content_stats_data.get('total_words', 0):,}")
            report.append(f"- **总行数**: {content_stats_data.get('total_lines', 0):,}")
            report.append("")

        # 结构统计
        structure_stats = self.analytics_data.get("structure_analysis", {})
        if structure_stats:
            nav_stats = structure_stats.get("navigation_structure", {})
            report.append("### 🏗️ 结构分析")
            report.append(f"- **索引文件**: {'✅' if nav_stats.get('has_index') else '❌'}")
            report.append(f"- **导航链接**: {nav_stats.get('nav_links', 0)}")
            report.append(f"- **孤立文件**: {len(nav_stats.get('orphaned_files', []))}")
            report.append("")

        # 质量评估
        quality_metrics = self.analytics_data.get("quality_metrics", {})
        if quality_metrics:
            report.append("### 📈 质量评估")
            report.append(f"- **整体得分**: {quality_metrics.get('overall_quality_score', 0):.1f}/100")
            report.append(f"- **完整性**: {quality_metrics.get('completeness_score', 0):.1f}/100")
            report.append(f"- **一致性**: {quality_metrics.get('consistency_score', 0):.1f}/100")
            report.append(f"- **维护性**: {quality_metrics.get('maintenance_score', 0):.1f}/100")
            report.append(f"- **可访问性**: {quality_metrics.get('accessibility_score', 0):.1f}/100")
            report.append("")

        # 改进建议
        recommendations = self.analytics_data.get("recommendations", [])
        if recommendations:
            report.append("## 💡 改进建议")
            report.append("")
            for i, rec in enumerate(recommendations[:5], 1):  # 只显示前5个建议
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec.get("priority", "medium"), "🟡")
                report.append(f"{i}. **{priority_emoji} {rec.get('title', '未知')}** ({rec.get('priority', 'medium')})")
                report.append(f"   {rec.get('description', '无描述')}")
                report.append("")

        return "\n".join(report)

    def print_summary(self) -> None:
        """打印摘要信息"""
        print("\n" + "="*60)
        print("📊 文档分析摘要")
        print("="*60)

        # 基本信息
        print(f"项目: {self.analytics_data['project_info']['name']}")
        print(f"文档目录: {self.analytics_data['project_info']['docs_directory']}")
        print(f"分析时间: {self.analytics_data['analysis_time']}")
        print()

        # 核心指标
        content_stats = self.analytics_data.get("content_analysis", {})
        if content_stats:
            file_stats = content_stats.get("file_statistics", {})
            content_data = content_stats.get("content_statistics", {})

            print("📄 文档统计:")
            print(f"  总文件数: {file_stats.get('total_files', 0)}")
            print(f"  总大小: {file_stats.get('total_size_human', '未知')}")
            print(f"  总字数: {content_data.get('total_words', 0):,}")
            print(f"  总行数: {content_data.get('total_lines', 0):,}")
            print()

        # 质量得分
        quality_metrics = self.analytics_data.get("quality_metrics", {})
        if quality_metrics:
            print("📈 质量评估:")
            print(f"  整体得分: {quality_metrics.get('overall_quality_score', 0):.1f}/100")
            print(f"  完整性: {quality_metrics.get('completeness_score', 0):.1f}/100")
            print(f"  一致性: {quality_metrics.get('consistency_score', 0):.1f}/100")
            print(f"  维护性: {quality_metrics.get('maintenance_score', 0):.1f}/100")
            print()

        # 主要建议
        recommendations = self.analytics_data.get("recommendations", [])
        if recommendations:
            print("💡 主要建议:")
            for rec in recommendations[:3]:
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec.get("priority", "medium"), "🟡")
                print(f"  {priority_icon} {rec.get('title', '未知')}")
            print()

        print("="*60)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="文档分析工具")
    parser.add_argument("--docs-dir", default="docs", help="文档目录路径")
    parser.add_argument("--output", help="分析报告输出路径")
    parser.add_argument("--summary", action="store_true", help="显示摘要报告")
    parser.add_argument("--full-analysis", action="store_true", help="执行完整分析")

    args = parser.parse_args()

    # 创建分析器
    analyzer = DocsAnalytics(args.docs_dir)

    # 执行分析
    if args.full_analysis:
        await analyzer.analyze_content()
        await analyzer.analyze_structure()
        analyzer.analyze_quality()
        analyzer.generate_recommendations()
    else:
        # 默认执行基础分析
        await analyzer.analyze_content()
        await analyzer.analyze_structure()
        analyzer.analyze_quality()
        analyzer.generate_recommendations()

    # 保存分析结果
    report_path = analyzer.save_analysis(args.output)

    # 显示摘要
    if args.summary:
        print(analyzer.generate_summary_report())

    # 打印控制台摘要
    analyzer.print_summary()

    print(f"\n📊 详细分析报告: {report_path}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())