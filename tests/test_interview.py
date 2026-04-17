"""面试功能测试"""

import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def reset_qb():
    """每个测试前重置题库"""
    from app.interview.question_bank import QuestionBank
    # 重置单例
    QuestionBank._instance = None
    yield
    # 测试后也重置
    QuestionBank._instance = None


class TestQuestionBank:
    """题库测试"""

    def test_question_bank_singleton(self):
        """测试题库单例"""
        from app.interview.question_bank import QuestionBank
        qb1 = QuestionBank()
        qb2 = QuestionBank()
        assert qb1 is qb2

    def test_builtin_questions_loaded(self):
        """测试内置题目已加载"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        assert len(qb._questions) > 0

    def test_list_questions(self):
        """测试题库筛选"""
        from app.interview.question_bank import QuestionBank, QuestionCategory
        qb = QuestionBank()
        questions = qb.list_questions(category=QuestionCategory.TECHNICAL, limit=5)
        assert isinstance(questions, list)
        for q in questions:
            assert q.category == QuestionCategory.TECHNICAL

    def test_list_by_difficulty(self):
        """测试按难度筛选"""
        from app.interview.question_bank import QuestionBank, DifficultyLevel
        qb = QuestionBank()
        questions = qb.list_questions(difficulty=DifficultyLevel.MEDIUM, limit=5)
        assert isinstance(questions, list)

    def test_get_question(self):
        """测试获取题目"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        # 获取任意一道题
        qids = list(qb._questions.keys())
        q = qb.get_question(qids[0])
        assert q is not None
        assert q.id == qids[0]

    def test_question_to_dict(self):
        """测试题目序列化"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        qids = list(qb._questions.keys())
        q = qb.get_question(qids[0])
        d = q.to_dict()
        assert "id" in d
        assert "question_text" in d
        assert "ideal_answer" in d

    def test_question_deserialization(self):
        """测试题目反序列化"""
        from app.interview.question_bank import QuestionBank, InterviewQuestion
        qb = QuestionBank()
        qids = list(qb._questions.keys())
        q = qb.get_question(qids[0])
        d = q.to_dict()
        q2 = InterviewQuestion.from_dict(d)
        assert q2.id == q.id
        assert q2.question_text == q.question_text

    def test_technical_questions(self):
        """测试技术题目"""
        from app.interview.question_bank import QuestionBank, QuestionCategory
        qb = QuestionBank()
        questions = qb.list_questions(category=QuestionCategory.TECHNICAL)
        assert len(questions) > 0
        for q in questions:
            assert q.category == QuestionCategory.TECHNICAL

    def test_behavioral_questions(self):
        """测试行为题目"""
        from app.interview.question_bank import QuestionBank, QuestionCategory
        qb = QuestionBank()
        questions = qb.list_questions(category=QuestionCategory.BEHAVIORAL)
        assert len(questions) > 0

    def test_system_design_questions(self):
        """测试系统设计题目"""
        from app.interview.question_bank import QuestionBank, QuestionCategory
        qb = QuestionBank()
        questions = qb.list_questions(category=QuestionCategory.SYSTEM_DESIGN)
        assert len(questions) > 0

    def test_algorithm_questions(self):
        """测试算法题目"""
        from app.interview.question_bank import QuestionBank, QuestionCategory
        qb = QuestionBank()
        questions = qb.list_questions(category=QuestionCategory.ALGORITHM)
        assert len(questions) > 0

    def test_ml_questions(self):
        """测试 ML/DL 题目"""
        from app.interview.question_bank import QuestionBank, QuestionCategory
        qb = QuestionBank()
        questions = qb.list_questions(category=QuestionCategory.ML_DL)
        assert len(questions) > 0

    def test_industry_questions(self):
        """测试行业知识题目"""
        from app.interview.question_bank import QuestionBank, QuestionCategory
        qb = QuestionBank()
        questions = qb.list_questions(category=QuestionCategory.INDUSTRY_KNOWLEDGE)
        assert len(questions) > 0

    def test_database_questions(self):
        """测试数据库题目"""
        from app.interview.question_bank import QuestionBank, QuestionCategory
        qb = QuestionBank()
        questions = qb.list_questions(category=QuestionCategory.DATABASE)
        assert len(questions) > 0


class TestInterviewSession:
    """面试会话测试"""

    def test_generate_interview(self):
        """测试生成面试"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        session = qb.generate_interview(
            target_position="后端工程师",
            target_companies=["字节跳动", "腾讯"],
            count=3,
        )
        assert session is not None
        assert session.session_id is not None
        assert len(session.question_ids) == 3
        assert session.status == "in_progress"

    def test_generate_interview_with_difficulty(self):
        """测试指定难度生成面试"""
        from app.interview.question_bank import QuestionBank, DifficultyLevel
        qb = QuestionBank()
        session = qb.generate_interview(
            target_position="算法工程师",
            difficulty=DifficultyLevel.HARD,
            count=3,
        )
        assert session is not None
        assert len(session.question_ids) >= 1

    def test_submit_answer_short(self):
        """测试提交过短答案"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        session = qb.generate_interview(target_position="测试", count=1)
        qid = session.question_ids[0]
        result = qb.submit_answer(session.session_id, qid, "很短")
        assert result["score"] == 0.0

    def test_submit_answer_normal(self):
        """测试提交正常答案"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        session = qb.generate_interview(target_position="测试", count=1)
        qid = session.question_ids[0]
        # 模拟一个较长答案
        answer = "这是一个关于Python的详细回答。GIL是全局解释器锁，它在同一时刻只允许一个线程执行Python字节码。这是为了保护引用计数。"
        result = qb.submit_answer(session.session_id, qid, answer)
        assert "score" in result
        assert "feedback" in result
        assert 0 <= result["score"] <= 100

    def test_complete_interview(self):
        """测试完成面试"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        session = qb.generate_interview(target_position="测试", count=1)
        qid = session.question_ids[0]
        qb.submit_answer(session.session_id, qid, "这是一个完整的回答，涉及多个关键点。")
        report = qb.complete_interview(session.session_id)
        assert "overall_score" in report
        assert "overall_comment" in report
        assert "category_scores" in report
        assert session.status == "completed"

    def test_session_progress(self):
        """测试会话进度"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        session = qb.generate_interview(target_position="测试", count=3)
        assert session.progress == "0/3"
        assert session.current_index == 0

    def test_session_to_dict(self):
        """测试会话序列化"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        session = qb.generate_interview(target_position="测试", count=1)
        d = session.to_dict()
        assert "session_id" in d
        assert "target_position" in d
        assert "question_ids" in d

    def test_multiple_sessions(self):
        """测试多个会话独立"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        s1 = qb.generate_interview(target_position="后端", count=1)
        s2 = qb.generate_interview(target_position="前端", count=1)
        assert s1.session_id != s2.session_id

    def test_get_next_follow_up(self):
        """测试追问生成"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        session = qb.generate_interview(target_position="测试", count=1)
        qid = session.question_ids[0]
        follow_up = qb.get_next_follow_up(session.session_id, qid)
        # 有追问的问题可能返回追问，也可能返回None
        assert follow_up is None or isinstance(follow_up, str)

    def test_interview_stats(self):
        """测试面试统计"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        sessions = qb.list_sessions()
        assert isinstance(sessions, list)


class TestEnums:
    """枚举测试"""

    def test_question_categories(self):
        """测试题目分类枚举"""
        from app.interview.question_bank import QuestionCategory
        assert QuestionCategory.TECHNICAL.value == "technical"
        assert QuestionCategory.BEHAVIORAL.value == "behavioral"
        assert QuestionCategory.SYSTEM_DESIGN.value == "system_design"

    def test_difficulty_levels(self):
        """测试难度枚举"""
        from app.interview.question_bank import DifficultyLevel
        assert DifficultyLevel.EASY.value == 1
        assert DifficultyLevel.MEDIUM.value == 2
        assert DifficultyLevel.HARD.value == 3
        assert DifficultyLevel.EXPERT.value == 4

    def test_question_types(self):
        """测试题目类型枚举"""
        from app.interview.question_bank import QuestionType
        assert QuestionType.OPEN_ENDED.value == "open_ended"
        assert QuestionType.WHITEBOARD.value == "whiteboard"
        assert QuestionType.SYSTEM_DESIGN.value == "system_design"


class TestAnswerEvaluation:
    """答案评测测试"""

    def test_keyword_matching(self):
        """测试关键词匹配"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        questions = qb.list_questions(limit=1)
        if questions:
            q = questions[0]
            # 包含关键词的答案应该得分更高
            weak_answer = "很短"
            strong_answer = " ".join(q.key_points[:2]) if q.key_points else "这是一个详细的回答"

            weak_result = qb._evaluate_answer(q, weak_answer)
            strong_result = qb._evaluate_answer(q, strong_answer)
            assert strong_result["score"] >= weak_result["score"]

    def test_empty_answer(self):
        """测试空答案"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        questions = qb.list_questions(limit=1)
        if questions:
            result = qb._evaluate_answer(questions[0], "")
            assert result["score"] == 0.0

    def test_feedback_generation(self):
        """测试反馈生成"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        questions = qb.list_questions(limit=1)
        if questions:
            result = qb._evaluate_answer(
                questions[0],
                "这是我的详细回答，包含多个关键点和技术细节。",
            )
            assert "feedback" in result
            assert len(result["feedback"]) > 0


class TestReportGeneration:
    """报告生成测试"""

    def test_report_format(self):
        """测试报告格式"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        session = qb.generate_interview(target_position="全栈工程师", count=1)
        qid = session.question_ids[0]
        qb.submit_answer(session.session_id, qid, "详细且全面的回答")
        report = qb.complete_interview(session.session_id)

        assert "session_id" in report
        assert "candidate_name" in report
        assert "target_position" in report
        assert "overall_score" in report
        assert "overall_comment" in report
        assert "category_scores" in report
        assert "recommendations" in report
        assert isinstance(report["recommendations"], list)

    def test_report_weak_areas(self):
        """测试报告薄弱环节识别"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        session = qb.generate_interview(target_position="后端", count=1)
        qid = session.question_ids[0]
        # 提交一个差答案
        qb.submit_answer(session.session_id, qid, "差")
        report = qb.complete_interview(session.session_id)
        assert report["overall_score"] is not None


class TestSkillFiltering:
    """技能筛选测试"""

    def test_filter_by_skill(self):
        """测试按技能标签筛选"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        questions = qb.list_questions(skills=["python"], limit=10)
        assert isinstance(questions, list)

    def test_filter_by_multiple_skills(self):
        """测试多技能筛选"""
        from app.interview.question_bank import QuestionBank
        qb = QuestionBank()
        questions = qb.list_questions(skills=["python", "mysql"], limit=10)
        assert isinstance(questions, list)
