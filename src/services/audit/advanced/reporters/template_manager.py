"""
模板管理器
Template Manager

管理审计报告的模板和样式。
"""



logger = get_logger(__name__)


class TemplateManager:
    """
    模板管理器 / Template Manager

    管理报告模板的创建、加载和应用。
    Manages creation, loading, and application of report templates.
    """

    def __init__(self):
        """初始化模板管理器 / Initialize Template Manager"""
        self.logger = get_logger(f"audit.{self.__class__.__name__}")

        # 内置模板
        self.built_in_templates = {
            "standard_audit": {
                "name": "标准审计模板",
                "description": "标准的审计报告模板",
                "sections": [
                    "executive_summary",
                    "audit_overview",
                    "findings",
                    "recommendations",
                    "appendices"
                ],
                "style": "professional",
            },
            "security_focused": {
                "name": "安全重点模板",
                "description": "专注于安全方面的审计模板",
                "sections": [
                    "security_summary",
                    "threat_analysis",
                    "vulnerability_assessment",
                    "risk_mitigation",
                    "compliance_status"
                ],
                "style": "security",
            },
            "compliance_template": {
                "name": "合规模板",
                "description": "合规性审计专用模板",
                "sections": [
                    "compliance_overview",
                    "requirement_analysis",
                    "gap_assessment",
                    "remediation_plan",
                    "evidence_documentation"
                ],
                "style": "compliance",
            },
            "executive_template": {
                "name": "高管报告模板",
                "description": "为高管准备的简化审计模板",
                "sections": [
                    "executive_summary",
                    "key_metrics",
                    "critical_findings",
                    "strategic_recommendations"
                ],
                "style": "executive",
            },
        }

        # 样式配置
        self.styles = {
            "professional": {
                "primary_color": "#2c3e50",
                "secondary_color": "#3498db",
                "font_family": "Arial, sans-serif",
                "font_size": "12px",
                "header_size": "18px",
                "margin": "20px",
                "padding": "15px",
            },
            "security": {
                "primary_color": "#c0392b",
                "secondary_color": "#e74c3c",
                "font_family": "Courier New, monospace",
                "font_size": "11px",
                "header_size": "16px",
                "margin": "15px",
                "padding": "10px",
            },
            "compliance": {
                "primary_color": "#27ae60",
                "secondary_color": "#2ecc71",
                "font_family": "Times New Roman, serif",
                "font_size": "12px",
                "header_size": "17px",
                "margin": "25px",
                "padding": "20px",
            },
            "executive": {
                "primary_color": "#8e44ad",
                "secondary_color": "#9b59b6",
                "font_family": "Helvetica, sans-serif",
                "font_size": "14px",
                "header_size": "20px",
                "margin": "30px",
                "padding": "25px",
            },
        }

        # 自定义模板存储
        self.custom_templates: Dict[str, Dict[str, Any]] = {}

    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        获取模板 / Get Template

        Args:
            template_name: 模板名称 / Template name

        Returns:
            Optional[Dict[str, Any]]: 模板配置 / Template configuration
        """
        # 先检查内置模板
        if template_name in self.built_in_templates:
            return self.built_in_templates[template_name]

        # 检查自定义模板
        if template_name in self.custom_templates:
            return self.custom_templates[template_name]

        self.logger.warning(f"未找到模板: {template_name}")
        return None

    def create_template(
        self,
        name: str,
        description: str,
        sections: List[str],
        style: str = "professional",
        custom_styles: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        创建自定义模板 / Create Custom Template

        Args:
            name: 模板名称 / Template name
            description: 模板描述 / Template description
            sections: 章节列表 / Sections list
            style: 样式名称 / Style name
            custom_styles: 自定义样式 / Custom styles

        Returns:
            bool: 创建是否成功 / Whether creation was successful
        """
        try:
            # 验证参数
            if not name or not sections:
                self.logger.error("模板名称和章节列表不能为空")
                return False

            if style not in self.styles:
                self.logger.warning(f"未知样式: {style}，使用默认样式")
                style = "professional"

            # 创建模板
            template = {
                "name": name,
                "description": description,
                "sections": sections,
                "style": style,
                "custom_styles": custom_styles or {},
                "created_at": datetime.now().isoformat(),
                "version": "1.0.0",
            }

            # 保存模板
            self.custom_templates[name] = template

            self.logger.info(f"自定义模板已创建: {name}")
            return True

        except Exception as e:
            self.logger.error(f"创建模板失败: {e}")
            return False

    def apply_template(
        self,
        template_name: str,
        data: Dict[str, Any],
        report_type: str = "standard"
    ) -> Dict[str, Any]:
        """
        应用模板 / Apply Template

        Args:
            template_name: 模板名称 / Template name
            data: 报告数据 / Report data
            report_type: 报告类型 / Report type

        Returns:
            Dict[str, Any]: 应用模板后的报告 / Report with template applied
        """
        template = self.get_template(template_name)
        if not template:
            self.logger.error(f"无法应用模板: {template_name}")
            return data

        try:
            # 获取样式配置
            style_name = template.get("style", "professional")
            style_config = self.styles.get(style_name, self.styles["professional"])
            custom_styles = template.get("custom_styles", {})

            # 合并样式
            final_styles = {**style_config, **custom_styles}

            # 构建报告结构
            structured_report = {
                "title": self._generate_title(data, template, report_type),
                "template_info": {
                    "name": template["name"],
                    "description": template["description"],
                    "style": style_name,
                },
                "styles": final_styles,
                "sections": self._build_sections(data, template["sections"]),
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "template_version": template.get("version", "1.0.0"),
                    "report_type": report_type,
                },
            }

            return structured_report

        except Exception as e:
            self.logger.error(f"应用模板失败: {e}")
            return data

    def _generate_title(
        self,
        data: Dict[str, Any],
        template: Dict[str, Any],
        report_type: str
    ) -> str:
        """
        生成标题 / Generate Title

        Args:
            data: 数据 / Data
            template: 模板 / Template
            report_type: 报告类型 / Report type

        Returns:
            str: 标题 / Title
        """
        base_title = template["name"]

        # 根据报告类型添加后缀
        type_suffixes = {
            "user_activity": "用户活动报告",
            "security_summary": "安全摘要报告",
            "compliance_report": "合规报告",
            "risk_assessment": "风险评估报告",
            "performance_metrics": "性能指标报告",
        }

        suffix = type_suffixes.get(report_type, "审计报告")
        return f"{base_title} - {suffix}"

    def _build_sections(
        self,
        data: Dict[str, Any],
        section_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        构建章节 / Build Sections

        Args:
            data: 数据 / Data
            section_names: 章节名称列表 / Section names list

        Returns:
            List[Dict[str, Any]]: 章节列表 / Sections list
        """
        sections = []

        for section_name in section_names:
            section = self._build_section(section_name, data)
            if section:
                sections.append(section)

        return sections

    def _build_section(self, section_name: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        构建单个章节 / Build Single Section

        Args:
            section_name: 章节名称 / Section name
            data: 数据 / Data

        Returns:
            Optional[Dict[str, Any]]: 章节内容 / Section content
        """
        section_builders = {
            "executive_summary": self._build_executive_summary,
            "audit_overview": self._build_audit_overview,
            "findings": self._build_findings,
            "recommendations": self._build_recommendations,
            "appendices": self._build_appendices,
            "security_summary": self._build_security_summary,
            "threat_analysis": self._build_threat_analysis,
            "vulnerability_assessment": self._build_vulnerability_assessment,
            "risk_mitigation": self._build_risk_mitigation,
            "compliance_status": self._build_compliance_status,
            "compliance_overview": self._build_compliance_overview,
            "requirement_analysis": self._build_requirement_analysis,
            "gap_assessment": self._build_gap_assessment,
            "remediation_plan": self._build_remediation_plan,
            "evidence_documentation": self._build_evidence_documentation,
            "key_metrics": self._build_key_metrics,
            "critical_findings": self._build_critical_findings,
            "strategic_recommendations": self._build_strategic_recommendations,
        }

        builder = section_builders.get(section_name)
        if builder:
            return builder(data)
        else:
            # 默认章节
            return {
                "name": section_name,
                "title": section_name.replace("_", " ").title(),
                "content": data.get(section_name, {}),
                "type": "default",
            }

    def _build_executive_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建高管摘要 / Build Executive Summary"""
        return {
            "name": "executive_summary",
            "title": "高管摘要",
            "content": {
                "overview": data.get("summary", {}),
                "key_findings": data.get("key_findings", []),
                "risk_assessment": data.get("risk_assessment", {}),
                "next_steps": data.get("next_steps", []),
            },
            "type": "summary",
        }

    def _build_audit_overview(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建审计概览 / Build Audit Overview"""
        return {
            "name": "audit_overview",
            "title": "审计概览",
            "content": {
                "scope": data.get("scope", {}),
                "methodology": data.get("methodology", {}),
                "period": data.get("period", {}),
                "coverage": data.get("coverage", {}),
            },
            "type": "overview",
        }

    def _build_findings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建发现 / Build Findings"""
        return {
            "name": "findings",
            "title": "审计发现",
            "content": {
                "findings": data.get("findings", []),
                "observations": data.get("observations", []),
                "issues": data.get("issues", []),
            },
            "type": "findings",
        }

    def _build_recommendations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建建议 / Build Recommendations"""
        return {
            "name": "recommendations",
            "title": "建议",
            "content": {
                "recommendations": data.get("recommendations", []),
                "priorities": data.get("priorities", []),
                "implementation_plan": data.get("implementation_plan", {}),
            },
            "type": "recommendations",
        }

    def _build_appendices(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建附录 / Build Appendices"""
        return {
            "name": "appendices",
            "title": "附录",
            "content": {
                "raw_data": data.get("raw_data", {}),
                "detailed_analysis": data.get("detailed_analysis", {}),
                "supporting_documents": data.get("supporting_documents", []),
            },
            "type": "appendices",
        }

    def _build_security_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建安全摘要 / Build Security Summary"""
        return {
            "name": "security_summary",
            "title": "安全摘要",
            "content": {
                "security_overview": data.get("security_overview", {}),
                "incident_summary": data.get("incident_summary", {}),
                "security_metrics": data.get("security_metrics", {}),
            },
            "type": "security_summary",
        }

    def _build_threat_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建威胁分析 / Build Threat Analysis"""
        return {
            "name": "threat_analysis",
            "title": "威胁分析",
            "content": {
                "identified_threats": data.get("threats", []),
                "threat_landscape": data.get("threat_landscape", {}),
                "risk_assessment": data.get("risk_assessment", {}),
            },
            "type": "analysis",
        }

    def _build_vulnerability_assessment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建漏洞评估 / Build Vulnerability Assessment"""
        return {
            "name": "vulnerability_assessment",
            "title": "漏洞评估",
            "content": {
                "vulnerabilities": data.get("vulnerabilities", []),
                "severity_distribution": data.get("severity_distribution", {}),
                "remediation_priority": data.get("remediation_priority", []),
            },
            "type": "assessment",
        }

    def _build_risk_mitigation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建风险缓解 / Build Risk Mitigation"""
        return {
            "name": "risk_mitigation",
            "title": "风险缓解措施",
            "content": {
                "mitigation_strategies": data.get("mitigation_strategies", []),
                "controls": data.get("controls", []),
                "monitoring_plan": data.get("monitoring_plan", {}),
            },
            "type": "mitigation",
        }

    def _build_compliance_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建合规状态 / Build Compliance Status"""
        return {
            "name": "compliance_status",
            "title": "合规状态",
            "content": {
                "compliance_score": data.get("compliance_score", 0),
                "requirement_status": data.get("requirement_status", {}),
                "gaps": data.get("gaps", []),
            },
            "type": "compliance",
        }

    def _build_compliance_overview(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建合规概览 / Build Compliance Overview"""
        return {
            "name": "compliance_overview",
            "title": "合规概览",
            "content": {
                "framework": data.get("framework", {}),
                "scope": data.get("compliance_scope", {}),
                "overview": data.get("compliance_overview", {}),
            },
            "type": "overview",
        }

    def _build_requirement_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建需求分析 / Build Requirement Analysis"""
        return {
            "name": "requirement_analysis",
            "title": "需求分析",
            "content": {
                "requirements": data.get("requirements", []),
                "analysis": data.get("requirement_analysis", {}),
                "mapping": data.get("requirement_mapping", {}),
            },
            "type": "analysis",
        }

    def _build_gap_assessment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建差距评估 / Build Gap Assessment"""
        return {
            "name": "gap_assessment",
            "title": "差距评估",
            "content": {
                "gaps": data.get("gaps", []),
                "impact_analysis": data.get("gap_impact", {}),
                "prioritization": data.get("gap_prioritization", []),
            },
            "type": "assessment",
        }

    def _build_remediation_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建修复计划 / Build Remediation Plan"""
        return {
            "name": "remediation_plan",
            "title": "修复计划",
            "content": {
                "plan": data.get("remediation_plan", {}),
                "timeline": data.get("remediation_timeline", {}),
                "resources": data.get("remediation_resources", {}),
            },
            "type": "plan",
        }

    def _build_evidence_documentation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建证据文档 / Build Evidence Documentation"""
        return {
            "name": "evidence_documentation",
            "title": "证据文档",
            "content": {
                "evidence": data.get("evidence", {}),
                "documentation": data.get("documentation", []),
                "artifacts": data.get("artifacts", []),
            },
            "type": "documentation",
        }

    def _build_key_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建关键指标 / Build Key Metrics"""
        return {
            "name": "key_metrics",
            "title": "关键指标",
            "content": {
                "metrics": data.get("key_metrics", {}),
                "kpi": data.get("kpi", {}),
                "performance_indicators": data.get("performance_indicators", []),
            },
            "type": "metrics",
        }

    def _build_critical_findings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建关键发现 / Build Critical Findings"""
        return {
            "name": "critical_findings",
            "title": "关键发现",
            "content": {
                "critical_findings": data.get("critical_findings", []),
                "high_priority_issues": data.get("high_priority_issues", []),
                "immediate_actions": data.get("immediate_actions", []),
            },
            "type": "findings",
        }

    def _build_strategic_recommendations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建战略建议 / Build Strategic Recommendations"""
        return {
            "name": "strategic_recommendations",
            "title": "战略建议",
            "content": {
                "strategic_recommendations": data.get("strategic_recommendations", []),
                "long_term_plans": data.get("long_term_plans", []),
                "strategic_initiatives": data.get("strategic_initiatives", []),
            },
            "type": "recommendations",
        }

    def list_templates(self) -> Dict[str, Dict[str, str]]:
        """
        列出所有模板 / List All Templates

        Returns:
            Dict[str, Dict[str, str]]: 模板列表 / Template list
        """
        templates = {}

        # 添加内置模板
        for name, template in self.built_in_templates.items():
            templates[name] = {
                "name": template["name"],
                "description": template["description"],
                "type": "built_in",
                "style": template.get("style", "professional"),
            }

        # 添加自定义模板
        for name, template in self.custom_templates.items():
            templates[name] = {
                "name": template["name"],
                "description": template["description"],
                "type": "custom",
                "style": template.get("style", "professional"),
                "created_at": template.get("created_at", ""),
            }

        return templates

    def delete_template(self, template_name: str) -> bool:
        """
        删除模板 / Delete Template

        Args:
            template_name: 模板名称 / Template name

        Returns:
            bool: 删除是否成功 / Whether deletion was successful
        """
        if template_name in self.built_in_templates:
            self.logger.error("不能删除内置模板")
            return False

        if template_name in self.custom_templates:
            del self.custom_templates[template_name]
            self.logger.info(f"自定义模板已删除: {template_name}")
            return True

        self.logger.warning(f"未找到要删除的模板: {template_name}")
        return False

    def update_template(
        self,
        template_name: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        更新模板 / Update Template

        Args:
            template_name: 模板名称 / Template name
            updates: 更新内容 / Updates

        Returns:
            bool: 更新是否成功 / Whether update was successful
        """
        if template_name in self.built_in_templates:
            self.logger.error("不能更新内置模板")
            return False

        if template_name in self.custom_templates:
            self.custom_templates[template_name].update(updates)
            self.custom_templates[template_name]["updated_at"] = datetime.now().isoformat()
            self.logger.info(f"自定义模板已更新: {template_name}")
            return True

        self.logger.warning(f"未找到要更新的模板: {template_name}")
        return False

    def export_template(self, template_name: str) -> Optional[str]:
        """
        导出模板 / Export Template

        Args:
            template_name: 模板名称 / Template name

        Returns:
            Optional[str]: 模板JSON字符串 / Template JSON string
        """
        template = self.get_template(template_name)
        if template:
            return json.dumps(template, indent=2, ensure_ascii=False)
        return None

    def import_template(self, template_json: str) -> bool:
        """
        导入模板 / Import Template

        Args:
            template_json: 模板JSON字符串 / Template JSON string

        Returns:
            bool: 导入是否成功 / Whether import was successful
        """
        try:
            template_data = json.loads(template_json)
            name = template_data.get("name")



            if not name:
                self.logger.error("模板名称不能为空")
                return False

            # 如果模板已存在，添加时间戳避免冲突
            if name in self.custom_templates:
                name = f"{name}_{int(time.time())}"

            self.custom_templates[name] = template_data
            self.logger.info(f"模板已导入: {name}")
            return True

        except Exception as e:
            self.logger.error(f"导入模板失败: {e}")
            return False