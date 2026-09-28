"""
评估系统数据模型

定义学习效果评估相关的数据结构：
- AssessmentResult：评估结果
- LearningProgress：学习进度
- WeakPoint：薄弱点
- AdjustmentRecommendation：调整建议
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


class LearningProgress(BaseModel):
    """学习进度数据"""
    
    # 知识点ID
    knowledge_point_id: str = Field(..., description="知识点ID")
    
    # 学习时长（分钟）
    learning_duration: float = Field(0.0, description="学习时长（分钟）")
    
    # 答题正确率（0-100）
    correctness_rate: float = Field(0.0, description="答题正确率（0-100）")
    
    # 学习频率（次数）
    learning_frequency: int = Field(0, description="学习频率（次数）")
    
    # 资源使用情况
    resource_usage: Dict[str, int] = Field(default_factory=dict, description="资源使用情况")
    
    # 最后学习时间
    last_learning_time: Optional[datetime] = Field(None, description="最后学习时间")
    
    # 掌握度评估（0-100）
    mastery_level: float = Field(0.0, description="掌握度评估（0-100）")


class AssessmentWeakPoint(BaseModel):
    """评估薄弱点数据（评估报告专用）"""
    
    # 知识点ID
    knowledge_point_id: str = Field(..., description="知识点ID")
    
    # 知识点名称
    knowledge_point_name: str = Field(..., description="知识点名称")
    
    # 薄弱点程度（0-100，越低越薄弱）
    weakness_level: float = Field(..., description="薄弱点程度（0-100，越低越薄弱）")
    
    # 正确率
    correctness_rate: float = Field(..., description="正确率")
    
    # 薄弱点分类（严重薄弱点、薄弱点、一般薄弱点）
    weakness_category: str = Field(..., description="薄弱点分类")
    
    # 建议补强时长（分钟）
    recommended_duration: float = Field(..., description="建议补强时长（分钟）")


class AdjustmentRecommendation(BaseModel):
    """调整建议数据"""
    
    # 调整类型（路径调整、资源推送调整、学习频率调整）
    adjustment_type: str = Field(..., description="调整类型")
    
    # 调整内容
    adjustment_content: str = Field(..., description="调整内容")
    
    # 调整原因
    adjustment_reason: str = Field(..., description="调整原因")
    
    # 调整优先级（高、中、低）
    adjustment_priority: str = Field(..., description="调整优先级")
    
    # 调整后的内容
    adjusted_content: Optional[Dict] = Field(None, description="调整后的内容")


class AssessmentResult(BaseModel):
    """评估结果数据"""
    
    # 用户ID
    user_id: str = Field(..., description="用户ID")
    
    # 评估时间
    assessment_time: datetime = Field(default_factory=datetime.now, description="评估时间")
    
    # 整体掌握度（0-100）
    overall_mastery: float = Field(0.0, description="整体掌握度（0-100）")
    
    # 学习效率评估（分/小时）
    learning_efficiency: float = Field(0.0, description="学习效率评估（分/小时）")
    
    # 总学习时长（分钟）
    total_learning_duration: float = Field(0.0, description="总学习时长（分钟）")
    
    # 各知识点学习进度
    learning_progress: List[LearningProgress] = Field(default_factory=list, description="各知识点学习进度")
    
    # 薄弱点列表
    weak_points: List[AssessmentWeakPoint] = Field(default_factory=list, description="薄弱点列表")
    
    # 调整建议列表
    adjustment_recommendations: List[AdjustmentRecommendation] = Field(default_factory=list, description="调整建议列表")
    
    # 评估报告摘要
    assessment_summary: str = Field("", description="评估报告摘要")
    
    # 评估详细报告
    assessment_detail: Optional[Dict] = Field(None, description="评估详细报告")


class AssessmentRequest(BaseModel):
    """评估请求数据"""
    
    # 用户ID
    user_id: str = Field(..., description="用户ID")
    
    # 评估类型（完整评估、部分评估）
    assessment_type: str = Field("full", description="评估类型")


class LearningProgressUpdate(BaseModel):
    """学习进度更新数据"""
    
    # 用户ID
    user_id: str = Field(..., description="用户ID")
    
    # 知识点ID
    knowledge_point_id: str = Field(..., description="知识点ID")
    
    # 学习时长增量（分钟）
    learning_duration_increment: float = Field(..., description="学习时长增量（分钟）")
    
    # 答题结果（正确/错误）
    answer_result: Optional[str] = Field(None, description="答题结果（正确/错误）")
    
    # 资源使用类型
    resource_type: Optional[str] = Field(None, description="资源使用类型")


class PathAdjustmentRequest(BaseModel):
    """路径调整请求数据"""
    
    # 用户ID
    user_id: str = Field(..., description="用户ID")
    
    # 评估结果ID
    assessment_result_id: str = Field(..., description="评估结果ID")
    
    # 调整类型（自动调整、手动调整）
    adjustment_type: str = Field("auto", description="调整类型")


class AssessmentReport(BaseModel):
    """评估报告数据"""
    
    # 用户ID
    user_id: str = Field(..., description="用户ID")
    
    # 评估时间
    assessment_time: datetime = Field(..., description="评估时间")
    
    # 报告标题
    report_title: str = Field(..., description="报告标题")
    
    # 报告内容
    report_content: str = Field(..., description="报告内容")
    
    # 报告图表数据
    report_charts: Optional[Dict] = Field(None, description="报告图表数据")
    
    # 报告建议
    report_recommendations: List[str] = Field(default_factory=list, description="报告建议")