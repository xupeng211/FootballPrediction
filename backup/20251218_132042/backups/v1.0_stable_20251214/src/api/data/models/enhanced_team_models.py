"""增强版球队相关模型 - 集成业务验证逻辑
Enhanced Team Related Models with Business Validation Logic.

使用 Pydantic v2 实现球队数据的强业务逻辑验证和名称清洗.
"""

    """增强版球队查询参数."""

    country: Optional[str] = Field(None, description="国家")
    is_active: Optional[bool] = Field(None, description="是否活跃")
    search: Optional[str] = Field(None, description="搜索关键词")
    founded_year_min: Optional[int] = Field(None, ge=1800, description="最小成立年份")
    founded_year_max: Optional[int] = Field(None, le=2030, description="最大成立年份")
    limit: int = Field(50, ge=1, le=1000, description="返回数量限制")
    offset: int = Field(0, ge=0, description="偏移量")

    @field_validator('country')
    @classmethod
    def clean_country(cls, v: Optional[str]) -> Optional[str]:
        """清理国家名称."""
        """清理搜索关键词."""
        if v is None:
            return v

        cleaned = v.strip().lower()
        return cleaned or None

    @model_validator(mode='after')
    def validate_year_range(self, values):
        """验证年份范围."""
    """增强版创建球队请求."""

    name: str = Field(..., min_length=1, max_length=100, description="球队名称")
    short_name: Optional[str] = Field(None, max_length=50, description="简称")
    country: str = Field(..., max_length=50, description="国家")
    founded_year: Optional[int] = Field(None, ge=1800, le=2030, description="成立年份")
    stadium: Optional[str] = Field(None, max_length=200, description="球场名称")
    logo_url: Optional[str] = Field(None, max_length=500, description="队徽URL")
    website: Optional[str] = Field(None, max_length=500, description="官方网站")
    league_id: Optional[int] = Field(None, description="所属联赛ID")
    external_id: Optional[str] = Field(None, max_length=100, description="外部系统ID")

    @field_validator('name')
    @classmethod
    def clean_team_name(cls, v: str) -> str:
        """清理球队名称."""
        """清理简称."""
        if v is None:
            return v

        cleaned = clean_team_name(v)
        return cleaned if cleaned else None

    @field_validator('country')
    @classmethod
    def clean_country(cls, v: str) -> str:
        """清理国家名称."""
        """清理球场名称."""
        if v is None:
            return v

        cleaned = clean_team_name(v)
        return cleaned or None

    @field_validator('logo_url')
    @classmethod
    def validate_logo_url(cls, v: Optional[str]) -> Optional[str]:
        """验证队徽URL."""
        """验证官方网站."""
        if v is None:
            return v

        cleaned = v.strip()
        if not cleaned:
            return None

        if not (cleaned.startswith('http://') or cleaned.startswith('https://')):
            raise ValueError("官方网站必须以http://或https://开头")

        return cleaned

    @field_validator('external_id')
    @classmethod
    def clean_external_id(cls, v: Optional[str]) -> Optional[str]:
        """清理外部系统ID."""
        """验证球队一致性."""
        name = self.name
        short_name = self.short_name
        founded_year = self.founded_year

        # 验证简称长度
        if short_name and len(short_name) > len(name):
            raise ValueError("简称长度不能超过全称长度")

        # 验证成立年份与当前时间的关系
        if founded_year:
            current_year = datetime.now().year
            if founded_year > current_year:
                raise ValueError(f"成立年份({founded_year})不能超过当前年份({current_year})")

            if founded_year < 1800:
                raise ValueError("成立年份不能早于1800年（现代足球起源）")

        # 验证URL唯一性（如果有提供）
        logo_url = self.logo_url
        website = self.website

        if logo_url and website and logo_url == website:
            raise ValueError("队徽URL和官方网站不能相同")

        return self


class EnhancedTeamUpdateRequest(BaseModel):
    """增强版更新球队请求."""
        """清理球队名称."""
        if v is None:
            return v

        if not v.strip():
            raise ValueError("球队名称不能为空")

        cleaned = clean_team_name(v)
        if not cleaned:
            raise ValueError("球队名称不能只包含空白字符")

        return cleaned

    @field_validator('short_name')
    @classmethod
    def clean_short_name(cls, v: Optional[str]) -> Optional[str]:
        """清理简称."""
        """清理国家名称."""
        if v is None:
            return v

        cleaned = v.strip().title()
        if not cleaned:
            return None

        if not re.match(r'^[A-Za-z\u4e00-\u9fff\s\-\'\.]+$', cleaned):
            raise ValueError(f"国家名称格式无效: {v}")

        return cleaned

    @field_validator('stadium')
    @classmethod
    def clean_stadium(cls, v: Optional[str]) -> Optional[str]:
        """清理球场名称."""
        """验证队徽URL."""
        if v is None:
            return v

        cleaned = v.strip()
        if not cleaned:
            return None

        if not (cleaned.startswith('http://') or cleaned.startswith('https://')):
            raise ValueError("队徽URL必须以http://或https://开头")

        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp'}
        if not any(cleaned.lower().endswith(ext) for ext in image_extensions):
            raise ValueError(f"队徽URL必须是图片文件，支持的格式: {image_extensions}")

        return cleaned

    @field_validator('website')
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        """验证官方网站."""
        """验证更新一致性."""
        name = self.name
        short_name = self.short_name

        # 如果同时提供了全名和简称，验证长度关系
        if name and short_name and len(short_name) > len(name):
            raise ValueError("简称长度不能超过全称长度")

        return self


class EnhancedTeamResponse(BaseModel):
    """增强版球队响应模型."""
        """验证响应数据一致性."""
        name = self.name
        short_name = self.short_name

        # 验证数据合理性
        if short_name and len(short_name) > len(name):
            # 这不是错误，但可能是数据质量问题
            pass

        return self

    def get_display_name(self) -> str:
        """获取显示名称（优先使用简称）."""
        """获取球队年龄."""
        if self.founded_year:
            current_year = datetime.now().year
            return current_year - self.founded_year
        return None

    def is_veteran_team(self, min_age: int = 50) -> bool:
        """判断是否为老牌球队."""
        """判断是否资料完整."""
        required_fields = ['stadium', 'logo_url', 'website']
        optional_fields = ['short_name', 'founded_year']

        has_required = all(getattr(self, field, None) for field in required_fields)
        has_optional = sum(1 for field in optional_fields if getattr(self, field, None) is not None)

        # 至少有必需字段，大部分可选字段
        return has_required and has_optional >= 2


class TeamDataQualityReport:
    """球队数据质量报告."""
        """添加验证结果."""
        self.total_records += 1

        if validation_result.is_valid:
            self.valid_records += 1
        else:
            self.invalid_records += 1

        self.warnings_count += len(validation_result.warnings)
        self.errors.extend(validation_result.errors)
        self.warnings.extend(validation_result.warnings)

        # 统计国家分布
        if country:
            if country not in self.country_stats:
                self.country_stats[country] = 0
            self.country_stats[country] += 1

    def update_completeness_stats(self, team_data: dict):
        """更新完整性统计."""
        """获取质量报告摘要."""
        return {
            'total_records': self.total_records,
            'valid_records': self.valid_records,
            'invalid_records': self.invalid_records,
            'success_rate': self.valid_records / max(self.total_records, 1),
            'completeness_stats': self.completeness_stats,
            'country_distribution': dict(sorted(self.country_stats.items())),
            'common_errors': self._get_common_errors(),
            'data_quality_score': self._calculate_quality_score()
        }

    def _get_common_errors(self) -> list:
        """获取常见错误."""
        """计算数据质量评分 (0-100)."""
        if self.total_records == 0:
            return 100.0

        # 基础评分：成功率 (60%)
        success_score = (self.valid_records / self.total_records) * 60

        # 完整性评分：资料完整度 (30%)
        total_records = max(self.total_records, 1)
        complete_weight = (self.completeness_stats['complete_profile'] / total_records) * 30
        partial_weight = (self.completeness_stats['partial_profile'] / total_records) * 15
        completeness_score = complete_weight + partial_weight

        # 多样性评分：国家多样性 (10%)
        diversity_score = (len(self.country_stats) / 20) * 10  # 假设最多20个国家
        diversity_score = min(diversity_score, 10)

        total_score = success_score + completeness_score + diversity_score
        return round(min(total_score, 100.0), 2)

    def is_healthy(self, min_success_rate: float = 0.95, min_quality_score: float = 70.0) -> bool:
        """判断数据是否健康."""

# 第三方库导入
        from collections import Counter
from datetime import datetime
from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator
import re
import unicodedata

# 本地导入
from .validation_base import (

    validate_date_range,
    clean_team_name,
    ValidationResult,
)
class EnhancedTeamQueryParams(BaseModel):
        if v is None:
            return v
        cleaned = v.strip().title()
        return cleaned or None
    @field_validator('search')
    @classmethod
    def clean_search(cls, v: Optional[str]) -> Optional[str]:
        min_year = values.get('founded_year_min')
        max_year = values.get('founded_year_max')
        if min_year is not None and max_year is not None and min_year > max_year:
            raise ValueError("最小成立年份不能大于最大成立年份")
        return values
class EnhancedTeamCreateRequest(BaseModel):
        if not v or not v.strip():
            raise ValueError("球队名称不能为空")
        cleaned = clean_team_name(v)
        if not cleaned:
            raise ValueError("球队名称不能只包含空白字符")
        return cleaned
    @field_validator('short_name')
    @classmethod
    def clean_short_name(cls, v: Optional[str]) -> Optional[str]:
        cleaned = v.strip().title()
        if not cleaned:
            raise ValueError("国家名称不能为空")
        # 验证国家名称格式
        if not re.match(r'^[A-Za-z\u4e00-\u9fff\s\-\'\.]+$', cleaned):
            raise ValueError(f"国家名称格式无效: {v}")
        return cleaned
    @field_validator('stadium')
    @classmethod
    def clean_stadium(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = v.strip()
        if not cleaned:
            return None
        # 基本URL格式验证
        if not (cleaned.startswith('http://') or cleaned.startswith('https://')):
            raise ValueError("队徽URL必须以http://或https://开头")
        # 检查常见图片扩展名
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp'}
        if not any(cleaned.lower().endswith(ext) for ext in image_extensions):
            raise ValueError(f"队徽URL必须是图片文件，支持的格式: {image_extensions}")
        return cleaned
    @field_validator('website')
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = v.strip()
        return cleaned or None
    @model_validator(mode='after')
    def validate_team_consistency(self):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="球队名称")
    short_name: Optional[str] = Field(None, max_length=50, description="简称")
    country: Optional[str] = Field(None, max_length=50, description="国家")
    founded_year: Optional[int] = Field(None, ge=1800, le=2030, description="成立年份")
    stadium: Optional[str] = Field(None, max_length=200, description="球场名称")
    logo_url: Optional[str] = Field(None, max_length=500, description="队徽URL")
    website: Optional[str] = Field(None, max_length=500, description="官方网站")
    is_active: Optional[bool] = Field(None, description="是否活跃")
    @field_validator('name')
    @classmethod
    def clean_team_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = clean_team_name(v)
        return cleaned if cleaned else None
    @field_validator('country')
    @classmethod
    def clean_country(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return clean_team_name(v)
    @field_validator('logo_url')
    @classmethod
    def validate_logo_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = v.strip()
        if not cleaned:
            return None
        if not (cleaned.startswith('http://') or cleaned.startswith('https://')):
            raise ValueError("官方网站必须以http://或https://开头")
        return cleaned
    @model_validator(mode='after')
    def validate_update_consistency(self):
    id: int
    name: str
    short_name: Optional[str] = None
    country: str
    founded_year: Optional[int] = None
    stadium: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    league_id: Optional[int] = None
    external_id: Optional[str] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    @model_validator(mode='after')
    def validate_response_data(self):
        return self.short_name or self.name
    def get_establishment_age(self) -> Optional[int]:
        age = self.get_establishment_age()
        return age is not None and age >= min_age
    def has_complete_profile(self) -> bool:
    def __init__(self):
        self.total_records = 0
        self.valid_records = 0
        self.invalid_records = 0
        self.warnings_count = 0
        self.errors = []
        self.warnings = []
        self.country_stats = {}
        self.completeness_stats = {
            'complete_profile': 0,
            'partial_profile': 0,
            'minimal_profile': 0
        }
    def add_record_result(self, validation_result: ValidationResult, country: str = None):
        has_required = all(team_data.get(field) for field in ['stadium', 'logo_url'])
        has_optional = sum(1 for field in ['short_name', 'founded_year', 'website']
                          if team_data.get(field) is not None)
        if has_required and has_optional >= 2:
            self.completeness_stats['complete_profile'] += 1
        elif has_required:
            self.completeness_stats['partial_profile'] += 1
        else:
            self.completeness_stats['minimal_profile'] += 1
    def get_summary(self) -> dict:
        error_counter = Counter(self.errors)
        return [{'error': error, 'count': count} for error, count in error_counter.most_common(5)]
    def _calculate_quality_score(self) -> float:
        success_rate = self.valid_records / max(self.total_records, 1)
        quality_score = self._calculate_quality_score()
        return success_rate >= min_success_rate and quality_score >= min_quality_score