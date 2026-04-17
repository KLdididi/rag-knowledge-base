"""单元测试：记忆与 Agent 模块"""

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document


class TestMemoryResetEndpoint:
    """测试对话记忆管理接口"""

    def test_reset_single_session(self):
        """测试重置单个会话记忆（session_id 为 query 参数）"""
        from app.api.server import app
        from fastapi.testclient import TestClient
        mock_vs = MagicMock()
        mock_vs.document_count.return_value = 5
        mock_engine = MagicMock()
        with patch.multiple(
            "app.api.server",
            get_llm=MagicMock(),
            get_embeddings=MagicMock(),
            get_vectorstore=MagicMock(return_value=mock_vs),
            get_rag_engine=MagicMock(return_value=mock_engine),
        ):
            client = TestClient(app)
            # session_id 是 query 参数，不是 body
            response = client.post("/api/memory/reset?session_id=test_session_123")
            assert response.status_code == 200
            mock_engine.reset_memory.assert_called_once_with("test_session_123")

    def test_reset_all_sessions(self):
        """测试重置所有会话记忆"""
        from app.api.server import app
        from fastapi.testclient import TestClient
        mock_vs = MagicMock()
        mock_vs.document_count.return_value = 5
        mock_engine = MagicMock()
        with patch.multiple(
            "app.api.server",
            get_llm=MagicMock(),
            get_embeddings=MagicMock(),
            get_vectorstore=MagicMock(return_value=mock_vs),
            get_rag_engine=MagicMock(return_value=mock_engine),
        ):
            client = TestClient(app)
            response = client.post("/api/memory/reset-all")
            assert response.status_code == 200
            mock_engine.reset_all_memories.assert_called_once()


class TestAgentEndpoint:
    """测试 Agent 问答接口"""

    def test_agent_query(self):
        """测试 Agent 问答（使用 QueryRequest，返回 AgentResponse）"""
        from app.api.server import app
        from fastapi.testclient import TestClient
        mock_workflow = MagicMock()
        mock_workflow.run.return_value = {
            "answer": "Agent 分析结果：这是一个技术问题。",
            "sources": [{"source": "test.md"}],
        }
        mock_vs = MagicMock()
        mock_vs.document_count.return_value = 5
        with patch.multiple(
            "app.api.server",
            get_llm=MagicMock(),
            get_embeddings=MagicMock(),
            get_vectorstore=MagicMock(return_value=mock_vs),
            get_graph_workflow=MagicMock(return_value=mock_workflow),
        ):
            client = TestClient(app)
            response = client.post(
                "/api/agent",
                json={
                    "query": "分析这个技术问题",
                    "top_k": 4,  # QueryRequest 字段
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert data["agent_type"] == "langgraph"

    def test_agent_default_mode(self):
        """测试 Agent 默认参数"""
        from app.api.server import app
        from fastapi.testclient import TestClient
        mock_workflow = MagicMock()
        mock_workflow.run.return_value = {"answer": "默认模式回答", "sources": []}
        mock_vs = MagicMock()
        mock_vs.document_count.return_value = 5
        with patch.multiple(
            "app.api.server",
            get_llm=MagicMock(),
            get_embeddings=MagicMock(),
            get_vectorstore=MagicMock(return_value=mock_vs),
            get_graph_workflow=MagicMock(return_value=mock_workflow),
        ):
            client = TestClient(app)
            response = client.post("/api/agent", json={"query": "Agent 测试"})
            assert response.status_code == 200
            data = response.json()
            assert data["agent_type"] == "langgraph"


class TestGraphEndpoint:
    """测试 LangGraph 工作流接口"""

    def test_graph_workflow(self):
        """测试 LangGraph 状态图执行"""
        from app.api.server import app
        from fastapi.testclient import TestClient
        mock_workflow = MagicMock()
        mock_workflow.run.return_value = {
            "answer": "工作流生成的回答",
            "confidence": "high",
            "sources": [{"content": "doc", "source": "test.md"}],
        }
        mock_vs = MagicMock()
        mock_vs.document_count.return_value = 5
        with patch.multiple(
            "app.api.server",
            get_llm=MagicMock(),
            get_embeddings=MagicMock(),
            get_vectorstore=MagicMock(return_value=mock_vs),
            get_graph_workflow=MagicMock(return_value=mock_workflow),
        ):
            client = TestClient(app)
            response = client.post(
                "/api/graph",
                json={
                    "query": "LangGraph 工作流测试",
                    "session_id": "graph_test",
                    "search_type": "hybrid",
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data

    def test_graph_custom_params(self):
        """测试 GraphRequest 自定义参数"""
        from app.api.server import app
        from fastapi.testclient import TestClient
        mock_workflow = MagicMock()
        mock_workflow.run.return_value = {"answer": "回答", "sources": [], "confidence": "high"}
        mock_vs = MagicMock()
        mock_vs.document_count.return_value = 3
        with patch.multiple(
            "app.api.server",
            get_llm=MagicMock(),
            get_embeddings=MagicMock(),
            get_vectorstore=MagicMock(return_value=mock_vs),
            get_graph_workflow=MagicMock(return_value=mock_workflow),
        ):
            client = TestClient(app)
            response = client.post(
                "/api/graph",
                json={"query": "参数测试", "search_type": "mmr", "session_id": "custom"}
            )
            assert response.status_code == 200
            # 验证参数传递
            mock_workflow.run.assert_called_once()
            call_kwargs = mock_workflow.run.call_args[1]
            assert call_kwargs["session_id"] == "custom"
            assert call_kwargs["search_type"] == "mmr"


class TestStreamingEndpoint:
    """测试流式输出接口"""

    def test_streaming_response_format(self):
        """测试 SSE 流式响应格式"""
        from app.api.server import app
        from fastapi.testclient import TestClient
        mock_llm = MagicMock()
        mock_llm.astream = MagicMock(return_value=iter([
            MagicMock(content="这"),
            MagicMock(content="是"),
            MagicMock(content="流"),
        ]))
        mock_vs = MagicMock()
        mock_vs.document_count.return_value = 5
        mock_vs.hybrid_search.return_value = [
            (Document(page_content="相关文档", metadata={"filename": "doc.md"}), 0.9)
        ]
        with patch.multiple(
            "app.api.server",
            get_llm=MagicMock(return_value=mock_llm),
            get_embeddings=MagicMock(),
            get_vectorstore=MagicMock(return_value=mock_vs),
        ):
            client = TestClient(app)
            with client.stream("POST", "/api/query/stream", json={"query": "流式测试"}) as response:
                assert response.status_code == 200
                chunks = list(response.iter_lines())
                assert any("data:" in line for line in chunks)


class TestUploadEndpoint:
    """测试文档上传接口"""

    def test_upload_text_file(self, tmp_path):
        """测试上传文本文件"""
        from app.api.server import app
        from fastapi.testclient import TestClient
        test_file = tmp_path / "upload_test.txt"
        test_file.write_text("这是上传的测试文档内容。", encoding="utf-8")
        mock_vs = MagicMock()
        mock_vs.document_count.return_value = 0
        mock_loader = MagicMock()
        mock_loader.load_file.return_value = [Document(page_content="测试内容", metadata={})]
        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = [
            Document(page_content="测试内容", metadata={"chunk_index": 0})
        ]
        mock_embeddings = MagicMock()
        mock_embeddings.embed_documents.return_value = [[0.1] * 384]
        with patch.multiple(
            "app.api.server",
            get_llm=MagicMock(),
            get_embeddings=MagicMock(return_value=mock_embeddings),
            get_vectorstore=MagicMock(return_value=mock_vs),
            get_document_loader=MagicMock(return_value=mock_loader),
            get_text_splitter=MagicMock(return_value=mock_splitter),
        ):
            client = TestClient(app)
            with open(test_file, "rb") as f:
                response = client.post(
                    "/api/documents/upload",
                    files={"file": ("test.txt", f, "text/plain")}
                )
            assert response.status_code == 200
            data = response.json()
            assert "chunks" in data
            assert data["filename"] == "test.txt"

    def test_upload_unsupported_format(self, tmp_path):
        """测试上传不支持的格式"""
        from app.api.server import app
        from fastapi.testclient import TestClient
        mock_vs = MagicMock()
        mock_vs.document_count.return_value = 0
        test_file = tmp_path / "test.xyz"
        test_file.write_bytes(b"random data")
        with patch.multiple(
            "app.api.server",
            get_llm=MagicMock(),
            get_embeddings=MagicMock(),
            get_vectorstore=MagicMock(return_value=mock_vs),
        ):
            client = TestClient(app)
            with open(test_file, "rb") as f:
                response = client.post(
                    "/api/documents/upload",
                    files={"file": ("test.xyz", f, "application/octet-stream")}
                )
            assert response.status_code == 400


class TestErrorHandling:
    """测试错误处理"""

    def test_missing_query_field(self):
        """测试缺少查询字段"""
        from app.api.server import app
        from fastapi.testclient import TestClient
        mock_vs = MagicMock()
        mock_vs.document_count.return_value = 5
        with patch.multiple(
            "app.api.server",
            get_llm=MagicMock(),
            get_embeddings=MagicMock(),
            get_vectorstore=MagicMock(return_value=mock_vs),
        ):
            client = TestClient(app)
            response = client.post("/api/query", json={})
            assert response.status_code == 422  # FastAPI validation error

    def test_empty_query_rejected(self):
        """测试空查询被验证拒绝"""
        from app.api.server import app
        from fastapi.testclient import TestClient
        mock_vs = MagicMock()
        mock_vs.document_count.return_value = 5
        with patch.multiple(
            "app.api.server",
            get_llm=MagicMock(),
            get_embeddings=MagicMock(),
            get_vectorstore=MagicMock(return_value=mock_vs),
        ):
            client = TestClient(app)
            response = client.post("/api/query", json={"query": ""})
            assert response.status_code == 422  # min_length=1 validation
