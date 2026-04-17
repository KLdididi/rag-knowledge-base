"""
RAG 检索与生成模块
整合混合检索、Prompt工程、结构化输出、缓存和对话记忆
"""

import json
import hashlib
import time
from typing import List, Optional, Dict, Any, AsyncIterator
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.callbacks import AsyncCallbackHandler

from .vectorstore import VectorStore
from .prompts.rag_prompts import (
    RAG_SYSTEM_PROMPT, RAG_USER_PROMPT,
    RAG_FEW_SHOT_PROMPT, RAG_STRUCTURED_PROMPT,
)


class SimpleCache:
    """简单的响应缓存"""
    
    def __init__(self, ttl: int = 3600):
        self._cache: Dict[str, tuple] = {}  # key -> (result, timestamp)
        self.ttl = ttl
    
    def _make_key(self, question: str, session_id: str) -> str:
        return hashlib.md5(f"{session_id}:{question}".encode()).hexdigest()
    
    def get(self, question: str, session_id: str) -> Optional[Dict[str, Any]]:
        key = self._make_key(question, session_id)
        if key in self._cache:
            result, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl:
                return result
            else:
                del self._cache[key]
        return None
    
    def set(self, question: str, session_id: str, result: Dict[str, Any]):
        key = self._make_key(question, session_id)
        self._cache[key] = (result, time.time())
    
    def clear(self):
        self._cache.clear()


class StreamingCallbackHandler(AsyncCallbackHandler):
    """流式输出回调处理器"""

    def __init__(self):
        self.tokens = []

    async def on_llm_new_token(self, token: str, **kwargs):
        self.tokens.append(token)


class SimpleMemory:
    """简单的对话记忆实现"""
    
    def __init__(self, max_history: int = 10):
        self.messages: List[Dict[str, str]] = []
        self.max_history = max_history
    
    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})
        if len(self.messages) > self.max_history:
            self.messages.pop(0)
    
    def add_ai_message(self, content: str):
        self.messages.append({"role": "assistant", "content": content})
        if len(self.messages) > self.max_history:
            self.messages.pop(0)
    
    def get_history(self) -> List[Dict[str, str]]:
        return self.messages
    
    def clear(self):
        self.messages = []


class RAGEngine:
    """RAG 检索增强生成引擎 - 高端版"""

    def __init__(
        self,
        llm: BaseChatModel,
        embeddings: Embeddings,
        vectorstore: VectorStore,
        search_type: str = "hybrid",
        top_k: int = 4,
        prompt_mode: str = "standard",
        use_cache: bool = True,
        use_reranker: bool = False,
        rerank_top_n: int = 3,
    ):
        """
        search_type: "similarity" | "mmr" | "hybrid"
        prompt_mode: "standard" | "few_shot" | "structured"
        use_cache: 启用响应缓存
        use_reranker: 启用重排序
        rerank_top_n: 重排序后返回数量
        """
        self.llm = llm
        self.embeddings = embeddings
        self.vectorstore = vectorstore
        self.search_type = search_type
        self.top_k = top_k
        self.prompt_mode = prompt_mode
        self.use_cache = use_cache
        self.use_reranker = use_reranker
        self.rerank_top_n = rerank_top_n

        # 缓存
        self._cache = SimpleCache(ttl=3600) if use_cache else None
        
        # 对话记忆（按session_id隔离）
        self._memories: Dict[str, SimpleMemory] = {}

    def _rerank(self, query: str, docs: List[Document]) -> List[Document]:
        """简单的重排序 - 按与查询的相关性排序"""
        if not docs:
            return docs
        
        # 计算相关性分数（简单实现：词重叠）
        def calc_score(doc):
            query_words = set(query.lower().split())
            doc_words = set(doc.page_content.lower().split())
            return len(query_words & doc_words)
        
        # 排序
        scored_docs = [(doc, calc_score(doc)) for doc in docs]
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        return [doc for doc, score in scored_docs[:self.rerank_top_n]]

    def _get_prompt_template(self) -> str:
        """根据模式选择Prompt模板"""
        templates = {
            "standard": RAG_SYSTEM_PROMPT + "\n\n" + RAG_USER_PROMPT,
            "few_shot": RAG_FEW_SHOT_PROMPT,
            "structured": RAG_STRUCTURED_PROMPT,
        }
        return templates.get(self.prompt_mode, templates["standard"])

    def _retrieve(self, query: str) -> List[Document]:
        """执行检索"""
        if self.search_type == "hybrid":
            # 扩大检索范围用于重排序
            retrieve_k = self.rerank_top_n * 3 if self.use_reranker else self.top_k
            results = self.vectorstore.hybrid_search(
                query, vector_k=retrieve_k, bm25_k=retrieve_k, top_n=retrieve_k
            )
            return [doc for doc, score in results]
        elif self.search_type == "mmr":
            retrieve_k = self.rerank_top_n * 3 if self.use_reranker else self.top_k
            return self.vectorstore.mmr_search(query, k=retrieve_k)
        else:
            return self.vectorstore.similarity_search(query, k=self.top_k)

    def query(
        self, question: str, return_sources: bool = False,
        session_id: str = "default",
    ) -> Dict[str, Any]:
        """查询（支持多轮对话、缓存、重排序）"""
        
        # 检查缓存
        if self._cache:
            cached = self._cache.get(question, session_id)
            if cached:
                cached["from_cache"] = True
                return cached
        
        # 检索
        docs = self._retrieve(question)
        
        # 重排序
        if self.use_reranker:
            docs = self._rerank(question, docs)
        
        context = "\n\n---\n\n".join([doc.page_content for doc in docs])

        # 构建Prompt
        prompt_template = self._get_prompt_template()
        prompt = ChatPromptTemplate.from_template(prompt_template)

        # 获取对话记忆
        memory = self._get_memory(session_id)

        # 构建消息
        messages = []
        
        # 添加对话历史到上下文
        history = memory.get_history()
        if history:
            history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history])
            context_with_history = f"{context}\n\n对话历史:\n{history_text}"
        else:
            context_with_history = context

        system_msg = prompt.format(context=context_with_history, question=question)
        messages.append(SystemMessage(content=system_msg))
        messages.append(HumanMessage(content=question))

        # 调用LLM
        response = self.llm.invoke(messages)
        answer = response.content

        # 保存对话记录
        memory.add_user_message(question)
        memory.add_ai_message(answer)

        result = {
            "answer": answer,
            "question": question,
            "session_id": session_id,
            "from_cache": False,
        }

        if return_sources:
            result["sources"] = [
                {
                    "content": doc.page_content[:200],
                    "metadata": doc.metadata,
                }
                for doc in docs
            ]

        # 结构化模式：尝试解析JSON
        if self.prompt_mode == "structured":
            try:
                parsed = json.loads(answer)
                result["parsed"] = parsed
            except json.JSONDecodeError:
                result["parsed"] = None
        
        # 缓存结果
        if self._cache:
            self._cache.set(question, session_id, result)
        
        return result

    async def query_stream(
        self, question: str, session_id: str = "default",
    ) -> AsyncIterator[str]:
        """流式查询（支持重排序）"""
        docs = self._retrieve(question)
        
        # 重排序
        if self.use_reranker:
            docs = self._rerank(question, docs)
        
        context = "\n\n---\n\n".join([doc.page_content for doc in docs])
        prompt_template = self._get_prompt_template()
        prompt = ChatPromptTemplate.from_template(prompt_template)

        messages = [
            SystemMessage(content=prompt.format(context=context, question=question)),
            HumanMessage(content=question),
        ]

        # 流式调用
        async for chunk in self.llm.astream(messages):
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content

        # 保存对话记录
        memory = self._get_memory(session_id)
        memory.add_user_message(question)

    def search_only(self, query: str, k: Optional[int] = None) -> List[Document]:
        """仅检索不生成"""
        k = k or self.top_k
        return self.vectorstore.similarity_search(query, k=k)

    def _get_memory(self, session_id: str) -> SimpleMemory:
        """获取或创建session对应的对话记忆"""
        if session_id not in self._memories:
            self._memories[session_id] = SimpleMemory(max_history=10)
        return self._memories[session_id]

    def reset_memory(self, session_id: str = "default"):
        """重置指定session的对话记忆"""
        if session_id in self._memories:
            self._memories[session_id].clear()

    def reset_all_memories(self):
        """重置所有对话记忆"""
        for memory in self._memories.values():
            memory.clear()
        self._memories.clear()
