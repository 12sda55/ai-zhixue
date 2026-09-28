"""拓展阅读Agent - 对照规范 B7

输入：知识点ID
输出：Markdown格式拓展阅读 + 推荐URL
LLM生成，关联kg_node_id
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from app.core.llm import llm_client
from app.schemas.profile import StudentProfile
from app.schemas.knowledge_graph import get_knowledge_node, get_dependencies, get_all_dependents

logger = logging.getLogger(__name__)


class ReadingService:
    """拓展阅读生成服务"""

    def generate_reading(self, knowledge_point: str, profile: Optional[StudentProfile] = None) -> dict:
        """生成拓展阅读材料

        Args:
            knowledge_point: 知识点ID
            profile: 学生画像（可选，用于个性化推荐）

        Returns:
            {
                "knowledge_point": str,
                "title": str,
                "content": str,  # Markdown格式
                "references": list[dict],  # [{title, url, type}]
                "kg_node_ids": list[str],
            }
        """
        node_def = get_knowledge_node(knowledge_point)
        kp_name = node_def.name if node_def else knowledge_point
        kp_category = node_def.category if node_def else ""

        # 获取关联知识点
        deps = get_dependencies(knowledge_point)
        dependents = get_all_dependents(knowledge_point)
        related_ids = list(set(deps + dependents))[:5]

        # 构建个性化提示
        profile_hint = ""
        if profile:
            profile_hint = f"""
学生专业：{profile.major.value}
学习阶段：{profile.stage.value}
认知风格：{profile.cognitive_style.value}
请根据学生背景调整推荐内容的深度和方向。"""

        prompt = f"""请为知识点「{kp_name}」（分类：{kp_category}）生成拓展阅读材料。

要求：
1. 用Markdown格式输出
2. 包含以下部分：
   - **现实应用**：该知识点在真实场景中的应用案例（如数据库索引、网络协议等）
   - **历史背景**：关键贡献者、发明时间、演进历程
   - **进阶主题**：相关的高级变体、优化方向、前沿研究
   - **推荐阅读**：书籍、论文、博客、在线课程（每个给出标题和URL）
3. 推荐阅读至少包含3条，类型涵盖 book/paper/blog/course
4. 内容要有深度，适合大学生阅读
{profile_hint}

请严格按以下JSON格式返回：
{{
    "title": "拓展阅读标题",
    "content": "Markdown格式的完整内容",
    "references": [
        {{"title": "推荐资源标题", "url": "https://...", "type": "book/paper/blog/course"}}
    ]
}}"""

        try:
            result_text = llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=3000,
                response_format={"type": "json_object"},
            )

            result = json.loads(result_text.strip())

            # 确保必要字段存在
            return {
                "knowledge_point": knowledge_point,
                "title": result.get("title", f"{kp_name}拓展阅读"),
                "content": result.get("content", ""),
                "references": result.get("references", []),
                "kg_node_ids": [knowledge_point] + related_ids,
            }

        except json.JSONDecodeError as e:
            logger.error(f"拓展阅读JSON解析失败: {e}")
            # 降级：用原始文本作为content
            return {
                "knowledge_point": knowledge_point,
                "title": f"{kp_name}拓展阅读",
                "content": result_text if 'result_text' in dir() else f"关于{kp_name}的拓展阅读材料生成失败，请稍后重试。",
                "references": [],
                "kg_node_ids": [knowledge_point] + related_ids,
            }
        except Exception as e:
            logger.error(f"拓展阅读生成失败: {e}")
            return {
                "knowledge_point": knowledge_point,
                "title": f"{kp_name}拓展阅读",
                "content": f"关于{kp_name}的拓展阅读材料生成失败，请稍后重试。",
                "references": [],
                "kg_node_ids": [knowledge_point],
            }


# 全局单例
reading_service = ReadingService()
