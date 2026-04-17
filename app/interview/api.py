"""
面试专用功能 API 路由

提供：题库浏览、模拟面试、面试报告
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.interview.question_bank import (
    QuestionBank, QuestionCategory, DifficultyLevel,
    InterviewQuestion, InterviewSession
)

router = APIRouter(prefix="/api/interview", tags=["面试"])


# ============================================================
# 路由依赖
# ============================================================

def get_qb() -> QuestionBank:
    return QuestionBank()


# ============================================================
# 请求/响应模型
# ============================================================

class QuestionResponse(BaseModel):
    id: str
    category: str
    difficulty: int
    question_type: str
    question_text: str
    key_points: List[str]
    follow_up_questions: List[str]
    skills_tags: List[str]
    estimated_time_minutes: int
    hints: List[str]


class GenerateInterviewRequest(BaseModel):
    target_position: str = Field(..., description="目标岗位", examples=["后端工程师", "算法工程师", "全栈工程师"])
    target_companies: Optional[List[str]] = Field(default=[], description="目标公司", examples=[["字节跳动", "腾讯"], ["阿里巴巴"]])
    difficulty: Optional[int] = Field(default=None, description="难度 1-4", ge=1, le=4)
    categories: Optional[List[str]] = Field(default=None, description="题目分类列表")
    count: int = Field(default=5, description="题目数量", ge=3, le=20)


class SubmitAnswerRequest(BaseModel):
    question_id: str
    answer: str = Field(..., min_length=5)


class InterviewReportResponse(BaseModel):
    session_id: str
    candidate_name: str
    target_position: str
    overall_score: float
    overall_comment: str
    category_scores: Dict[str, float]
    question_count: int
    answered_count: int
    total_duration_minutes: float
    recommendations: List[str]
    started_at: Optional[str]
    completed_at: Optional[str]


# ============================================================
# 题库路由
# ============================================================

@router.get("/questions", response_model=List[QuestionResponse])
async def list_questions(
    category: Optional[str] = Query(default=None, description="题目分类"),
    difficulty: Optional[int] = Query(default=None, ge=1, le=4, description="难度等级"),
    skills: Optional[str] = Query(default=None, description="技能标签，逗号分隔"),
    limit: int = Query(default=20, ge=1, le=100),
) -> List[Dict]:
    """浏览题库，支持按分类/难度/技能筛选"""
    qb = get_qb()

    cat = None
    if category:
        try:
            cat = QuestionCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"未知分类: {category}")

    diff = None
    if difficulty:
        diff = DifficultyLevel(difficulty)

    skill_list = [s.strip() for s in skills.split(",")] if skills else None

    questions = qb.list_questions(
        category=cat,
        difficulty=diff,
        skills=skill_list,
        limit=limit,
    )
    return [q.to_dict() for q in questions]


@router.get("/questions/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: str) -> Dict:
    """获取题目详情（含参考答案）"""
    qb = get_qb()
    question = qb.get_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    result = question.to_dict()
    # 参考答案太大，默认不返回，单独接口获取
    result.pop("ideal_answer", None)
    return result


@router.get("/questions/{question_id}/answer")
async def get_answer(question_id: str) -> Dict:
    """获取题目参考答案（需要确认查看）"""
    qb = get_qb()
    question = qb.get_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    return {
        "question_id": question_id,
        "ideal_answer": question.ideal_answer,
        "key_points": question.key_points,
        "hints": question.hints,
    }


# ============================================================
# 模拟面试路由
# ============================================================

@router.post("/interview/generate")
async def generate_interview(request: GenerateInterviewRequest) -> Dict:
    """根据目标岗位和公司生成面试题目组合"""
    qb = get_qb()

    cats = None
    if request.categories:
        try:
            cats = [QuestionCategory(c) for c in request.categories]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    diff = None
    if request.difficulty:
        diff = DifficultyLevel(request.difficulty)

    session = qb.generate_interview(
        target_position=request.target_position,
        target_companies=request.target_companies,
        difficulty=diff,
        categories=cats,
        count=request.count,
    )

    # 返回题目列表（不含答案）
    questions = []
    for qid in session.question_ids:
        q = qb.get_question(qid)
        if q:
            questions.append({
                "id": q.id,
                "category": q.category.value,
                "difficulty": q.difficulty.value,
                "question_text": q.question_text,
                "question_type": q.question_type.value,
                "skills_tags": q.skills_tags,
                "estimated_time_minutes": q.estimated_time_minutes,
            })

    return {
        "session_id": session.session_id,
        "target_position": session.target_position,
        "target_companies": session.target_companies,
        "questions": questions,
        "total": len(questions),
        "started_at": session.started_at,
    }


@router.post("/interview/{session_id}/answer")
async def submit_answer(session_id: str, request: SubmitAnswerRequest) -> Dict:
    """提交答案，获取 AI 评测"""
    qb = get_qb()

    # 先获取题目（用于展示）
    question = qb.get_question(request.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    # 提交答案并评测
    result = qb.submit_answer(session_id, request.question_id, request.answer)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    # 获取下一个追问
    follow_up = qb.get_next_follow_up(session_id, request.question_id)

    # 获取当前会话状态
    session = qb.get_session(session_id)
    next_question = None
    if session and session.current_question_id:
        next_q = qb.get_question(session.current_question_id)
        if next_q:
            next_question = {
                "id": next_q.id,
                "category": next_q.category.value,
                "difficulty": next_q.difficulty.value,
                "question_text": next_q.question_text,
                "estimated_time_minutes": next_q.estimated_time_minutes,
            }

    return {
        "question_id": request.question_id,
        "answer": request.answer,
        "evaluation": result,
        "follow_up_question": follow_up,
        "next_question": next_question,
        "progress": session.progress if session else "0/0",
    }


@router.get("/interview/{session_id}")
async def get_interview_session(session_id: str) -> Dict:
    """获取面试会话状态"""
    qb = get_qb()
    session = qb.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="面试会话不存在")

    # 获取已回答的题目详情（不含答案）
    answered_questions = []
    for qid in session.question_ids[:session.current_index]:
        q = qb.get_question(qid)
        if q:
            answered_questions.append({
                "id": q.id,
                "question_text": q.question_text,
                "score": session.scores.get(qid),
                "feedback": session.feedback.get(qid, ""),
            })

    # 当前题目
    current_question = None
    if session.current_question_id:
        q = qb.get_question(session.current_question_id)
        if q:
            current_question = {
                "id": q.id,
                "question_text": q.question_text,
                "category": q.category.value,
                "difficulty": q.difficulty.value,
                "estimated_time_minutes": q.estimated_time_minutes,
            }

    return {
        "session_id": session.session_id,
        "target_position": session.target_position,
        "status": session.status,
        "progress": session.progress,
        "overall_score": session.overall_score,
        "answered_questions": answered_questions,
        "current_question": current_question,
        "started_at": session.started_at,
    }


@router.post("/interview/{session_id}/complete", response_model=InterviewReportResponse)
async def complete_interview(session_id: str) -> Dict:
    """完成面试，生成综合报告"""
    qb = get_qb()
    report = qb.complete_interview(session_id)
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    return report


@router.get("/interview/{session_id}/history")
async def get_interview_history(session_id: str) -> Dict:
    """获取面试详细历史"""
    qb = get_qb()
    session = qb.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="面试会话不存在")

    history = []
    for qid in session.question_ids:
        q = qb.get_question(qid)
        if q:
            history.append({
                "id": q.id,
                "category": q.category.value,
                "difficulty": q.difficulty.value,
                "question_text": q.question_text,
                "answer": session.answers.get(qid, ""),
                "follow_up_answer": session.follow_ups.get(qid, ""),
                "score": session.scores.get(qid),
                "feedback": session.feedback.get(qid, ""),
                "ideal_answer": q.ideal_answer,
                "key_points": q.key_points,
            })

    return {"session_id": session_id, "history": history}


@router.get("/interviews/history")
async def list_interviews() -> List[Dict]:
    """列出所有面试记录"""
    qb = get_qb()
    return qb.list_sessions()


# ============================================================
# 面试统计
# ============================================================

@router.get("/stats")
async def interview_stats() -> Dict:
    """获取面试统计数据"""
    qb = get_qb()
    sessions = list(qb._sessions.values())
    completed = [s for s in sessions if s.status == "completed"]

    if not completed:
        return {
            "total_interviews": len(sessions),
            "completed_interviews": 0,
            "average_score": 0,
            "category_coverage": {},
            "difficulty_coverage": {},
        }

    scores = [s.overall_score for s in completed if s.overall_score]
    avg_score = sum(scores) / len(scores) if scores else 0

    return {
        "total_interviews": len(sessions),
        "completed_interviews": len(completed),
        "average_score": round(avg_score, 1),
        "pass_rate": round(len([s for s in scores if s >= 60]) / len(scores) * 100, 1) if scores else 0,
    }
