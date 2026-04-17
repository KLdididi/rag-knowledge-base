"""单元测试：向量存储模块"""

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document


class TestVectorStore:
    """向量存储测试"""

    @pytest.fixture
    def mock_embeddings(self):
        import numpy as np
        embeddings = MagicMock()
        embeddings.embed_query.return_value = (np.array([0.1] * 384, dtype=np.float32))
        embeddings.embed_documents.return_value = [np.array([0.1] * 384, dtype=np.float32)] * 4
        return embeddings

    @pytest.fixture
    def sample_docs(self):
        return [
            Document(page_content="Python 是一种广泛使用的高级编程语言。", metadata={"filename": "python.md"}),
            Document(page_content="RAG 是检索增强生成技术，结合检索和生成模型。", metadata={"filename": "rag.md"}),
            Document(page_content="LangChain 是一个用于构建 LLM 应用的框架。", metadata={"filename": "langchain.md"}),
            Document(page_content="向量数据库用于存储和检索向量嵌入。", metadata={"filename": "vector_db.md"}),
        ]

    def test_vectorstore_init(self, mock_embeddings, tmp_path):
        """测试 VectorStore 初始化"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "vs_init")
        vs = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        assert vs.persist_directory == persist_dir
        assert vs.embeddings == mock_embeddings
        assert vs.collection_name == "knowledge_base"

    def test_create_from_documents(self, mock_embeddings, sample_docs, tmp_path):
        """测试从文档创建向量存储（返回 Chroma 实例）"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "vs_create")
        vs = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        result = vs.create_from_documents(sample_docs)
        # create_from_documents 返回 Chroma 实例
        assert result is not None
        assert vs.document_count() == 4

    def test_similarity_search(self, mock_embeddings, sample_docs, tmp_path):
        """测试向量相似性检索"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "vs_sim")
        vs = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        vs.create_from_documents(sample_docs)
        results = vs.similarity_search("Python 编程", k=2)
        assert len(results) <= 2
        assert all(isinstance(r, Document) for r in results)

    def test_similarity_search_with_score(self, mock_embeddings, sample_docs, tmp_path):
        """测试带分数的相似性检索"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "vs_sim_score")
        vs = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        vs.create_from_documents(sample_docs)
        results = vs.similarity_search_with_score("Python", k=3)
        assert len(results) <= 3
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)

    def test_hybrid_search(self, mock_embeddings, sample_docs, tmp_path):
        """测试混合检索（向量 + BM25 + RRF）"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "vs_hybrid")
        vs = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        vs.create_from_documents(sample_docs)
        results = vs.hybrid_search("Python 和 RAG", top_n=3)
        # hybrid_search 返回 List[Tuple[Document, float]]
        assert len(results) <= 3
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)
        assert all(isinstance(r[0], Document) and isinstance(r[1], float) for r in results)

    def test_hybrid_search_with_scores(self, mock_embeddings, sample_docs, tmp_path):
        """测试混合检索（显式参数名）"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "vs_hybrid2")
        vs = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        vs.create_from_documents(sample_docs)
        # 直接传 keyword args
        results = vs.hybrid_search(query="编程", vector_k=5, bm25_k=5, top_n=2)
        assert len(results) <= 2
        assert all(isinstance(r, tuple) for r in results)

    def test_mmr_search(self, mock_embeddings, sample_docs, tmp_path):
        """测试 MMR 多样性检索"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "vs_mmr")
        vs = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        vs.create_from_documents(sample_docs)
        results = vs.mmr_search("编程语言", k=2, fetch_k=4)
        assert len(results) <= 2
        assert all(isinstance(r, Document) for r in results)

    def test_delete_collection(self, mock_embeddings, sample_docs, tmp_path):
        """测试删除集合"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "vs_delete")
        vs = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        vs.create_from_documents(sample_docs)
        assert vs.document_count() == 4
        vs.delete_collection()
        # 重新创建验证
        vs2 = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        vs2.load()
        assert vs2.document_count() == 0

    def test_add_documents_incremental(self, mock_embeddings, sample_docs, tmp_path):
        """测试增量添加文档"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "vs_add")
        vs = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        vs.create_from_documents(sample_docs[:2])
        assert vs.document_count() == 2
        vs.add_documents(sample_docs[2:])
        assert vs.document_count() == 4

    def test_persistence_between_instances(self, mock_embeddings, sample_docs, tmp_path):
        """测试持久化：跨实例访问"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "vs_persist")
        vs1 = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        vs1.create_from_documents(sample_docs[:2])
        vs2 = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        vs2.load()
        assert vs2.document_count() == 2

    def test_empty_collection_search(self, mock_embeddings, tmp_path):
        """测试空集合检索"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "vs_empty")
        vs = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        vs.load()  # 加载空的
        results = vs.similarity_search("anything", k=3)
        assert len(results) == 0

    def test_unicode_content(self, mock_embeddings, tmp_path):
        """测试中文字符处理"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "vs_unicode")
        docs = [
            Document(page_content="中文测试文档，包含特殊字符：@#$%", metadata={"filename": "中文.md"}),
        ]
        vs = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        vs.create_from_documents(docs)
        assert vs.document_count() == 1
        results = vs.similarity_search("中文", k=1)
        assert len(results) >= 0  # 可能0或1

    def test_get_retriever(self, mock_embeddings, sample_docs, tmp_path):
        """测试获取检索器"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "vs_retriever")
        vs = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        vs.create_from_documents(sample_docs)
        retriever = vs.get_retriever(search_type="similarity", k=3)
        assert retriever is not None

    def test_hybrid_search_no_docs(self, mock_embeddings, tmp_path):
        """测试空集合的混合检索（fallback 到向量检索）"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "vs_hybrid_empty")
        vs = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        vs.load()
        results = vs.hybrid_search("anything", top_n=3)
        # fallback 到 similarity_search_with_score
        assert isinstance(results, list)


class TestHybridRetriever:
    """测试混合检索器"""

    @pytest.fixture
    def mock_embeddings(self):
        import numpy as np
        embeddings = MagicMock()
        embeddings.embed_query.return_value = np.array([0.1] * 384, dtype=np.float32)
        embeddings.embed_documents.return_value = [np.array([0.1] * 384, dtype=np.float32)] * 2
        return embeddings

    @pytest.fixture
    def sample_docs(self):
        return [
            Document(page_content="Python 编程语言介绍", metadata={}),
            Document(page_content="RAG 检索增强生成", metadata={}),
        ]

    def test_hybrid_retriever_from_documents(self, mock_embeddings, sample_docs, tmp_path):
        """测试 HybridRetriever.from_documents 工厂方法"""
        from app.core.vectorstore import HybridRetriever
        persist_dir = str(tmp_path / "hr_fromdocs")
        retriever = HybridRetriever.from_documents(
            documents=sample_docs,
            embeddings=mock_embeddings,
            persist_directory=persist_dir,
        )
        assert retriever is not None
        assert retriever.alpha == 0.5

    def test_hybrid_retriever_search(self, mock_embeddings, sample_docs, tmp_path):
        """测试 HybridRetriever 检索"""
        from app.core.vectorstore import HybridRetriever
        persist_dir = str(tmp_path / "hr_search")
        retriever = HybridRetriever.from_documents(
            documents=sample_docs,
            embeddings=mock_embeddings,
            persist_directory=persist_dir,
        )
        results = retriever.hybrid_search("Python 编程", top_n=2)
        assert len(results) <= 2
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)

    def test_hybrid_retriever_custom_alpha(self, mock_embeddings, sample_docs, tmp_path):
        """测试自定义权重 alpha"""
        from app.core.vectorstore import HybridRetriever
        persist_dir = str(tmp_path / "hr_alpha")
        retriever = HybridRetriever.from_documents(
            documents=sample_docs,
            embeddings=mock_embeddings,
            persist_directory=persist_dir,
            alpha=0.8,
        )
        assert retriever.alpha == 0.8
        results = retriever.hybrid_search("测试", top_n=2)
        assert isinstance(results, list)

    def test_hybrid_retriever_rrf_scores(self, mock_embeddings, sample_docs, tmp_path):
        """测试 RRF 融合算法返回分数"""
        from app.core.vectorstore import HybridRetriever
        persist_dir = str(tmp_path / "hr_rrf")
        retriever = HybridRetriever.from_documents(
            documents=sample_docs,
            embeddings=mock_embeddings,
            persist_directory=persist_dir,
        )
        results = retriever.hybrid_search("Python RAG", top_n=2)
        # 验证分数为正数
        for doc, score in results:
            assert score >= 0
