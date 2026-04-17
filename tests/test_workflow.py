"""单元测试：LangGraph 工作流模块"""

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document


class TestGraphState:
    """测试工作流状态定义"""

    def test_graph_state_structure(self):
        """测试 GraphState 结构"""
        from app.agents.workflow import GraphState
        state = GraphState(
            query="测试查询",
            session_id="test",
            search_type="hybrid",
            top_k=4,
            intent=None,
            retrieved_docs=[],
            answer=None,
            confidence=None,
            sources=[],
            error=None,
            messages=[],
        )
        assert state["query"] == "测试查询"
        assert state["session_id"] == "test"
        assert state["search_type"] == "hybrid"
        assert state["top_k"] == 4

    def test_graph_state_messages_annotation(self):
        """测试 GraphState messages 支持 Annotated list"""
        from app.agents.workflow import GraphState
        state = GraphState(
            query="测试",
            session_id="test",
            search_type="similarity",
            top_k=2,
            intent="knowledge_search",
            retrieved_docs=[],
            answer=None,
            confidence=None,
            sources=[],
            error=None,
            messages=["[Intent] knowledge_search", "[Retrieve] found 0 documents"],
        )
        assert len(state["messages"]) == 2
        assert "[Intent]" in state["messages"][0]


class TestQueryIntent:
    """测试查询意图枚举"""

    def test_intent_enum_values(self):
        """测试意图枚举值"""
        from app.agents.workflow import QueryIntent
        assert QueryIntent.KNOWLEDGE_SEARCH.value == "knowledge_search"
        assert QueryIntent.DOCUMENT_UPLOAD.value == "document_upload"
        assert QueryIntent.CONVERSATION.value == "conversation"
        assert QueryIntent.RESET.value == "reset"

    def test_intent_is_string(self):
        """测试枚举可作为字符串使用"""
        from app.agents.workflow import QueryIntent
        assert isinstance(QueryIntent.KNOWLEDGE_SEARCH.value, str)


class TestBuildGraph:
    """测试图构建功能"""

    def test_build_graph_returns_compiled(self):
        """测试 build_graph 返回编译后的图"""
        from app.agents.workflow import build_graph
        mock_llm = MagicMock()
        mock_rag = MagicMock()
        mock_vs = MagicMock()
        mock_loader = MagicMock()
        mock_splitter = MagicMock()

        # Mock langgraph components (imported inside build_graph as `from langgraph.graph import ...`)
        mock_graph_instance = MagicMock()
        mock_compiled = MagicMock()
        mock_graph_instance.compile.return_value = mock_compiled

        mock_sg = MagicMock(return_value=mock_graph_instance)
        mock_end = MagicMock()

        with patch.dict("sys.modules", {"langgraph.graph": MagicMock()}):
            import sys
            sys.modules["langgraph.graph"].StateGraph = mock_sg
            sys.modules["langgraph.graph"].END = mock_end
            result = build_graph(mock_llm, mock_rag, mock_vs, mock_loader, mock_splitter)
            assert result == mock_compiled
            added_nodes = [call[0][0] for call in mock_graph_instance.add_node.call_args_list]
            assert "intent_recognition" in added_nodes
            assert "retrieve" in added_nodes
            assert "generate" in added_nodes
            assert "quality_check" in added_nodes


class TestGraphWorkflow:
    """测试工作流封装类"""

    def test_graph_workflow_run_with_fallback(self):
        """测试 fallback 模式（无 langgraph 图）"""
        from app.agents.workflow import GraphWorkflow
        mock_rag = MagicMock()
        mock_rag.query.return_value = {"answer": "fallback回答", "sources": []}
        workflow = GraphWorkflow(compiled_graph=None, rag_engine=mock_rag)
        result = workflow.run("测试查询")
        assert result["answer"] == "fallback回答"
        mock_rag.query.assert_called_once_with("测试查询")

    def test_graph_workflow_run_with_graph(self):
        """测试有图时的执行"""
        from app.agents.workflow import GraphWorkflow
        mock_rag = MagicMock()
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "query": "测试查询",
            "session_id": "test_session",
            "search_type": "hybrid",
            "top_k": 4,
            "intent": "knowledge_search",
            "retrieved_docs": [
                {"content": "文档内容", "metadata": {"filename": "test.md"}}
            ],
            "answer": "LangGraph 生成的回答",
            "confidence": "high",
            "sources": [{"content": "文档内容", "source": "test.md"}],
            "error": None,
            "messages": ["[Intent] knowledge_search", "[Retrieve] found 1 documents"],
        }
        workflow = GraphWorkflow(compiled_graph=mock_graph, rag_engine=mock_rag)
        result = workflow.run("测试查询", session_id="test_session", search_type="hybrid")
        assert result["answer"] == "LangGraph 生成的回答"
        assert result["confidence"] == "high"
        assert result["intent"] == "knowledge_search"
        assert len(result["trace"]) == 2

    def test_graph_workflow_run_with_error(self):
        """测试工作流执行异常处理"""
        from app.agents.workflow import GraphWorkflow
        mock_rag = MagicMock()
        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = Exception("Graph execution failed")
        workflow = GraphWorkflow(compiled_graph=mock_graph, rag_engine=mock_rag)
        result = workflow.run("测试查询")
        assert "工作流执行错误" in result["answer"]
        assert result["confidence"] == "error"
        assert result["error"] == "Graph execution failed"

    def test_graph_workflow_custom_parameters(self):
        """测试自定义参数传递"""
        from app.agents.workflow import GraphWorkflow
        mock_rag = MagicMock()
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "query": "自定义查询",
            "session_id": "custom_session",
            "search_type": "mmr",
            "top_k": 6,
            "intent": "knowledge_search",
            "retrieved_docs": [],
            "answer": "回答",
            "confidence": "high",
            "sources": [],
            "error": None,
            "messages": [],
        }
        workflow = GraphWorkflow(compiled_graph=mock_graph, rag_engine=mock_rag)
        result = workflow.run("自定义查询", session_id="custom_session", search_type="mmr", top_k=6)
        call_args = mock_graph.invoke.call_args[0][0]
        assert call_args["session_id"] == "custom_session"
        assert call_args["search_type"] == "mmr"
        assert call_args["top_k"] == 6

    def test_graph_workflow_empty_docs(self):
        """测试无相关文档时的处理"""
        from app.agents.workflow import GraphWorkflow
        mock_rag = MagicMock()
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "query": "",
            "session_id": "default",
            "search_type": "hybrid",
            "top_k": 4,
            "intent": "conversation",
            "retrieved_docs": [],
            "answer": "请提供有效的查询内容。",
            "confidence": "high",
            "sources": [],
            "error": None,
            "messages": ["[Intent] conversation"],
        }
        workflow = GraphWorkflow(compiled_graph=mock_graph, rag_engine=mock_rag)
        result = workflow.run("")
        assert "answer" in result

    def test_graph_workflow_returns_trace(self):
        """测试 trace 字段存在"""
        from app.agents.workflow import GraphWorkflow
        mock_rag = MagicMock()
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "query": "trace测试",
            "session_id": "default",
            "search_type": "hybrid",
            "top_k": 4,
            "intent": "knowledge_search",
            "retrieved_docs": [],
            "answer": "回答",
            "confidence": "high",
            "sources": [],
            "error": None,
            "messages": ["[Intent] knowledge_search", "[Retrieve] found 0 documents", "[Generate] success"],
        }
        workflow = GraphWorkflow(compiled_graph=mock_graph, rag_engine=mock_rag)
        result = workflow.run("trace测试")
        assert "trace" in result
        assert isinstance(result["trace"], list)
        assert len(result["trace"]) == 3
