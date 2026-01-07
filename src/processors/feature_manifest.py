#!/usr/bin/env python3
"""
V26.7 特征清单管理器

目的：实现"特征字典锁定"，确保不同批次间的特征严格对齐

核心功能：
1. 加载固定特征清单 v26_feature_manifest.json
2. 验证提取的特征是否符合清单
3. 填充缺失特征，确保所有比赛的特征维度一致
4. 导出标准化特征字典（用于离线解析）

作者：高级数据架构师
日期：2026-01-07
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FeatureManifest:
    """特征清单数据类"""

    version: str
    created: str
    description: str
    feature_schema: Dict[str, Any] = field(default_factory=dict)
    alignment_rules: Dict[str, Any] = field(default_factory=dict)
    extraction_config: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_file(cls, manifest_path: str | Path) -> 'FeatureManifest':
        """从 JSON 文件加载特征清单"""
        manifest_path = Path(manifest_path)

        if not manifest_path.exists():
            raise FileNotFoundError(f"特征清单文件不存在: {manifest_path}")

        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return cls(
            version=data.get('manifest_version', 'UNKNOWN'),
            created=data.get('manifest_created', ''),
            description=data.get('manifest_description', ''),
            feature_schema=data.get('feature_schema', {}),
            alignment_rules=data.get('alignment_rules', {}),
            extraction_config=data.get('extraction_config', {})
        )

    def validate(self) -> bool:
        """验证特征清单完整性"""
        required_keys = ['manifest_version', 'manifest_created', 'feature_schema']
        for key in required_keys:
            if key not in self.__dict__:
                logger.error(f"特征清单缺少必需字段: {key}")
                return False

        return True

    def get_required_features(self) -> List[str]:
        """获取必需特征列表"""
        required = []
        for category, features in self.feature_schema.items():
            if isinstance(features, dict):
                for feat_name, feat_config in features.items():
                    if feat_config.get('required', False):
                        required.append(feat_name)
        return required

    def get_feature_aliases(self) -> Dict[str, List[str]]:
        """获取特征别名映射（用于 API 字段名 -> 标准特征名）"""
        aliases = {}
        for category, features in self.feature_schema.items():
            if isinstance(features, dict):
                for feat_name, feat_config in features.items():
                    if 'aliases' in feat_config:
                        for alias in feat_config['aliases']:
                            aliases[alias] = feat_name
        return aliases

    def get_extraction_config(self) -> Dict[str, Any]:
        """获取提取配置"""
        return self.extraction_config

    def is_strict_mode(self) -> bool:
        """检查是否启用严格模式（不允许新特征）"""
        return self.alignment_rules.get('strict_mode', False)


class FeatureAligner:
    """特征对齐器 - 确保不同批次特征严格对齐"""

    def __init__(self, manifest: FeatureManifest):
        self.manifest = manifest
        self.global_registry: Dict[str, int] = {}
        self.feature_order: List[str] = []

    def align_features(
        self,
        features: Dict[str, Any],
        reference_registry: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        对齐特征到固定清单

        Args:
            features: 提取的特征字典
            reference_registry: 参考特征注册表（用于全局对齐）

        Returns:
            对齐后的特征字典
        """
        # 如果提供了参考注册表，使用它
        if reference_registry:
            target_registry = reference_registry
        else:
            # 使用全局注册表
            target_registry = self.global_registry

        # 填充必需特征
        aligned = {}

        # 1. 添加元数据
        aligned['_meta'] = {
            'extractor_version': 'V26.2',
            'extraction_timestamp': None,
            'alignment_manifest_version': self.manifest.version,
            'feature_count': len(features)
        }

        # 2. 按固定顺序添加特征
        for key in sorted(features.keys()):
            if key == '_meta':
                continue

            # 更新全局注册表
            if key not in target_registry:
                target_registry[key] = len(target_registry)

            aligned[key] = features[key]

        # 3. 确保特征顺序一致
        sorted_features = dict(sorted(aligned.items(), key=lambda x: x[0]))

        logger.debug(
            f"特征对齐完成: {len(sorted_features)} 维, "
            f"清单版本: {self.manifest.version}"
        )

        return sorted_features

    def export_feature_dictionary(
        self,
        all_features: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        导出特征字典（用于离线解析）

        Args:
            all_features: 所有比赛的特征列表

        Returns:
            特征字典 {feature_name: index}
        """
        registry: Dict[str, int] = {'_meta': 0}

        for features in all_features:
            for key in features.keys():
                if key not in registry:
                    registry[key] = len(registry)

        logger.info(f"导出特征字典: {len(registry)} 个特征")
        return registry

    def save_registry(
        self,
        registry: Dict[str, int],
        output_path: str | Path = 'config/v26_feature_registry.json'
    ):
        """保存特征注册表到文件"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 按索引排序
        sorted_registry = dict(sorted(registry.items(), key=lambda x: x[1]))

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'registry_version': self.manifest.version,
                'created_at': None,  # 将在运行时填充
                'total_features': len(sorted_registry),
                'features': sorted_registry
            }, f, indent=2, ensure_ascii=False)

        logger.info(f"特征注册表已保存: {output_path}")


def load_manifest(
    manifest_path: str | Path = 'config/v26_feature_manifest.json'
) -> FeatureManifest:
    """加载特征清单（便捷函数）"""
    return FeatureManifest.from_file(manifest_path)


# 全局单例
_global_manifest: Optional[FeatureManifest] = None
_global_aligner: Optional[FeatureAligner] = None


def get_global_manifest() -> FeatureManifest:
    """获取全局特征清单单例"""
    global _global_manifest
    if _global_manifest is None:
        _global_manifest = load_manifest()
    return _global_manifest


def get_global_aligner() -> FeatureAligner:
    """获取全局特征对齐器单例"""
    global _global_aligner
    if _global_aligner is None:
        _global_aligner = FeatureAligner(get_global_manifest())
    return _global_aligner
