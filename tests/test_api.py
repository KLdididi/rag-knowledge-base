"""API集成测试"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_llm():
    """模拟LLM"""
    llm = MagicMock()
    response = MagicMock()
    response.content = "这是测试回答。"
    llm.invoke.return_value = response
    return llm


@pytest.fixture
def mock_embeddings():
    return MagicMock()


@pytest.fixture
def mock_vectorstore(mock_embeddings):
    vs = MagicMock()
    vs.document_count.return_value = 10
    vs.similarity_search.return_value = [
        MagicMock(page_content="测试文档内容", metadata={"filename": "test.pdf"})
    ]
    return vs


class TestHealthEndpoint:
    def test_health_check(self, mock_vectorstore):
        from app.api.server import app
        with patch("app.api.server.get_vectorstore", return_value=mock_vectorstore):
            client = TestClient(app)
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["version"] == "2.0.0"
            assert data["document_count"] == 10
            assert ".pdf" in data["supported_formats"]


class TestDocumentCountEndpoint:
    def test_get_document_count(self, mock_vectorstore):
        from app.api.server import app
        with patch("app.api.server.get_vectorstore", return_value=mock_vectorstore):
            client = TestClient(app)
            response = client.get("/api/documents/count")
            assert response.status_code == 200
            assert response.json()["count"] == 10


class TestQueryEndpoint:
    def test_query_knowledge_base(self, mock_llm, mock_embeddings, mock_vectorstore):
        from app.api.server import app
        with patch.multiple(
            "app.api.server",
            get_llm=MagicMock(return_value=mock_llm),
            get_embeddings=MagicMock(return_value=mock_embeddings),
            get_vectorstore=MagicMock(return_value=mock_vectorstore),
        ):
            client = TestClient(app)
            response = client.post(
                "/api/query",
                json={"query": "什么是RAG", "top_k": 4, "return_sources": False}
            )
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert "question" in data
