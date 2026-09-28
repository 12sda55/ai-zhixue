"""数据迁移脚本 - 从硬编码数据迁移到数据库

将以下硬编码数据源迁移到 MySQL：
1. KNOWLEDGE_GRAPH → knowledge_nodes + knowledge_dependencies
2. KNOWLEDGE_TEXTS → knowledge_content
3. KNOWLEDGE_POINT_ALIASES → knowledge_aliases
4. MANIM_TEMPLATES → video_templates
5. _VISUALIZATION_CONFIGS → visualization_configs
6. ACHIEVEMENTS → achievements
7. _get_source_attribution → source_references

所有操作幂等：已存在的记录跳过，不重复插入。
"""

from __future__ import annotations

import json
import logging
import re

from sqlalchemy.orm import Session

from app.models.profile import (
    KnowledgeNodeModel,
    KnowledgeDependencyModel,
    KnowledgeContentModel,
    KnowledgeAliasModel,
    VideoTemplateModel,
    VisualizationConfigModel,
    AchievementModel,
    SourceReferenceModel,
)
from app.schemas.knowledge_graph import KNOWLEDGE_GRAPH
from app.knowledge.texts import KNOWLEDGE_TEXTS
from app.agents.teacher.dispatcher import KNOWLEDGE_POINT_ALIASES
from app.knowledge.manim_templates import MANIM_TEMPLATES
from app.services.multimodal_service import _VISUALIZATION_CONFIGS
from app.services.innovation_service import ACHIEVEMENTS
from app.services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)

# ===== Markdown section → content_type 映射 =====
_SECTION_TYPE_MAP: dict[str, str] = {
    "概念": "concept",
    "核心概念": "concept",
    "核心原理": "principle",
    "核心操作": "principle",
    "分析技巧": "principle",
    "存储方式": "principle",
    "特点": "principle",
    "四条规则": "principle",
    "旋转类型": "principle",
    "旋转示例": "code_example",
    "Python示例": "code_example",
    "示例": "code_example",
    "括号匹配示例": "code_example",
    "Dijkstra算法": "code_example",
    "Kruskal算法": "code_example",
    "常见误区": "common_mistake",
    "应用场景": "applications",
    "经典应用": "applications",
    "常见变体": "applications",
    "应用": "applications",
    "复杂度": "summary",
    "性能": "summary",
    "与数组对比": "comparison",
    "递归 vs 迭代": "comparison",
    "BFS": "concept",
    "DFS": "concept",
    "五条规则": "principle",
}


def _parse_markdown_sections(text: str) -> list[tuple[str, str]]:
    """解析 Markdown 文本，提取 ## 级别的 section

    Returns:
        [(section_name, section_content), ...]
    """
    sections: list[tuple[str, str]] = []
    current_name = ""
    current_lines: list[str] = []

    for line in text.split("\n"):
        if line.startswith("## "):
            if current_name:
                sections.append((current_name, "\n".join(current_lines).strip()))
            current_name = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_name:
        sections.append((current_name, "\n".join(current_lines).strip()))

    return sections


def _section_name_to_content_type(section_name: str) -> str:
    """将 Markdown section 名称映射为 content_type"""
    # 精确匹配
    if section_name in _SECTION_TYPE_MAP:
        return _SECTION_TYPE_MAP[section_name]

    # 模糊匹配：section_name 包含关键词
    for key, ctype in _SECTION_TYPE_MAP.items():
        if key in section_name:
            return ctype

    # 默认
    return "concept"


def seed_knowledge_data(db: Session):
    """从硬编码数据迁移到数据库，幂等执行"""
    _seed_knowledge_nodes(db)
    _seed_knowledge_dependencies(db)
    _seed_knowledge_content(db)
    _seed_knowledge_aliases(db)
    _seed_video_templates(db)
    _seed_visualization_configs(db)
    _seed_achievements(db)
    _seed_source_references(db)


def _seed_knowledge_nodes(db: Session):
    """从 KNOWLEDGE_GRAPH 创建 KnowledgeNodeModel 记录"""
    for idx, node_def in enumerate(KNOWLEDGE_GRAPH):
        existing = db.query(KnowledgeNodeModel).filter(
            KnowledgeNodeModel.id == node_def.id
        ).first()
        if existing:
            logger.debug("知识点节点已存在，跳过: %s", node_def.id)
            continue

        model = KnowledgeNodeModel(
            id=node_def.id,
            name=node_def.name,
            category=node_def.category,
            description=node_def.description,
            optional=node_def.optional,
            sort_order=idx,
        )
        db.add(model)
        logger.info("插入知识点节点: %s (%s)", node_def.id, node_def.name)

    db.commit()


def _seed_knowledge_dependencies(db: Session):
    """从 KNOWLEDGE_GRAPH 的 dependencies 字段创建 KnowledgeDependencyModel"""
    for node_def in KNOWLEDGE_GRAPH:
        for dep_id in node_def.dependencies:
            existing = db.query(KnowledgeDependencyModel).filter(
                KnowledgeDependencyModel.node_id == node_def.id,
                KnowledgeDependencyModel.dependency_id == dep_id,
            ).first()
            if existing:
                logger.debug("依赖关系已存在，跳过: %s → %s", node_def.id, dep_id)
                continue

            model = KnowledgeDependencyModel(
                node_id=node_def.id,
                dependency_id=dep_id,
            )
            db.add(model)
            logger.info("插入依赖关系: %s → %s", node_def.id, dep_id)

    db.commit()


def _seed_knowledge_content(db: Session):
    """从 KNOWLEDGE_TEXTS 解析 Markdown sections 并创建 KnowledgeContentModel"""
    for node_id, text in KNOWLEDGE_TEXTS.items():
        sections = _parse_markdown_sections(text)

        for sort_order, (section_name, section_content) in enumerate(sections):
            content_type = _section_name_to_content_type(section_name)

            if not section_content:
                continue

            existing = db.query(KnowledgeContentModel).filter(
                KnowledgeContentModel.node_id == node_id,
                KnowledgeContentModel.content_type == content_type,
            ).first()
            if existing:
                logger.debug("知识内容已存在，跳过: %s/%s", node_id, content_type)
                continue

            model = KnowledgeContentModel(
                node_id=node_id,
                content_type=content_type,
                content=section_content,
                sort_order=sort_order,
            )
            db.add(model)
            logger.info("插入知识内容: %s/%s", node_id, content_type)

    db.commit()


def _seed_knowledge_aliases(db: Session):
    """从 KNOWLEDGE_POINT_ALIASES 创建 KnowledgeAliasModel

    KNOWLEDGE_POINT_ALIASES 格式: {alias: node_id}
    """
    for alias, node_id in KNOWLEDGE_POINT_ALIASES.items():
        existing = db.query(KnowledgeAliasModel).filter(
            KnowledgeAliasModel.alias == alias
        ).first()
        if existing:
            logger.debug("别名已存在，跳过: %s", alias)
            continue

        model = KnowledgeAliasModel(
            alias=alias,
            node_id=node_id,
        )
        db.add(model)
        logger.info("插入别名: %s → %s", alias, node_id)

    db.commit()


def _seed_video_templates(db: Session):
    """从 MANIM_TEMPLATES 创建 VideoTemplateModel

    MANIM_TEMPLATES 格式: {node_id: {"scene_class": str, "script": str, "narrations": list[str]}}
    """
    for node_id, template in MANIM_TEMPLATES.items():
        template_id = f"manim_{node_id}"

        existing = db.query(VideoTemplateModel).filter(
            VideoTemplateModel.id == template_id
        ).first()
        if existing:
            logger.debug("视频模板已存在，跳过: %s", template_id)
            continue

        narrations = template.get("narrations", [])
        model = VideoTemplateModel(
            id=template_id,
            node_id=node_id,
            scene_class=template.get("scene_class", ""),
            script=template.get("script", ""),
            narrations_json=json.dumps(narrations, ensure_ascii=False),
            duration_estimate=90,
            difficulty=1,
            is_default=True,
        )
        db.add(model)
        logger.info("插入视频模板: %s", template_id)

    db.commit()


def _seed_visualization_configs(db: Session):
    """从 _VISUALIZATION_CONFIGS 创建 VisualizationConfigModel

    _VISUALIZATION_CONFIGS 格式: {node_id: {"component_type": str, "data_schema": dict, "controls": dict}}
    """
    for node_id, config in _VISUALIZATION_CONFIGS.items():
        config_id = f"viz_{node_id}"

        existing = db.query(VisualizationConfigModel).filter(
            VisualizationConfigModel.id == config_id
        ).first()
        if existing:
            logger.debug("可视化配置已存在，跳过: %s", config_id)
            continue

        model = VisualizationConfigModel(
            id=config_id,
            node_id=node_id,
            component_type=config.get("component_type", ""),
            data_schema_json=json.dumps(config.get("data_schema", {}), ensure_ascii=False),
            controls_json=json.dumps(config.get("controls", {}), ensure_ascii=False),
            step_templates_json="",
        )
        db.add(model)
        logger.info("插入可视化配置: %s", config_id)

    db.commit()


def _seed_achievements(db: Session):
    """从 ACHIEVEMENTS 创建 AchievementModel

    ACHIEVEMENTS 格式: list[Achievement]，每个有 id, name, description, icon
    """
    for idx, ach in enumerate(ACHIEVEMENTS):
        existing = db.query(AchievementModel).filter(
            AchievementModel.id == ach.id
        ).first()
        if existing:
            logger.debug("成就已存在，跳过: %s", ach.id)
            continue

        model = AchievementModel(
            id=ach.id,
            name=ach.name,
            description=ach.description,
            icon=ach.icon,
            category="",
            condition_json="",
            sort_order=idx,
        )
        db.add(model)
        logger.info("插入成就: %s (%s)", ach.id, ach.name)

    db.commit()


def _seed_source_references(db: Session):
    """从 _get_source_attribution 创建 SourceReferenceModel

    _get_source_attribution 返回格式:
    "《算法导论》第3版 第2章 | 严蔚敏《数据结构》第2章 线性表 | LeetCode Hot 100"
    按 | 分割后逐条插入。
    """
    ks = KnowledgeService()

    # 收集所有需要迁移的 node_id（KNOWLEDGE_GRAPH 中的 + _get_source_attribution 中的）
    all_node_ids = {node.id for node in KNOWLEDGE_GRAPH}

    for node_id in all_node_ids:
        source_str = ks._get_source_attribution(node_id)
        if not source_str:
            continue

        # 检查该 node_id 是否已有 source references
        existing_count = db.query(SourceReferenceModel).filter(
            SourceReferenceModel.node_id == node_id
        ).count()
        if existing_count > 0:
            logger.debug("来源参考已存在，跳过: %s", node_id)
            continue

        # 按 | 分割
        parts = [p.strip() for p in source_str.split("|") if p.strip()]

        for sort_order, part in enumerate(parts):
            # 尝试识别来源类型
            source_type = ""
            if "算法导论" in part:
                source_type = "textbook"
            elif "严蔚敏" in part:
                source_type = "textbook"
            elif "LeetCode" in part:
                source_type = "practice"
            elif "王道" in part:
                source_type = "textbook"

            model = SourceReferenceModel(
                node_id=node_id,
                source_type=source_type,
                title=part,
                detail=part,
                url="",
                sort_order=sort_order,
            )
            db.add(model)
            logger.info("插入来源参考: %s - %s", node_id, part[:30])

    db.commit()
