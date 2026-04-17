"""单元测试：核心模块"""

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document


class TestTextSplitter:
    """测试文本切分模块"""

    def test_split_documents(self):
        from app.core.splitter import TextSplitter
        splitter = TextSplitter(chunk_size=100, chunk_overlap=20)
        docs = [Document(page_content="这是一段测试文本。" * 20, metadata={"source": "test.txt"})]
        chunks = splitter.split_documents(docs)
        assert len(chunks) > 1
        assert all(c.page_content for c in chunks)

    def test_split_preserves_metadata(self):
        from app.core.splitter import TextSplitter
        splitter = TextSplitter(chunk_size=50, chunk_overlap=10)
        docs = [Document(page_content="测试文档内容。" * 15, metadata={"source": "test.pdf"})]
        chunks = splitter.split_and_preserve_metadata(docs)
        assert len(chunks) > 1
        assert all("chunk_index" in c.metadata for c in chunks)

    def test_split_empty_documents(self):
        from app.core.splitter import TextSplitter
        splitter = TextSplitter()
        docs = [Document(page_content="", metadata={"source": "empty.txt"})]
        chunks = splitter.split_documents(docs)
        assert len(chunks) == 0


class TestDocumentLoader:
    """测试文档加载模块"""

    def test_supported_extensions(self):
        from app.core.loader import DocumentLoader
        loader = DocumentLoader()
        assert ".pdf" in loader.SUPPORTED_EXTENSIONS
        assert ".docx" in loader.SUPPORTED_EXTENSIONS
        assert ".txt" in loader.SUPPORTED_EXTENSIONS
        assert ".md" in loader.SUPPORTED_EXTENSIONS
        assert ".csv" in loader.SUPPORTED_EXTENSIONS

    def test_load_text_file(self, tmp_path):
        from app.core.loader import DocumentLoader
        loader = DocumentLoader()
        test_file = tmp_path / "test.txt"
        test_file.write_text("这是一个测试文档。", encoding="utf-8")
        docs = loader.load_file(str(test_file))
        assert len(docs) == 1
        assert "测试文档" in docs[0].page_content
        assert docs[0].metadata["filename"] == "test.txt"

    def test_load_unsupported_format(self):
        from app.core.loader import DocumentLoader
        loader = DocumentLoader()
        with pytest.raises(ValueError, match="不支持"):
            loader.load_file("test.xyz")

    def test_load_csv(self, tmp_path):
        from app.core.loader import DocumentLoader
        loader = DocumentLoader()
        test_file = tmp_path / "test.csv"
        test_file.write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-8")
        docs = loader.load_file(str(test_file))
        assert len(docs) == 2
        assert "Alice" in docs[0].page_content


class TestRAGEngine:
    """测试RAG引擎"""

    def test_rag_engine_init(self):
        from app.core.rag_engine import RAGEngine
        mock_llm = MagicMock()
        mock_embeddings = MagicMock()
        mock_vs = MagicMock()
        engine = RAGEngine(mock_llm, mock_embeddings, mock_vs)
        assert engine.search_type == "hybrid"
        assert engine.top_k == 4

    def test_rag_engine_search_only(self):
        from app.core.rag_engine import RAGEngine
        mock_llm = MagicMock()
        mock_embeddings = MagicMock()
        mock_vs = MagicMock()
        mock_vs.similarity_search.return_value = [Document(page_content="test")]
        engine = RAGEngine(mock_llm, mock_embeddings, mock_vs)
        results = engine.search_only("test query", k=3)
        assert len(results) == 1
        mock_vs.similarity_search.assert_called_once_with("test query", k=3)

    def test_prompt_modes(self):
        from app.core.rag_engine import RAGEngine
        mock_llm = MagicMock()
        mock_embeddings = MagicMock()
        mock_vs = MagicMock()
        engine = RAGEngine(mock_llm, mock_embeddings, mock_vs, prompt_mode="few_shot")
        assert engine.prompt_mode == "few_shot"
        engine2 = RAGEngine(mock_llm, mock_embeddings, mock_vs, prompt_mode="structured")
        assert engine2.prompt_mode == "structured"


class TestConfig:
    """测试配置管理"""

    def test_config_loads(self):
        from app.core.config import config
        assert config.llm.model == "gpt-3.5-turbo"
        assert config.vectorstore.top_k == 4
        assert config.retriever.search_type == "hybrid"

    def test_config_dataclass(self):
        from app.core.config import AppConfig, LLMConfig
        cfg = AppConfig()
        assert isinstance(cfg.llm, LLMConfig)
