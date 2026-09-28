"""资源关联网络 — 以学习路径为骨架，将所有资源挂在路径节点上

一个知识点对应一个资源包（文档+习题+视频+阅读+代码）
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
import logging

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class ResourcePackage:
    """知识点资源包"""
    node_id: str
    node_name: str = ""
    document: Optional[Dict] = None
    questions: List[Dict] = field(default_factory=list)
    video: Optional[Dict] = None
    reading: Optional[Dict] = None
    code_template: Optional[Dict] = None
    missing_types: List[str] = field(default_factory=list)  # 缺失的资源类型


class ResourceNetwork:
    """资源关联网络"""

    def get_resource_package(self, node_id: str, user_id: str = "") -> ResourcePackage:
        """获取路径节点的完整资源包

        Args:
            node_id: 知识点ID
            user_id: 用户ID（用于查询用户特定资源）

        Returns:
            ResourcePackage: 完整资源包
        """
        db = SessionLocal()
        try:
            from app.models.profile import (
                ResourceModel, QuestionModel, CodeTemplateModel
            )
            from app.core.knowledge_cache import knowledge_cache

            # 获取知识点名称
            node_info = knowledge_cache.get_node(node_id)
            node_name = node_info.get("name", node_id) if node_info else node_id

            package = ResourcePackage(node_id=node_id, node_name=node_name)

            # 1. 查找文档资源
            doc_resource = db.query(ResourceModel).filter(
                ResourceModel.type == "document",
                ResourceModel.kg_node_ids.contains(f'"{node_id}"')
            ).first()
            if doc_resource:
                import json
                package.document = json.loads(doc_resource.content_json) if doc_resource.content_json else None
            else:
                package.missing_types.append("document")

            # 2. 查找习题
            questions = db.query(QuestionModel).filter(
                QuestionModel.knowledge_point == node_id
            ).limit(5).all()
            if questions:
                package.questions = [
                    {"id": q.id, "type": q.type, "level": q.level, "description": q.description}
                    for q in questions
                ]
            else:
                package.missing_types.append("question")

            # 3. 查找视频资源
            video_resource = db.query(ResourceModel).filter(
                ResourceModel.type == "video",
                ResourceModel.kg_node_ids.contains(f'"{node_id}"')
            ).first()
            if video_resource:
                import json
                package.video = json.loads(video_resource.content_json) if video_resource.content_json else None
            else:
                package.missing_types.append("video")

            # 4. 查找阅读资源
            reading_resource = db.query(ResourceModel).filter(
                ResourceModel.type == "reading",
                ResourceModel.kg_node_ids.contains(f'"{node_id}"')
            ).first()
            if reading_resource:
                import json
                package.reading = json.loads(reading_resource.content_json) if reading_resource.content_json else None
            else:
                package.missing_types.append("reading")

            # 5. 查找代码模板
            code_template = db.query(CodeTemplateModel).filter(
                CodeTemplateModel.knowledge_point == node_id
            ).first()
            if code_template:
                package.code_template = {
                    "id": code_template.id,
                    "title": code_template.title,
                    "code": code_template.code
                }
            else:
                package.missing_types.append("code_template")

            return package
        finally:
            db.close()

    def generate_missing_resources(self, package: ResourcePackage) -> Dict:
        """自动补缺缺失资源

        Args:
            package: 资源包（含missing_types列表）

        Returns:
            Dict: 补缺任务列表
        """
        tasks = []
        for missing_type in package.missing_types:
            if missing_type == "document":
                tasks.append({"agent": "document_agent", "knowledge_point": package.node_id})
            elif missing_type == "question":
                tasks.append({"agent": "question_agent", "knowledge_point": package.node_id})
            elif missing_type == "video":
                # 只有可视化知识点才生成视频
                from app.core.knowledge_cache import knowledge_cache
                viz_config = knowledge_cache.get_viz_config(package.node_id)
                if viz_config:
                    tasks.append({"agent": "video_agent", "knowledge_point": package.node_id})
            elif missing_type == "reading":
                tasks.append({"agent": "reading_agent", "knowledge_point": package.node_id})

        return {"tasks": tasks, "node_id": package.node_id}


# 全局单例
resource_network = ResourceNetwork()
