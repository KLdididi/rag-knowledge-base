"""
面试专用功能 - Gradio UI

提供：面试题库浏览、模拟面试对话、面试报告
"""

import gradio as gr
from gradio.misc import Axis
import json
import time
from datetime import datetime

# ============================================================
# 面试 UI 配置
# ============================================================

INTERVIEW_CSS = """
.interview-card {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
}
.score-badge {
    font-size: 24px;
    font-weight: bold;
}
.score-high { color: #22c55e; }
.score-medium { color: #f59e0b; }
.score-low { color: #ef4444; }
.category-tag {
    background: #3b82f6;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
}
.difficulty-easy { color: #22c55e; }
.difficulty-medium { color: #f59e0b; }
.difficulty-hard { color: #ef4444; }
.difficulty-expert { color: #8b5cf6; }
"""


# ============================================================
# 面试会话状态管理
# ============================================================

class InterviewState:
    """面试会话状态"""

    def __init__(self):
        self.session_id: str = ""
        self.questions: list = []
        self.current_index: int = 0
        self.answers: dict = {}
        self.scores: dict = {}
        self.feedback: dict = {}
        self.current_question: dict = {}

    def reset(self):
        self.__init__()

    def is_complete(self) -> bool:
        return self.current_index >= len(self.questions)


# ============================================================
# API 交互（通过 FastAPI）
# ============================================================

def api_get(path: str, params: dict = None):
    """简单的 API 调用"""
    import requests
    base = "http://localhost:8000"
    try:
        resp = requests.get(f"{base}{path}", params=params, timeout=5)
        return resp.json()
    except Exception as e:
        return {"error": f"无法连接服务器: {e}"}


def api_post(path: str, data: dict):
    """POST 请求"""
    import requests
    base = "http://localhost:8000"
    try:
        resp = requests.post(f"{base}{path}", json=data, timeout=30)
        return resp.json()
    except Exception as e:
        return {"error": f"无法连接服务器: {e}"}


# ============================================================
# Gradio 界面组件
# ============================================================

def create_question_card(q: dict) -> str:
    """创建题目卡片 HTML"""
    diff_names = {1: "简单", 2: "中等", 3: "困难", 4: "专家"}
    diff_colors = {1: "easy", 2: "medium", 3: "hard", 4: "expert"}
    diff = q.get("difficulty", 2)

    category = q.get("category", "")
    cat_names = {
        "technical": "技术",
        "behavioral": "行为",
        "system_design": "系统设计",
        "algorithm": "算法",
        "database": "数据库",
        "ml_dl": "ML/DL",
        "soft_skills": "软技能",
        "industry_knowledge": "行业知识",
    }
    cat_display = cat_names.get(category, category)

    return f"""
    <div class='interview-card'>
        <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;'>
            <span class='category-tag'>{cat_display}</span>
            <span class='difficulty-{diff_colors.get(diff, "medium")}'>★ {diff_names.get(diff, "中等")}</span>
        </div>
        <p style='font-size:16px; font-weight:500; margin:10px 0;'>{q.get('question_text', '')}</p>
        <p style='color:#666; font-size:13px;'>预计回答时间：{q.get('estimated_time_minutes', 5)} 分钟</p>
    </div>
    """


def create_score_badge(score: float) -> str:
    """创建分数徽章"""
    if score is None:
        return "<span class='score-badge score-medium'>—</span>"
    if score >= 80:
        cls = "score-high"
        emoji = "🌟"
    elif score >= 60:
        cls = "score-medium"
        emoji = "👍"
    else:
        cls = "score-low"
        emoji = "📚"
    return f"<span class='score-badge {cls}'>{emoji} {score:.0f}分</span>"


def create_feedback_card(q: dict, answer: str, score: float, feedback: str) -> str:
    """创建反馈卡片"""
    return f"""
    <div class='interview-card' style='border-left: 4px solid #3b82f6;'>
        <p style='font-size:14px; font-weight:bold; margin-bottom:5px;'>📝 你的回答：</p>
        <p style='color:#333; margin-bottom:15px;'>{answer}</p>
        <div style='margin-bottom:15px;'>{create_score_badge(score)}</div>
        <p style='font-size:14px; font-weight:bold; margin-bottom:5px;'>💡 评价：</p>
        <p style='color:#555;'>{feedback}</p>
        <p style='font-size:13px; color:#666; margin-top:10px;'>关键点：{', '.join(q.get('key_points', [])[:3])}</p>
    </div>
    """


# ============================================================
# 界面功能函数
# ============================================================

def load_question_bank(category: str = "all", difficulty: int = 0):
    """加载题库"""
    params = {}
    if category and category != "all":
        params["category"] = category
    if difficulty and difficulty > 0:
        params["difficulty"] = difficulty
    result = api_get("/api/interview/questions", params)
    if "error" in result:
        return [], f"❌ {result['error']}"
    questions = result if isinstance(result, list) else []
    cards = [create_question_card(q) for q in questions]
    return cards, f"📚 共找到 {len(questions)} 道题目"


def start_interview(target_position: str, companies: str, difficulty: int, count: int):
    """开始一场模拟面试"""
    if not target_position:
        return "❌ 请输入目标岗位", "", "", "", "", ""

    company_list = [c.strip() for c in companies.split(",") if c.strip()]
    req = {
        "target_position": target_position,
        "target_companies": company_list,
        "difficulty": difficulty if difficulty > 0 else None,
        "count": count,
    }
    result = api_post("/api/interview/interview/generate", req)
    if "error" in result:
        return f"❌ {result['error']}", "", "", "", "", ""

    state = InterviewState()
    state.session_id = result["session_id"]
    state.questions = result.get("questions", [])
    state.current_index = 0

    if state.questions:
        state.current_question = state.questions[0]
        q = state.current_question
        question_html = create_question_card(q)
        tips = f"⏱️ 预计回答时间：{q.get('estimated_time_minutes', 5)} 分钟"
        tips += f"\n🏷️ 技能标签：{', '.join(q.get('skills_tags', []))}"
    else:
        question_html = "❌ 未找到适合的题目"
        tips = ""

    return (
        f"✅ 面试已开始！Session: {state.session_id}",
        question_html,
        "",
        tips,
        f"0/{len(state.questions)}",
        "in_progress",
    )


def submit_interview_answer(answer: str, state_str: str):
    """提交答案"""
    if not answer or not answer.strip():
        return "❌ 请先回答问题", "", state_str

    state = InterviewState()
    if not state.session_id:
        return "❌ 请先开始面试", "", ""

    if not state.current_question:
        return "❌ 当前没有题目", "", ""

    req = {
        "question_id": state.current_question["id"],
        "answer": answer,
    }
    result = api_post(f"/api/interview/interview/{state.session_id}/answer", req)
    if "error" in result:
        return f"❌ {result['error']}", "", state_str

    eval_result = result.get("evaluation", {})
    score = eval_result.get("score")
    feedback = eval_result.get("feedback", "")

    state.answers[state.current_question["id"]] = answer
    state.scores[state.current_question["id"]] = score
    state.feedback[state.current_question["id"]] = feedback

    # 构建反馈卡片
    q = state.current_question
    q_full = api_get(f"/api/interview/questions/{q['id']}/answer")
    feedback_html = create_feedback_card(
        q_full if isinstance(q_full, dict) else q,
        answer,
        score,
        feedback,
    )

    # 获取下一题
    progress = result.get("progress", "")
    next_q = result.get("next_question")
    if next_q:
        state.current_question = next_q
        state.current_index += 1
        question_html = create_question_card(next_q)
        tips = f"⏱️ 预计回答时间：{next_q.get('estimated_time_minutes', 5)} 分钟"
        tips += f"\n🏷️ 技能标签：{', '.join(next_q.get('skills_tags', []))}"
        next_btn = gr.update(visible=True)
        answer_box = gr.update(value="")
    else:
        question_html = ""
        tips = "🎉 所有题目回答完毕！点击「完成面试」查看报告"
        next_btn = gr.update(visible=False)

    state_str = f"idx:{state.current_index}|total:{len(state.questions)}"
    return feedback_html, question_html, state_str


def finish_interview(state_str: str):
    """完成面试，生成报告"""
    state = InterviewState()
    if not state.session_id:
        return "❌ 请先开始面试"

    result = api_post(f"/api/interview/interview/{state.session_id}/complete", {})
    if "error" in result:
        return f"❌ {result['error']}"

    score = result.get("overall_score", 0)
    comment = result.get("overall_comment", "")
    cat_scores = result.get("category_scores", {})
    recs = result.get("recommendations", [])

    report = f"""
    <div class='interview-card'>
        <h2>📊 面试报告</h2>
        <div style='text-align:center; margin:20px 0;'>
            {create_score_badge(score)}
        </div>
        <p style='font-size:16px; text-align:center;'>{comment}</p>
        <hr style='margin:20px 0;'>
        <h3>📈 分类得分</h3>
        <div style='display:flex; flex-wrap:wrap; gap:10px;'>
    """

    cat_names = {
        "technical": "技术 🖥️",
        "behavioral": "行为 👥",
        "system_design": "系统设计 🏗️",
        "algorithm": "算法 💻",
        "database": "数据库 🗄️",
        "ml_dl": "ML/DL 🤖",
        "soft_skills": "软技能 💬",
        "industry_knowledge": "行业 📚",
    }
    for cat, avg in cat_scores.items():
        cat_display = cat_names.get(cat, cat)
        bar = "█" * int(avg / 10) + "░" * (10 - int(avg / 10))
        color = "#22c55e" if avg >= 70 else "#f59e0b" if avg >= 50 else "#ef4444"
        report += f"<p>{cat_display}: <span style='color:{color};'>{bar} {avg:.0f}分</span></p>"

    report += """
        </div>
        <hr style='margin:20px 0;'>
        <h3>💡 改进建议</h3>
        <ul>
    """
    for rec in recs:
        report += f"<li>{rec}</li>"
    report += """
        </ul>
        <p style='color:#666; font-size:12px; margin-top:20px;'>
            面试时长：{duration} 分钟 | 完成时间：{now}
        </p>
    </div>
    """.format(
        duration=result.get("total_duration_minutes", 0),
        now=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    return report


# ============================================================
# 构建 Gradio 界面
# ============================================================

def build_interview_ui() -> gr.Blocks:
    """构建面试 UI"""

    with gr.Blocks(
        title="模拟面试",
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="emerald",
        ),
        css=INTERVIEW_CSS,
    ) as demo:
        gr.Markdown("# 🎯 模拟面试系统")
        gr.Markdown("基于 AI 的智能面试练习，涵盖技术/算法/System Design/行为问题")

        with gr.Tabs():
            # ---- Tab 1: 题库浏览 ----
            with gr.TabItem("📚 题库浏览"):
                with gr.Row():
                    with gr.Column(scale=1):
                        category_dd = gr.Dropdown(
                            choices=[
                                "all: 全部",
                                "technical: 技术",
                                "behavioral: 行为",
                                "system_design: 系统设计",
                                "algorithm: 算法",
                                "database: 数据库",
                                "ml_dl: ML/DL",
                                "soft_skills: 软技能",
                                "industry_knowledge: 行业知识",
                            ],
                            value="all: 全部",
                            label="题目分类",
                        )
                        difficulty_sl = gr.Slider(
                            minimum=0, maximum=4, step=1, value=0,
                            label="难度等级 (0=不限)",
                            info="1=简单, 2=中等, 3=困难, 4=专家",
                        )
                        search_btn = gr.Button("🔍 搜索题目", variant="primary")

                    with gr.Column(scale=3):
                        question_list = gr.HTML(label="题目列表")
                        status_box = gr.Textbox(label="状态", lines=1)

                search_btn.click(
                    fn=load_question_bank,
                    inputs=[category_dd, difficulty_sl],
                    outputs=[question_list, status_box],
                )

            # ---- Tab 2: 模拟面试 ----
            with gr.TabItem("🎤 模拟面试"):
                gr.Markdown("### 🎯 开始面试")
                with gr.Row():
                    with gr.Column(scale=1):
                        target_position = gr.Textbox(
                            label="🎯 目标岗位",
                            placeholder="例如：后端工程师 / 算法工程师",
                            lines=1,
                        )
                        companies = gr.Textbox(
                            label="🏢 目标公司（可选）",
                            placeholder="例如：字节跳动, 腾讯, 阿里巴巴",
                            lines=1,
                            info="提供后优先推送相关高频题",
                        )
                        with gr.Row():
                            difficulty_sl = gr.Slider(
                                minimum=0, maximum=4, step=1, value=0,
                                label="难度",
                            )
                            count_sl = gr.Slider(
                                minimum=3, maximum=15, step=1, value=5,
                                label="题目数量",
                            )
                        start_btn = gr.Button("🚀 开始面试", variant="primary", size="lg")

                    with gr.Column(scale=2):
                        progress_text = gr.HTML(
                            '<p style="color:#666;">准备开始...</p>'
                        )

                gr.Markdown("---")
                gr.Markdown("### 📋 当前题目")
                current_question = gr.HTML(label="")
                tips_box = gr.Textbox(label="提示", lines=2, interactive=False)

                gr.Markdown("### ✍️ 你的回答")
                answer_input = gr.TextArea(
                    label="",
                    placeholder="请用 STAR 法则组织你的回答...",
                    lines=5,
                )
                with gr.Row():
                    submit_btn = gr.Button("📤 提交回答", variant="primary")
                    next_btn = gr.Button("➡️ 下一题", visible=False)
                    finish_btn = gr.Button("🏁 完成面试", variant="stop")

                gr.Markdown("---")
                gr.Markdown("### 📝 回答反馈")
                feedback_area = gr.HTML(label="")

                state_hidden = gr.Textbox(visible=False)

                start_btn.click(
                    fn=start_interview,
                    inputs=[target_position, companies, difficulty_sl, count_sl],
                    outputs=[status_box, current_question, answer_input, tips_box, progress_text, state_hidden],
                )

                submit_btn.click(
                    fn=submit_interview_answer,
                    inputs=[answer_input, state_hidden],
                    outputs=[feedback_area, current_question, state_hidden],
                )

                finish_btn.click(
                    fn=finish_interview,
                    inputs=[state_hidden],
                    outputs=[feedback_area],
                )

            # ---- Tab 3: 历史记录 ----
            with gr.TabItem("📜 面试记录"):
                gr.Markdown("### 📜 历史面试记录")
                history_btn = gr.Button("🔄 刷新记录")

                def load_history():
                    result = api_get("/api/interview/interviews/history")
                    if "error" in result:
                        return f"<p>❌ {result['error']}</p>"

                    sessions = result if isinstance(result, list) else []
                    if not sessions:
                        return "<p>暂无面试记录</p>"

                    html = "<div>"
                    for s in sessions[:20]:
                        score = s.get("overall_score")
                        status_emoji = "✅" if s.get("status") == "completed" else "🔄"
                        score_str = f"{score:.0f}分" if score else "未评分"
                        html += f"""
                        <div class='interview-card'>
                            {status_emoji} <b>{s.get('target_position', '')}</b>
                            | 进度: {s.get('progress', '')}
                            | 得分: {score_str}
                            | {s.get('started_at', '')[:10] if s.get('started_at') else ''}
                        </div>
                        """
                    html += "</div>"
                    return html

                history_output = gr.HTML()
                history_btn.click(fn=load_history, inputs=[], outputs=[history_output])
                history_output.change(fn=load_history, inputs=[], outputs=[history_output])

    return demo


if __name__ == "__main__":
    ui = build_interview_ui()
    ui.launch(server_name="0.0.0.0", server_port=7861)
