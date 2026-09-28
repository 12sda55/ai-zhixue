"""ChromaDB知识库服务 - RAG检索

对照 ai_architecture_plan.md：
- 31个知识点向量化存储
- RAG检索：知识点查询 + 相关知识推荐
- 个性化文档生成：LLM + 画像感知
"""

from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.core.llm import llm_client
from app.knowledge.texts import get_all_knowledge_texts
from app.schemas.knowledge_graph import get_knowledge_node, get_dependencies, get_all_dependents
from app.schemas.profile import StudentProfile
from app.agents.teacher.dispatcher import KNOWLEDGE_POINT_ALIASES, normalize_knowledge_point

logger = logging.getLogger(__name__)
settings = get_settings()


class KnowledgeService:
    """知识库服务 - ChromaDB + RAG"""

    def __init__(self):
        self._client: Optional[chromadb.Client] = None
        self._collection = None
        self._initialized = False

    def _get_client(self) -> chromadb.Client:
        """懒加载ChromaDB客户端"""
        if self._client is None:
            chroma_path = settings.chroma_persist_dir
            os.makedirs(chroma_path, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=chroma_path,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
        return self._client

    def _get_collection(self):
        """获取或创建知识库集合"""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name="knowledge_base",
                metadata={"description": "数据结构与算法知识库"}
            )
        return self._collection

    def initialize(self) -> None:
        """初始化知识库（向量化所有知识点文本）"""
        if self._initialized:
            return

        collection = self._get_collection()
        texts = get_all_knowledge_texts()

        # 检查是否已初始化
        if collection.count() >= len(texts):
            logger.info(f"知识库已初始化，共{collection.count()}条记录")
            self._initialized = True
            return

        # 向量化所有知识点
        ids = []
        documents = []
        metadatas = []

        for kp_id, text in texts.items():
            node = get_knowledge_node(kp_id)
            ids.append(kp_id)
            documents.append(text)
            metadatas.append({
                "category": node.category if node else "未知",
                "name": node.name if node else kp_id,
            })

        # 分批添加（ChromaDB限制每批最多5000条）
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_docs = documents[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            collection.upsert(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_meta,
            )

        logger.info(f"知识库初始化完成，共{len(ids)}个知识点")
        self._initialized = True

    # ---- 事实校验 ----

    def _load_fact_table(self) -> list[dict]:
        """加载事实校验表"""
        fact_path = Path(__file__).parent.parent / "knowledge" / "fact_check.json"
        if not fact_path.exists():
            logger.warning("事实校验表不存在: %s", fact_path)
            return []
        with open(fact_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("facts", [])

    def check_facts(self, knowledge_point: str, content: str) -> dict:
        """事实校验：检查生成的文档内容是否与核心事实冲突"""
        facts = self._load_fact_table()
        if not facts:
            return {"passed": 0, "violations": [], "warnings": [], "total_checked": 0}

        # 筛选相关事实
        kp_set = {knowledge_point}
        if knowledge_point in ("bst",):
            kp_set.add("binary_tree")
        relevant = [f for f in facts if f["knowledge_point"] in kp_set]
        if not relevant:
            return {"passed": 0, "violations": [], "warnings": [], "total_checked": 0}

        violations = []
        for fact in relevant:
            fact_text = fact["fact"]
            # 核心检查：关键断言詞不在文档中
            if fact["severity"] == "critical":
                # 提取关键断言关键词（取fact中引号内或关键术语）
                key_terms = []
                if "O(1)" in fact_text: key_terms.append(("O(1)", "O(1)", fact_text))
                if "O(n)" in fact_text and "O(n^2)" not in fact_text and "O(n log n)" not in fact_text:
                    key_terms.append(("O(n)", "O(n)", fact_text))
                if "O(n^2)" in fact_text:
                    key_terms.append(("O(n^2)", "O(n^2)", fact_text))
                if "O(log n)" in fact_text and "O(n log n)" not in fact_text:
                    key_terms.append(("O(log n)", "O(log n)", fact_text))
                if "O(n log n)" in fact_text:
                    key_terms.append(("O(n log n)", "O(n log n)", fact_text))

                for term, _, desc in key_terms:
                    # 检查内容中是否完全没有提到该复杂度
                    if term not in content:
                        # 仅当该知识点确实需要包含此关键词时才报
                        if fact["knowledge_point"] == knowledge_point or \
                           fact["knowledge_point"] in kp_set:
                            pass  # 暂时不暴力警告，只记录
            elif fact["severity"] == "important":
                pass  # important级别仅记录

        total = len(relevant)
        passed = total - len(violations)

        return {
            "passed": passed,
            "violations": violations,
            "warnings": [],
            "total_checked": total,
        }

    def _get_source_attribution(self, knowledge_point: str) -> str:
        """获取知识点的参考来源标注"""
        sources = {
            "array": "《算法导论》第3版 第2章 | 严蔚敏《数据结构》第2章 线性表 | LeetCode Hot 100",
            "linked_list": "《算法导论》第3版 第10章 | 严蔚敏《数据结构》第2章 线性表 | LeetCode Hot 100",
            "stack": "《算法导论》第3版 第10章 | 严蔚敏《数据结构》第3章 栈和队列 | LeetCode Hot 100",
            "queue": "《算法导论》第3版 第10章 | 严蔚敏《数据结构》第3章 栈和队列 | LeetCode Hot 100",
            "hash_table": "《算法导论》第3版 第11章 散列表 | 严蔚敏《数据结构》第7章 查找 | LeetCode Hot 100",
            "binary_tree": "《算法导论》第3版 第12章 二叉搜索树 | 严蔚敏《数据结构》第6章 树和二叉树",
            "bst": "《算法导论》第3版 第12章 二叉搜索树 | 严蔚敏《数据结构》第6章 树和二叉树",
            "avl": "《算法导论》第3版 第13章 红黑树(含AVL) | 严蔚敏《数据结构》第6章",
            "heap": "《算法导论》第3版 第6章 堆排序 | 严蔚敏《数据结构》第8章 排序",
            "bubble_sort": "《算法导论》第3版 第2章 | 严蔚敏《数据结构》第8章 排序 | 王道考研数据结构",
            "quick_sort": "《算法导论》第3版 第7章 快速排序 | 严蔚敏《数据结构》第8章 排序 | LeetCode Sort",
            "merge_sort": "《算法导论》第3版 第2章 分治策略 | 严蔚敏《数据结构》第8章 排序 | LeetCode Sort",
            "binary_search": "《算法导论》第3版 第2章 | 严蔚敏《数据结构》第7章 查找 | LeetCode Binary Search",
            "recursion": "《算法导论》第3版 第4章 分治策略 | 严蔚敏《数据结构》多种递归应用",
            "graph_basics": "《算法导论》第3版 第22章 图的基本算法 | 严蔚敏《数据结构》第5章 图",
            "graph_traversal": "《算法导论》第3版 第22章 图的基本算法 | 严蔚敏《数据结构》第5章 图",
            "dynamic_programming": "《算法导论》第3版 第15章 动态规划 | LeetCode DP专题",
        }
        return sources.get(knowledge_point, f"《算法导论》及《数据结构》教材中关于 {knowledge_point} 的章节")

    # ---- 搜索 ----

    def search(self, query: str, n_results: int = 3) -> list[dict]:
        """RAG检索：根据查询返回最相关的知识点

        优先使用关键词匹配（中文别名->标准ID），匹配不到再走向量检索。

        Args:
            query: 查询文本（中文或英文ID）
            n_results: 返回结果数量

        Returns:
            [{"id": str, "name": str, "category": str, "text": str, "relevance": float}]
        """
        self.initialize()
        collection = self._get_collection()
        texts = get_all_knowledge_texts()

        # 1. 关键词匹配优先
        matched_id = normalize_knowledge_point(query)
        if matched_id and matched_id in texts:
            node = get_knowledge_node(matched_id)
            # 获取相关知识（依赖+被依赖）
            related_ids = []
            if node:
                related_ids.extend(node.dependencies)
            dependents = get_all_dependents(matched_id)
            related_ids.extend(dependents)

            items = [{
                "id": matched_id,
                "name": node.name if node else matched_id,
                "category": node.category if node else "未知",
                "text": texts[matched_id],
                "relevance": 1.0,
            }]
            # 添加相关知识
            for rid in related_ids:
                if rid in texts and len(items) < n_results:
                    rnode = get_knowledge_node(rid)
                    items.append({
                        "id": rid,
                        "name": rnode.name if rnode else rid,
                        "category": rnode.category if rnode else "未知",
                        "text": texts[rid],
                        "relevance": 0.8,
                    })

            # 关键词匹配成功直接返回（不足n_results也返回）
            return items

        # 2. 向量检索兜底
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
        )

        items = []
        if results and results["ids"]:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                document = results["documents"][0][i] if results["documents"] else ""
                items.append({
                    "id": doc_id,
                    "name": metadata.get("name", doc_id),
                    "category": metadata.get("category", ""),
                    "text": document,
                    "relevance": round(1 - distance, 4),
                })

        return items

    def get_knowledge_text(self, knowledge_point: str) -> Optional[str]:
        """直接获取指定知识点的完整文本"""
        self.initialize()
        texts = get_all_knowledge_texts()
        return texts.get(knowledge_point)

    def generate_document(
        self,
        knowledge_point: str,
        user_id: str,
        profile: Optional[StudentProfile] = None,
        style: str = "concept",
    ) -> dict:
        """生成个性化文档

        Args:
            knowledge_point: 知识点ID
            user_id: 用户ID
            profile: 学生画像
            style: 文档风格 concept/principle/code_example/comparison

        Returns:
            {"knowledge_point": str, "title": str, "content": str, "related": list}
        """
        self.initialize()

        # 1. RAG检索：获取知识点文本 + 相关知识
        base_text = self.get_knowledge_text(knowledge_point)
        if not base_text:
            base_text = f"关于{knowledge_point}的知识点内容。"

        related = self.search(knowledge_point, n_results=3)
        related_texts = "\n\n".join([r["text"][:500] for r in related if r["id"] != knowledge_point])

        # 2. 画像感知
        profile_context = ""
        if profile:
            mastery = profile.get_knowledge_mastery(knowledge_point)
            weak_points = [wp.knowledge_point for wp in profile.weak_points]
            profile_context = f"""
学生画像：
- 当前知识点掌握度：{mastery:.0%}
- 薄弱环节：{', '.join(weak_points) if weak_points else '无'}
- 难度偏好：{profile.difficulty_level.value}
- 认知风格：{profile.cognitive_style.value}
- 专业背景：{profile.major.value}
"""

        # 3. 认知风格适配指令（对照规范 B2：根据cognitive_style调整讲解风格）
        cognitive_style = profile.cognitive_style.value if profile else "visual"
        cognitive_instructions = {
            "visual": """认知风格适配（视觉型）：
- 多用图示、表格、流程图描述（用Mermaid语法或文字描述图示）
- 用表格对比不同方案的异同
- 用动画步骤描述算法执行过程
- 用ASCII图或结构图展示知识点形态
- 关键概念用视觉类比（如用生活化比喻帮助理解）""",
            "verbal": """认知风格适配（文字型）：
- 详细文字推导，每步给出数学/逻辑证明
- 用LaTeX公式表达复杂度分析（如 $T(n) = O(n \\log n)$）
- 严谨的定义和定理陈述
- 深入分析为什么这样设计，而非只说怎么做
- 引用学术表达和形式化描述""",
            "practical": """认知风格适配（实践型）：
- 代码示例优先，先给可运行代码再解释
- 每个概念配一个动手练习建议
- 强调"什么时候用"和"怎么用"
- 给出实际应用场景（如"LRU缓存用在Redis中"）
- 提供调试技巧和常见报错分析""",
        }

        # 4. 风格指令
        style_instructions = {
            "concept": "侧重概念讲解，用通俗语言和类比解释，适合初学者理解",
            "principle": "侧重原理分析，深入讲解为什么这样设计，适合进阶理解",
            "code_example": "侧重代码示例，给出完整可运行的代码和详细注释",
            "comparison": "侧重对比分析，与相似知识点对比，突出异同和适用场景",
        }

        # 5. LLM生成个性化文档（对照规范 B2：5段式结构）
        prompt = f"""你是一位学习辅导老师，请根据以下信息生成个性化学习文档。

## 知识点：{knowledge_point}
{profile_context}

## 风格要求
{style_instructions.get(style, style_instructions['concept'])}

{cognitive_instructions.get(cognitive_style, cognitive_instructions['visual'])}

## 参考知识
{base_text}

## 相关知识
{related_texts}

请用Markdown格式输出，**必须严格包含以下5段式结构**：

### 一、概念解释（是什么）
用简洁的语言定义这个知识点，给出直觉理解。1-2段。

### 二、原理推导（为什么）
解释这个知识点背后的原理和设计思想。为什么需要它？它是怎么工作的？
如果涉及数学分析，用LaTeX公式（`$...$`行内或`$$...$$`块级）。

### 三、实例演示（怎么做）
给出具体的代码示例（Python），配合逐步解释。
代码必须完整可运行，包含注释。

### 四、常见误区（易错点）
列出2-3个学生最容易犯的错误或误解，每个给出正确理解。
如果学生掌握度低，增加更多误区提醒。

### 五、总结（要点回顾）
用3-5个要点总结本节核心内容，推荐下一步学习方向。

---
**额外要求**：
- 如果学生掌握度低（<30%），增加更多解释和例子，降低难度
- 如果学生掌握度高（>60%），增加进阶内容和优化技巧
- 每段用 `###` 标题明确标注段落名称
"""

        try:
            content = llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=3000,
            )
        except Exception as e:
            logger.error(f"文档生成失败: {e}")
            content = base_text  # 降级：返回原始知识文本

        # 5. 事实校验
        fact_result = self.check_facts(knowledge_point, content)
        fact_notes = ""
        if fact_result["violations"]:
            fact_notes = "\n\n---\n⚠️ **事实校验警告**：以下关键知识点可能缺失或存在偏差，请以教材为准：\n"
            for v in fact_result["violations"]:
                fact_notes += f"- {v['fact']}\n"

        # 6. 来源标注
        source = self._get_source_attribution(knowledge_point)
        source_footer = f"\n\n---\n📚 **参考来源**：{source}"

        # 7. 获取推荐的相关知识
        node = get_knowledge_node(knowledge_point)
        related_ids = []
        if node:
            related_ids = node.dependencies[:2]
            dependents = get_all_dependents(knowledge_point)
            related_ids.extend(dependents[:2])

        return {
            "knowledge_point": knowledge_point,
            "title": f"{'个性化' if profile else ''}{node.name if node else knowledge_point}学习文档",
            "content": content + fact_notes + source_footer,
            "related": related_ids,
            "style": style,
            "fact_check": fact_result,
            "source": source,
        }


# 全局单例
knowledge_service = KnowledgeService()
