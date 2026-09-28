"""知识内容缓存 - 启动时从MySQL加载到Redis，运行期间不查MySQL"""

import json
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class KnowledgeCache:
    """知识内容缓存

    Redis Key: knowledge:all (String, 永久TTL)
    启动时从MySQL加载全部知识内容到Redis
    运行期间所有知识查询走Redis
    """

    def __init__(self):
        self._cache: Dict = {}  # 内存缓存fallback（Redis不可用时）
        self._loaded = False

    def load_all(self, db):
        """启动时：从MySQL加载全部知识内容到缓存

        Args:
            db: SQLAlchemy Session
        """
        from app.models.profile import (
            KnowledgeNodeModel, KnowledgeContentModel, KnowledgeAliasModel,
            KnowledgeDependencyModel, VideoTemplateModel, VisualizationConfigModel,
            SourceReferenceModel, AchievementModel
        )

        cache_data = {
            "nodes": {},        # node_id → node_dict
            "content": {},      # node_id → {content_type: content_text}
            "aliases": {},      # alias → node_id
            "dependencies": {}, # node_id → [dependency_ids]
            "video_templates": {},  # node_id → template_dict
            "viz_configs": {},  # node_id → config_dict
            "sources": {},      # node_id → [source_dicts]
            "achievements": [], # achievement list
        }

        # 1. 知识点节点
        nodes = db.query(KnowledgeNodeModel).all()
        for n in nodes:
            cache_data["nodes"][n.id] = {
                "id": n.id, "name": n.name, "category": n.category,
                "description": n.description, "optional": n.optional,
                "sort_order": n.sort_order
            }

        # 2. 教学内容
        contents = db.query(KnowledgeContentModel).all()
        for c in contents:
            if c.node_id not in cache_data["content"]:
                cache_data["content"][c.node_id] = {}
            cache_data["content"][c.node_id][c.content_type] = c.content

        # 3. 别名
        aliases = db.query(KnowledgeAliasModel).all()
        for a in aliases:
            cache_data["aliases"][a.alias] = a.node_id

        # 4. 依赖关系
        deps = db.query(KnowledgeDependencyModel).all()
        for d in deps:
            if d.node_id not in cache_data["dependencies"]:
                cache_data["dependencies"][d.node_id] = []
            cache_data["dependencies"][d.node_id].append(d.dependency_id)

        # 5. 视频模板
        templates = db.query(VideoTemplateModel).all()
        for t in templates:
            cache_data["video_templates"][t.node_id] = {
                "id": t.id, "scene_class": t.scene_class,
                "script": t.script, "narrations_json": t.narrations_json,
                "duration_estimate": t.duration_estimate,
                "difficulty": t.difficulty, "is_default": t.is_default
            }

        # 6. 可视化配置
        viz_configs = db.query(VisualizationConfigModel).all()
        for v in viz_configs:
            cache_data["viz_configs"][v.node_id] = {
                "id": v.id, "component_type": v.component_type,
                "data_schema_json": v.data_schema_json,
                "controls_json": v.controls_json,
                "step_templates_json": v.step_templates_json
            }

        # 7. 参考来源
        sources = db.query(SourceReferenceModel).all()
        for s in sources:
            if s.node_id not in cache_data["sources"]:
                cache_data["sources"][s.node_id] = []
            cache_data["sources"][s.node_id].append({
                "source_type": s.source_type, "title": s.title,
                "detail": s.detail, "url": s.url
            })

        # 8. 成就
        achievements = db.query(AchievementModel).all()
        for a in achievements:
            cache_data["achievements"].append({
                "id": a.id, "name": a.name, "description": a.description,
                "icon": a.icon, "category": a.category,
                "condition_json": a.condition_json
            })

        # 保存到内存缓存
        self._cache = cache_data
        self._loaded = True

        # 尝试保存到Redis
        try:
            self._save_to_redis(cache_data)
        except Exception as e:
            logger.warning(f"Redis save failed, using memory cache: {e}")

        logger.info(f"KnowledgeCache loaded: {len(nodes)} nodes, {len(contents)} contents, {len(aliases)} aliases")

    def _save_to_redis(self, cache_data: Dict):
        """保存到Redis"""
        try:
            import redis
            from app.core.config import get_settings
            settings = get_settings()
            if settings.redis_url:
                r = redis.from_url(settings.redis_url)
                r.set("knowledge:all", json.dumps(cache_data, ensure_ascii=False))
                logger.info("Knowledge cache saved to Redis")
        except Exception as e:
            logger.debug(f"Redis not available: {e}")

    def _load_from_redis(self) -> Optional[Dict]:
        """从Redis加载"""
        try:
            import redis
            from app.core.config import get_settings
            settings = get_settings()
            if settings.redis_url:
                r = redis.from_url(settings.redis_url)
                data = r.get("knowledge:all")
                if data:
                    return json.loads(data)
        except Exception:
            pass
        return None

    # --- 查询方法 ---

    def get_node(self, node_id: str) -> Optional[Dict]:
        """获取知识点定义"""
        return self._cache.get("nodes", {}).get(node_id)

    def get_all_nodes(self) -> Dict:
        """获取所有知识点"""
        return self._cache.get("nodes", {})

    def get_content(self, node_id: str, content_type: Optional[str] = None) -> Optional[Dict]:
        """获取知识点教学文本"""
        contents = self._cache.get("content", {}).get(node_id, {})
        if content_type:
            return contents.get(content_type)
        return contents

    def get_aliases(self) -> Dict:
        """获取所有别名映射"""
        return self._cache.get("aliases", {})

    def resolve_alias(self, alias: str) -> Optional[str]:
        """别名解析：返回对应的node_id"""
        return self._cache.get("aliases", {}).get(alias)

    def get_dependencies(self, node_id: str) -> List[str]:
        """获取知识点的前置依赖"""
        return self._cache.get("dependencies", {}).get(node_id, [])

    def get_video_template(self, node_id: str) -> Optional[Dict]:
        """获取视频模板"""
        return self._cache.get("video_templates", {}).get(node_id)

    def get_viz_config(self, node_id: str) -> Optional[Dict]:
        """获取可视化配置"""
        return self._cache.get("viz_configs", {}).get(node_id)

    def get_sources(self, node_id: str) -> List[Dict]:
        """获取参考来源"""
        return self._cache.get("sources", {}).get(node_id, [])

    def get_achievements(self) -> List[Dict]:
        """获取所有成就定义"""
        return self._cache.get("achievements", [])

    def get_nodes_by_category(self, category: str) -> List[Dict]:
        """按分类获取知识点"""
        return [n for n in self._cache.get("nodes", {}).values() if n.get("category") == category]


# 全局单例
knowledge_cache = KnowledgeCache()
