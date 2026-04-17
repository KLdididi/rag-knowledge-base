"""
向量存储与检索模块
支持 Chroma 向量数据库，向量检索 + BM25 混合检索 + Reranker
"""

import os
from typing import List, Optional, Tuple
from rank_bm25 import BM25Okapi

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma


class HybridRetriever:
    """混合检索器：向量检索 + BM25 关键词检索"""

    def __init__(
        self,
        vectorstore: Chroma,
        bm25_index: Optional[BM25Okapi] = None,
        bm25_docs: Optional[List[Document]] = None,
        alpha: float = 0.5,
    ):
        """
        alpha: 向量检索权重 (0~1), 1-alpha 为BM25权重
        """
        self.vectorstore = vectorstore
        self.bm25_index = bm25_index
        self.bm25_docs = bm25_docs or []
        self.alpha = alpha

    @classmethod
    def from_documents(
        cls, documents: List[Document], embeddings: Embeddings,
        persist_directory: str = "./chroma_db",
        collection_name: str = "knowledge_base",
        alpha: float = 0.5,
    ) -> "HybridRetriever":
        """从文档列表构建混合检索器"""
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=persist_directory,
            collection_name=collection_name,
        )

        # 构建 BM25 索引
        tokenized_docs = [doc.page_content.split() for doc in documents]
        bm25_index = BM25Okapi(tokenized_docs)

        return cls(
            vectorstore=vectorstore,
            bm25_index=bm25_index,
            bm25_docs=documents,
            alpha=alpha,
        )

    def hybrid_search(
        self, query: str, vector_k: int = 5, bm25_k: int = 5, top_n: int = 3
    ) -> List[Tuple[Document, float]]:
        """
        混合检索：向量 + BM25，按 RRF (Reciprocal Rank Fusion) 合并排序

        RRF 公式: score(d) = sum(1 / (k + rank_i(d)))，k=60
        """
        k = 60  # RRF 常数

        # 1. 向量检索
        vector_results = self.vectorstore.similarity_search_with_score(query, k=vector_k)
        vector_ranks = {id(doc.page_content): rank for rank, (doc, _) in enumerate(vector_results)}

        # 2. BM25 检索
        tokenized_query = query.split()
        bm25_scores = self.bm25_index.get_scores(tokenized_query)
        bm25_ranked = sorted(
            zip(range(len(bm25_scores)), bm25_scores),
            key=lambda x: x[1], reverse=True
        )[:bm25_k]
        bm25_ranks = {idx: rank for rank, (idx, _) in enumerate(bm25_ranked)}

        # 3. RRF 融合
        rrf_scores = {}
        seen_docs = {}

        for rank, (doc, score) in enumerate(vector_results):
            doc_id = doc.page_content
            rrf_scores[doc_id] = self.alpha / (k + rank + 1)
            seen_docs[doc_id] = doc

        for rank, (idx, score) in enumerate(bm25_ranked):
            if idx < len(self.bm25_docs):
                doc = self.bm25_docs[idx]
                doc_id = doc.page_content
                rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + (1 - self.alpha) / (k + rank + 1)
                seen_docs[doc_id] = doc

        # 4. 排序取 Top-N
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return [(seen_docs[doc_id], score) for doc_id, score in sorted_results]


class VectorStore:
    """向量数据库管理器"""

    def __init__(
        self,
        embeddings: Embeddings,
        persist_directory: str = "./chroma_db",
        collection_name: str = "knowledge_base",
    ):
        self.embeddings = embeddings
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self._vectorstore: Optional[Chroma] = None
        self._all_docs: List[Document] = []  # 缓存所有文档用于BM25
        self._hybrid_retriever: Optional[HybridRetriever] = None

    def create_from_documents(self, documents: List[Document]) -> Chroma:
        """从文档列表创建向量数据库"""
        self._all_docs = documents
        self._vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=self.persist_directory,
            collection_name=self.collection_name,
        )
        self._build_hybrid_index(documents)
        return self._vectorstore

    def _build_hybrid_index(self, documents: List[Document]):
        """构建混合检索索引"""
        tokenized_docs = [doc.page_content.split() for doc in documents]
        bm25_index = BM25Okapi(tokenized_docs)
        self._hybrid_retriever = HybridRetriever(
            vectorstore=self._vectorstore,
            bm25_index=bm25_index,
            bm25_docs=documents,
        )

    def load(self) -> Chroma:
        """加载已存在的向量数据库"""
        self._vectorstore = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_name=self.collection_name,
        )
        # 加载所有文档用于BM25
        all_data = self._vectorstore._collection.get()
        if all_data and all_data.get("documents"):
            self._all_docs = [
                Document(page_content=text, metadata=meta)
                for text, meta in zip(all_data["documents"], all_data["metadatas"])
            ]
            self._build_hybrid_index(self._all_docs)
        return self._vectorstore

    def get_retriever(self, search_type: str = "similarity", k: int = 4, **kwargs):
        """获取检索器"""
        if self._vectorstore is None:
            self.load()
        return self._vectorstore.as_retriever(
            search_type=search_type,
            search_kwargs={"k": k, **kwargs},
        )

    def hybrid_search(
        self, query: str, vector_k: int = 5, bm25_k: int = 5, top_n: int = 3
    ) -> List[Tuple[Document, float]]:
        """混合检索（向量 + BM25 + RRF 融合）"""
        if self._hybrid_retriever is None:
            self.load()
        if self._hybrid_retriever is None:
            # fallback到纯向量检索
            results = self.similarity_search_with_score(query, k=top_n)
            return results
        return self._hybrid_retriever.hybrid_search(query, vector_k, bm25_k, top_n)

    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """相似度搜索"""
        if self._vectorstore is None:
            self.load()
        return self._vectorstore.similarity_search(query, k=k)

    def similarity_search_with_score(
        self, query: str, k: int = 4
    ) -> List[Tuple[Document, float]]:
        """带分数的相似度搜索"""
        if self._vectorstore is None:
            self.load()
        return self._vectorstore.similarity_search_with_score(query, k=k)

    def mmr_search(self, query: str, k: int = 3, fetch_k: int = 10) -> List[Document]:
        """MMR 多样性搜索"""
        if self._vectorstore is None:
            self.load()
        return self._vectorstore.max_marginal_relevance_search(
            query, k=k, fetch_k=fetch_k
        )

    def add_documents(self, documents: List[Document]) -> List[str]:
        """增量添加文档"""
        if self._vectorstore is None:
            self.load()
        ids = self._vectorstore.add_documents(documents)
        self._all_docs.extend(documents)
        # 重建BM25索引
        self._build_hybrid_index(self._all_docs)
        return ids

    def delete_collection(self):
        """删除集合"""
        if self._vectorstore is not None:
            self._vectorstore.delete_collection()
            self._vectorstore = None
        self._all_docs = []
        self._hybrid_retriever = None

    def document_count(self) -> int:
        """获取文档数量"""
        if self._vectorstore is None:
            self.load()
        return self._vectorstore._collection.count()
