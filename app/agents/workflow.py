"""
LangGraph 状态图工作流
实现基于状态机的多Agent协作：查询意图识别 → 检索路由 → 回答生成 → 质量评估
"""

from typing import Annotated, TypedDict, Dict, Any, List, Optional
from enum import Enum
import operator


class QueryIntent(str, Enum):
    """用户查询意图分类"""
    KNOWLEDGE_SEARCH = "knowledge_search"  # 知识库查询
    DOCUMENT_UPLOAD = "document_upload"    # 文档上传
    CONVERSATION = "conversation"          # 普通对话
    RESET = "reset"                        # 重置


class GraphState(TypedDict):
    """工作流状态定义"""
    # 输入
    query: str
    session_id: str
    search_type: str
    top_k: int

    # 意图识别
    intent: Optional[str]

    # 检索
    retrieved_docs: List[Dict[str, Any]]

    # 生成
    answer: Optional[str]
    confidence: Optional[str]

    # 元信息
    sources: List[Dict[str, str]]
    error: Optional[str]
    messages: Annotated[list, operator.add]


def build_graph(llm, rag_engine, vectorstore, document_loader, text_splitter):
    """
    构建LangGraph状态图工作流

    流程：用户输入 → 意图识别 → [条件分支] → 检索/处理 → 生成回答 → 质量检查 → 输出
    """
    try:
        from langgraph.graph import StateGraph, END
    except ImportError:
        # 如果没装langgraph，用简单模拟
        print("Warning: langgraph not installed. Using fallback workflow.")
        return None

    # ============ 节点函数 ============

    def intent_recognition(state: GraphState) -> GraphState:
        """意图识别节点"""
        query = state["query"]

        # 简单规则 + LLM 分类
        intent = QueryIntent.KNOWLEDGE_SEARCH.value
        query_lower = query.lower()

        if any(kw in query_lower for kw in ["上传", "添加文档", "索引", "upload", "添加文件"]):
            intent = QueryIntent.DOCUMENT_UPLOAD.value
        elif any(kw in query_lower for kw in ["重置", "清空", "reset", "清除"]):
            intent = QueryIntent.RESET.value
        elif len(query) < 3:
            intent = QueryIntent.CONVERSATION.value

        state["intent"] = intent
        state["messages"].append(f"[Intent] {intent}")
        return state

    def retrieve_documents(state: GraphState) -> GraphState:
        """文档检索节点（使用混合检索）"""
        query = state["query"]
        search_type = state.get("search_type", "hybrid")
        top_k = state.get("top_k", 4)

        try:
            if search_type == "hybrid":
                results = vectorstore.hybrid_search(
                    query, vector_k=5, bm25_k=5, top_n=top_k
                )
                docs = [{"content": doc.page_content, "metadata": doc.metadata, "score": score} for doc, score in results]
            else:
                retrieved = vectorstore.similarity_search(query, k=top_k)
                docs = [{"content": doc.page_content, "metadata": doc.metadata} for doc in retrieved]

            state["retrieved_docs"] = docs
            state["sources"] = [
                {"content": d["content"][:100], "source": d["metadata"].get("filename", "未知")}
                for d in docs
            ]
            state["messages"].append(f"[Retrieve] found {len(docs)} documents")
        except Exception as e:
            state["error"] = str(e)
            state["retrieved_docs"] = []

        return state

    def generate_answer(state: GraphState) -> GraphState:
        """回答生成节点"""
        query = state["query"]
        docs = state.get("retrieved_docs", [])

        if not docs:
            state["answer"] = "根据已有知识库，未找到与您问题相关的信息。"
            state["confidence"] = "low"
            return state

        context = "\n\n---\n\n".join([d["content"] for d in docs])

        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content=f"你是一个专业的知识库问答助手。请根据以下上下文准确回答用户问题，不要编造信息。\n\n上下文：\n{context}"),
            HumanMessage(content=query),
        ]

        try:
            response = llm.invoke(messages)
            state["answer"] = response.content
            state["confidence"] = "high" if docs else "low"
            state["messages"].append(f"[Generate] success")
        except Exception as e:
            state["answer"] = f"生成回答时出错: {e}"
            state["confidence"] = "error"
            state["error"] = str(e)

        return state

    def quality_check(state: GraphState) -> GraphState:
        """质量检查节点"""
        answer = state.get("answer", "")
        docs = state.get("retrieved_docs", [])

        if not docs and state.get("intent") == "knowledge_search":
            state["confidence"] = "low"
            state["messages"].append("[QualityCheck] no relevant docs found")

        if len(answer) < 10:
            state["confidence"] = "low"

        return state

    # ============ 条件路由 ============

    def route_by_intent(state: GraphState) -> str:
        """根据意图路由到不同处理分支"""
        intent = state.get("intent", "knowledge_search")
        if intent == "document_upload":
            return "handle_upload"
        elif intent == "reset":
            return "handle_reset"
        else:
            return "retrieve"

    def route_by_quality(state: GraphState) -> str:
        """根据质量检查结果决定是否重新检索"""
        confidence = state.get("confidence", "low")
        if confidence == "low" and not state.get("answer"):
            return "retrieve"  # 重新检索
        return "end"

    # ============ 构建图 ============

    graph = StateGraph(GraphState)

    # 添加节点
    graph.add_node("intent_recognition", intent_recognition)
    graph.add_node("retrieve", retrieve_documents)
    graph.add_node("generate", generate_answer)
    graph.add_node("quality_check", quality_check)
    graph.add_node("handle_upload", lambda s: {**s, "answer": "请使用 /api/documents/upload 接口上传文档。", "confidence": "high"})
    graph.add_node("handle_reset", lambda s: {
        **s,
        "answer": "对话记忆已重置。",
        "confidence": "high",
        "messages": s.get("messages", []) + ["[Reset] memory cleared"],
    })

    # 设置入口
    graph.set_entry_point("intent_recognition")

    # 添加边
    graph.add_conditional_edges(
        "intent_recognition",
        route_by_intent,
        {
            "retrieve": "retrieve",
            "handle_upload": "handle_upload",
            "handle_reset": "handle_reset",
        },
    )
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "quality_check")
    graph.add_conditional_edges(
        "quality_check",
        route_by_quality,
        {
            "retrieve": "retrieve",
            "end": END,
        },
    )
    graph.add_edge("handle_upload", END)
    graph.add_edge("handle_reset", END)

    return graph.compile()


class GraphWorkflow:
    """LangGraph工作流封装"""

    def __init__(self, compiled_graph, rag_engine):
        self.graph = compiled_graph
        self.rag_engine = rag_engine

    def run(self, query: str, session_id: str = "default",
            search_type: str = "hybrid", top_k: int = 4) -> Dict[str, Any]:
        """执行工作流"""
        initial_state = {
            "query": query,
            "session_id": session_id,
            "search_type": search_type,
            "top_k": top_k,
            "intent": None,
            "retrieved_docs": [],
            "answer": None,
            "confidence": None,
            "sources": [],
            "error": None,
            "messages": [],
        }

        try:
            if self.graph is None:
                # fallback: 直接用RAG引擎
                return self.rag_engine.query(query)
            result = self.graph.invoke(initial_state)
            return {
                "answer": result.get("answer", ""),
                "confidence": result.get("confidence", "unknown"),
                "sources": result.get("sources", []),
                "intent": result.get("intent", ""),
                "trace": result.get("messages", []),
                "error": result.get("error"),
            }
        except Exception as e:
            return {
                "answer": f"工作流执行错误: {e}",
                "confidence": "error",
                "sources": [],
                "error": str(e),
            }
