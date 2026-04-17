"""性能基准测试"""

import pytest
import time
import statistics
from unittest.mock import MagicMock
from langchain_core.documents import Document


class BenchmarkResults:
    """性能测试结果收集器"""
    def __init__(self, name: str):
        self.name = name
        self.times = []

    def add(self, elapsed_ms: float):
        self.times.append(elapsed_ms)

    def report(self) -> dict:
        if not self.times:
            return {"name": self.name, "error": "No data"}
        return {
            "name": self.name,
            "count": len(self.times),
            "min_ms": round(min(self.times), 2),
            "max_ms": round(max(self.times), 2),
            "avg_ms": round(statistics.mean(self.times), 2),
            "median_ms": round(statistics.median(self.times), 2),
            "stdev_ms": round(statistics.stdev(self.times), 2) if len(self.times) > 1 else 0,
        }


class TestVectorStorePerformance:
    """向量存储性能基准测试"""

    @pytest.fixture
    def mock_embeddings(self):
        embeddings = MagicMock()
        embeddings.embed_query.return_value = [0.1] * 384
        embeddings.embed_documents.return_value = [[0.1] * 384] * 100
        return embeddings

    def test_benchmark_similarity_search_small(self, mock_embeddings, tmp_path):
        """基准：100文档 相似性检索（50次）"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "perf_sim")
        vs = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        docs = [
            Document(page_content=f"文档{i}内容", metadata={"index": i})
            for i in range(100)
        ]
        vs.create_from_documents(docs)

        bench = BenchmarkResults("similarity_search_100docs_50runs")
        for _ in range(50):
            start = time.perf_counter()
            vs.similarity_search("Python 机器学习", k=5)
            elapsed = (time.perf_counter() - start) * 1000
            bench.add(elapsed)

        result = bench.report()
        print(f"\n{'='*60}")
        print(f"  {result['name']}")
        print(f"  文档数量: 100    检索次数: {result['count']}")
        print(f"  最小延迟: {result['min_ms']} ms")
        print(f"  平均延迟: {result['avg_ms']} ms")
        print(f"  中位延迟: {result['median_ms']} ms")
        print(f"  最大延迟: {result['max_ms']} ms")
        print(f"  标准差:   {result['stdev_ms']} ms")
        print(f"{'='*60}")
        # 性能要求：平均延迟 < 500ms（Mock Embedding）
        assert result["avg_ms"] < 500

    def test_benchmark_bm25_search(self, mock_embeddings, tmp_path):
        """基准：BM25 关键词检索性能"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "perf_bm25")
        vs = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        docs = [
            Document(page_content=f"关键词 内容 文档{i}", metadata={"index": i})
            for i in range(100)
        ]
        vs.create_from_documents(docs)

        bench = BenchmarkResults("bm25_search_100docs_20runs")
        for _ in range(20):
            start = time.perf_counter()
            # 通过 hybrid_search 测试 BM25（RRF融合中包含BM25）
            vs.hybrid_search("关键词", top_n=5)
            elapsed = (time.perf_counter() - start) * 1000
            bench.add(elapsed)

        result = bench.report()
        print(f"\n  BM25 检索 (via hybrid): avg={result['avg_ms']}ms")
        assert result["avg_ms"] < 200

    def test_benchmark_mmr_search(self, mock_embeddings, tmp_path):
        """基准：MMR 多样性检索"""
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "perf_mmr")
        vs = VectorStore(embeddings=mock_embeddings, persist_directory=persist_dir)
        docs = [
            Document(page_content=f"文档{i}内容包含Python和机器学习", metadata={"index": i})
            for i in range(50)
        ]
        vs.create_from_documents(docs)

        bench = BenchmarkResults("mmr_search_50docs_30runs")
        for _ in range(30):
            start = time.perf_counter()
            vs.mmr_search("Python 编程", k=5, fetch_k=10)
            elapsed = (time.perf_counter() - start) * 1000
            bench.add(elapsed)

        result = bench.report()
        print(f"\n  MMR 检索: avg={result['avg_ms']}ms")
        assert result["avg_ms"] < 200


class TestRAGEnginePerformance:
    """RAG 引擎性能基准测试"""

    @pytest.fixture
    def mock_llm_fast(self):
        """模拟快速 LLM"""
        llm = MagicMock()
        response = MagicMock()
        response.content = "这是测试回答内容。"
        llm.invoke.return_value = response
        return llm

    @pytest.fixture
    def mock_embeddings_fast(self):
        embeddings = MagicMock()
        embeddings.embed_query.return_value = [0.1] * 384
        embeddings.embed_documents.return_value = [[0.1] * 384] * 10
        return embeddings

    @pytest.fixture
    def mock_vs(self, mock_embeddings_fast, tmp_path):
        from app.core.vectorstore import VectorStore
        persist_dir = str(tmp_path / "perf_rag")
        vs = VectorStore(embeddings=mock_embeddings_fast, persist_directory=persist_dir)
        docs = [
            Document(page_content=f"相关文档{i}内容", metadata={"index": i})
            for i in range(10)
        ]
        vs.create_from_documents(docs)
        return vs

    def test_benchmark_rag_query_latency(self, mock_llm_fast, mock_embeddings_fast, mock_vs):
        """基准：RAG 查询端到端延迟（50次，无缓存）"""
        from app.core.rag_engine import RAGEngine
        
        engine = RAGEngine(
            llm=mock_llm_fast,
            embeddings=mock_embeddings_fast,
            vectorstore=mock_vs,
            use_cache=False,
            use_reranker=False,
        )

        bench = BenchmarkResults("rag_query_10docs_50runs")
        for i in range(50):
            start = time.perf_counter()
            engine.query(f"RAG 测试问题 {i}", return_sources=True)
            elapsed = (time.perf_counter() - start) * 1000
            bench.add(elapsed)

        result = bench.report()
        print(f"\n{'='*60}")
        print(f"  RAG 查询性能 (无缓存)")
        print(f"  平均延迟: {result['avg_ms']} ms")
        print(f"  中位延迟: {result['median_ms']} ms")
        print(f"  最大延迟: {result['max_ms']} ms")
        print(f"{'='*60}")
        assert result["avg_ms"] < 200

    def test_benchmark_cache_hit_performance(self, mock_llm_fast, mock_embeddings_fast, mock_vs):
        """基准：缓存命中性能"""
        from app.core.rag_engine import RAGEngine
        
        engine = RAGEngine(
            llm=mock_llm_fast,
            embeddings=mock_embeddings_fast,
            vectorstore=mock_vs,
            use_cache=True,
        )

        question = "缓存性能测试问题"
        # 第一次（cache miss）
        start1 = time.perf_counter()
        engine.query(question)
        elapsed1 = (time.perf_counter() - start1) * 1000

        # 第二次（cache hit）
        start2 = time.perf_counter()
        result2 = engine.query(question)
        elapsed2 = (time.perf_counter() - start2) * 1000

        print(f"\n{'='*60}")
        print(f"  缓存性能测试")
        print(f"  首次查询 (miss): {elapsed1:.2f} ms")
        print(f"  二次查询 (hit): {elapsed2:.2f} ms")
        print(f"  缓存命中: {result2.get('from_cache', False)}")
        print(f"{'='*60}")

        assert result2.get("from_cache") == True
        # 缓存命中应远快于首次
        assert elapsed2 < elapsed1 / 5

    def test_benchmark_multi_session_memory(self, mock_llm_fast, mock_embeddings_fast, mock_vs):
        """基准：多会话记忆创建"""
        from app.core.rag_engine import RAGEngine
        
        engine = RAGEngine(
            llm=mock_llm_fast,
            embeddings=mock_embeddings_fast,
            vectorstore=mock_vs,
        )

        bench = BenchmarkResults("multi_session_100sessions")
        for i in range(100):
            session_id = f"session_{i}"
            start = time.perf_counter()
            engine.query(f"会话{i}测试问题", session_id=session_id)
            elapsed = (time.perf_counter() - start) * 1000
            bench.add(elapsed)

        result = bench.report()
        print(f"\n  多会话创建: avg={result['avg_ms']}ms")
        assert result["avg_ms"] < 100


class TestEmbeddingsPerformance:
    """Embedding 模型性能测试"""

    def test_benchmark_mock_embedding_speed(self):
        """基准：Mock Embedding 速度"""
        embeddings = MagicMock()
        embeddings.embed_query.return_value = [0.1] * 384

        bench = BenchmarkResults("mock_embed_query_1000runs")
        for _ in range(1000):
            start = time.perf_counter()
            embeddings.embed_query("测试查询文本内容")
            elapsed = (time.perf_counter() - start) * 1000
            bench.add(elapsed)

        result = bench.report()
        print(f"\n  Mock embed_query: avg={result['avg_ms']}ms (1000次)")
        # Mock 应极快
        assert result["avg_ms"] < 0.1


class TestConcurrentPerformance:
    """并发性能测试"""

    def test_benchmark_sequential_queries(self):
        """顺序查询基准"""
        from app.core.rag_engine import RAGEngine
        
        mock_llm = MagicMock()
        response = MagicMock()
        response.content = "测试回答"
        mock_llm.invoke.return_value = response

        mock_vs = MagicMock()
        mock_vs.hybrid_search.return_value = [
            (Document(page_content="文档", metadata={}), 0.9)
        ]

        engine = RAGEngine(
            llm=mock_llm,
            embeddings=MagicMock(),
            vectorstore=mock_vs,
            use_cache=False,
        )

        start = time.perf_counter()
        for i in range(50):
            engine.query(f"顺序查询 {i}")
        total_ms = (time.perf_counter() - start) * 1000

        qps = 50 / (total_ms / 1000)
        print(f"\n{'='*60}")
        print(f"  顺序查询 50 次")
        print(f"  总耗时: {total_ms:.2f} ms")
        print(f"  平均: {total_ms/50:.2f} ms/query")
        print(f"  QPS: {qps:.1f}")
        print(f"{'='*60}")
        
        # 至少 10 QPS
        assert qps > 10
