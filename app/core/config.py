"""统一配置管理模块"""

import os
from dataclasses import dataclass, field
from typing import Optional, Literal
from dotenv import load_dotenv

load_dotenv()


# LLM 提供商类型
LLMProvider = Literal["openai", "ollama"]


@dataclass
class LLMConfig:
    """大模型配置"""
    provider: LLMProvider = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "ollama"))
    api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    api_base: str = field(default_factory=lambda: os.getenv("OPENAI_API_BASE", None))
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "llama3"))
    temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.7")))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "2000")))


@dataclass
class EmbeddingConfig:
    """Embedding 模型配置"""
    model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002"))
    api_base: str = field(default_factory=lambda: os.getenv("OPENAI_API_BASE", None))


@dataclass
class VectorStoreConfig:
    """向量数据库配置"""
    persist_directory: str = field(default_factory=lambda: os.getenv("CHROMA_PERSIST_DIR", "./chroma_db"))
    collection_name: str = field(default_factory=lambda: os.getenv("CHROMA_COLLECTION", "knowledge_base"))
    top_k: int = field(default_factory=lambda: int(os.getenv("DEFAULT_TOP_K", "4")))


@dataclass
class RetrieverConfig:
    """检索器配置"""
    search_type: str = field(default_factory=lambda: os.getenv("SEARCH_TYPE", "hybrid"))
    vector_k: int = field(default_factory=lambda: int(os.getenv("VECTOR_K", "5")))
    bm25_k: int = field(default_factory=lambda: int(os.getenv("BM25_K", "5")))
    rerank_top_n: int = field(default_factory=lambda: int(os.getenv("RERANK_TOP_N", "3")))
    use_reranker: bool = field(default_factory=lambda: os.getenv("USE_RERANKER", "false").lower() == "true")
    use_cache: bool = field(default_factory=lambda: os.getenv("USE_CACHE", "false").lower() == "true")
    cache_ttl: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL", "3600")))


@dataclass
class ServerConfig:
    """服务配置"""
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    reload: bool = field(default_factory=lambda: os.getenv("RELOAD", "true").lower() == "true")
    upload_dir: str = field(default_factory=lambda: os.getenv("UPLOAD_DIR", "./data"))


@dataclass
class AppConfig:
    """全局配置"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    vectorstore: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    retriever: RetrieverConfig = field(default_factory=RetrieverConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls()


# 全局配置单例
config = AppConfig.from_env()
