"""
FastAPI 服务层
支持：RAG查询、Agent工作流、SSE流式输出、对话记忆、文档管理
"""

import os
import json
import time
import uuid
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field

from app.core.config import config
from app.core.loader import DocumentLoader
from app.core.splitter import TextSplitter
from app.core.vectorstore import VectorStore
from app.core.rag_engine import RAGEngine
from app.agents.workflow import build_graph, GraphWorkflow
from app.interview.api import router as interview_router
from app.core.monitoring import (
    get_logger, metrics, tracer, health_checker,
    HealthStatus, HealthCheckResult
)

from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_ollama import ChatOllama, OllamaEmbeddings

# 监控日志器
monitoring_logger = get_logger("rag-api")


# ============ 全局实例 ============

_llm = None
_embeddings = None
_vectorstore = None
_rag_engine = None
_graph_workflow = None
_document_loader = None
_text_splitter = None


def get_llm():
    global _llm
    if _llm is None:
        provider = config.llm.provider
        
        if provider == "ollama":
            # Ollama 本地模型
            _llm = ChatOllama(
                model=config.llm.model,
                temperature=config.llm.temperature,
                max_tokens=config.llm.max_tokens,
            )
        else:
            # OpenAI API
            kwargs = {
                "model": config.llm.model,
                "temperature": config.llm.temperature,
                "max_tokens": config.llm.max_tokens,
            }
            if config.llm.api_base:
                kwargs["openai_api_base"] = config.llm.api_base
            if config.llm.api_key:
                kwargs["openai_api_key"] = config.llm.api_key
            _llm = ChatOpenAI(**kwargs)
    return _llm


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        provider = config.llm.provider
        
        if provider == "ollama":
            # Ollama Embeddings
            _embeddings = OllamaEmbeddings(
                model=config.embedding.model,
            )
        else:
            # OpenAI Embeddings
            kwargs = {"model": config.embedding.model}
            if config.embedding.api_base:
                kwargs["openai_api_base"] = config.embedding.api_base
            if config.llm.api_key:
                kwargs["openai_api_key"] = config.llm.api_key
            _embeddings = OpenAIEmbeddings(**kwargs)
    return _embeddings


def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = VectorStore(
            embeddings=get_embeddings(),
            persist_directory=config.vectorstore.persist_directory,
            collection_name=config.vectorstore.collection_name,
        )
    return _vectorstore


def get_rag_engine():
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine(
            llm=get_llm(),
            embeddings=get_embeddings(),
            vectorstore=get_vectorstore(),
            search_type=config.retriever.search_type,
            top_k=config.vectorstore.top_k,
            use_cache=config.retriever.use_cache,
            use_reranker=config.retriever.use_reranker,
            rerank_top_n=config.retriever.rerank_top_n,
        )
    return _rag_engine


def get_graph_workflow():
    global _graph_workflow
    if _graph_workflow is None:
        compiled = build_graph(
            llm=get_llm(),
            rag_engine=get_rag_engine(),
            vectorstore=get_vectorstore(),
            document_loader=DocumentLoader(),
            text_splitter=TextSplitter(),
        )
        _graph_workflow = GraphWorkflow(
            compiled_graph=compiled,
            rag_engine=get_rag_engine(),
        )
    return _graph_workflow


def get_document_loader():
    global _document_loader
    if _document_loader is None:
        _document_loader = DocumentLoader()
    return _document_loader


def get_text_splitter():
    global _text_splitter
    if _text_splitter is None:
        _text_splitter = TextSplitter()
    return _text_splitter


# ============ lifespan ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        vs = get_vectorstore()
        count = vs.document_count()
        print(f"[Startup] 向量数据库已加载，共 {count} 个文档块")
    except Exception as e:
        print(f"[Startup] 向量数据库加载失败（首次启动正常）: {e}")
    yield
    global _llm, _embeddings, _vectorstore, _rag_engine, _graph_workflow
    _llm = _embeddings = _vectorstore = _rag_engine = _graph_workflow = None


# ============ FastAPI App ============

app = FastAPI(
    title="RAG Knowledge Base API",
    description="""
    智能知识库问答系统 API

    ## 核心功能
    - **RAG检索增强生成**: 基于向量+BM25混合检索的问答
    - **LangGraph工作流**: 状态图驱动的多Agent协作
    - **流式输出**: SSE (Server-Sent Events) 实时流式响应
    - **对话记忆**: 多轮对话上下文管理
    - **文档管理**: 多格式文档上传与索引
    """,
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 面试功能路由
app.include_router(interview_router)


# ============ 监控中间件 ============

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """请求指标中间件"""
    trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4())[:8])
    request.state.trace_id = trace_id
    start_time = time.perf_counter()
    
    method = request.method
    path = request.url.path
    
    # 跳过指标端点自身的监控
    skip_metrics = path in ["/metrics", "/health/detailed", "/traces"]
    
    response = await call_next(request)
    
    duration_ms = (time.perf_counter() - start_time) * 1000
    
    if not skip_metrics:
        metrics.record_request(method, path, response.status_code, duration_ms)
        monitoring_logger.info(
            "HTTP request",
            method=method,
            path=path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
            trace_id=trace_id,
        )
    
    response.headers["X-Trace-ID"] = trace_id
    response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
    return response


# ============ 请求/响应模型 ============

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="用户查询")
    top_k: int = Field(default=4, ge=1, le=20, description="检索文档数量")
    return_sources: bool = Field(default=False, description="是否返回来源")
    search_type: str = Field(default="hybrid", description="检索类型: similarity/mmr/hybrid")
    prompt_mode: str = Field(default="standard", description="Prompt模式: standard/few_shot/structured")

class StreamRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="用户查询")
    session_id: str = Field(default="default", description="会话ID")

class GraphRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="用户查询")
    session_id: str = Field(default="default", description="会话ID")
    search_type: str = Field(default="hybrid", description="检索类型")

class QueryResponse(BaseModel):
    answer: str
    question: str
    sources: Optional[List[dict]] = None
    session_id: str = "default"

class GraphResponse(BaseModel):
    answer: str
    confidence: Optional[str] = None
    sources: Optional[List[dict]] = None
    intent: Optional[str] = None
    trace: Optional[List[str]] = None
    error: Optional[str] = None

class AgentResponse(BaseModel):
    answer: str
    agent_type: str
    sources: Optional[List[str]] = None

class DocumentInfo(BaseModel):
    filename: str
    chunks: int
    message: str

class HealthResponse(BaseModel):
    status: str
    version: str
    document_count: int
    supported_formats: List[str]


# ============ API 路由 ============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    try:
        vs = get_vectorstore()
        count = vs.document_count()
    except Exception:
        count = 0
    return HealthResponse(
        status="ok",
        version="2.0.0",
        document_count=count,
        supported_formats=list(DocumentLoader.SUPPORTED_EXTENSIONS),
    )


@app.get("/health/detailed")
async def health_detailed():
    """详细健康检查（包含各组件状态）"""
    result = health_checker.check_all()
    status_code = 200 if result["status"] == "healthy" else 503 if result["status"] == "unhealthy" else 200
    return JSONResponse(content=result, status_code=status_code)


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus 指标端点"""
    from fastapi.responses import PlainTextResponse
    content = metrics.export_prometheus()
    return PlainTextResponse(content=content, media_type="text/plain")


@app.get("/traces")
async def recent_traces(limit: int = Query(default=10, ge=1, le=100)):
    """最近追踪记录"""
    traces = tracer.get_recent_traces(limit=limit)
    return {
        "count": len(traces),
        "traces": traces,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@app.get("/stats")
async def application_stats():
    """应用统计摘要"""
    return {
        "version": "2.0.0",
        "metrics": metrics.get_summary(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@app.post("/api/query", response_model=QueryResponse)
async def query_knowledge_base(body: QueryRequest, http_request: Request):
    """RAG知识库查询（支持多轮对话）"""
    start = time.perf_counter()
    trace_id = getattr(http_request.state, "trace_id", "unknown")
    try:
        engine = get_rag_engine()
        engine.search_type = body.search_type
        engine.prompt_mode = body.prompt_mode
        engine.top_k = body.top_k
        result = engine.query(
            body.query,
            return_sources=body.return_sources,
        )
        duration_ms = (time.perf_counter() - start) * 1000
        metrics.record_retrieval(
            body.query, 
            len(result.get("sources", [])), 
            duration_ms, 
            body.search_type
        )
        monitoring_logger.info(
            "RAG query completed",
            query=body.query[:50],
            sources=len(result.get("sources", [])),
            duration_ms=round(duration_ms, 2),
            search_type=body.search_type,
            trace_id=trace_id,
        )
        return QueryResponse(**result)
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        monitoring_logger.error(
            "RAG query failed",
            query=body.query[:50],
            error=str(e),
            duration_ms=round(duration_ms, 2),
            trace_id=trace_id,
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query/stream")
async def query_stream(request: StreamRequest):
    """RAG知识库流式查询（SSE）"""
    engine = get_rag_engine()

    async def event_generator():
        try:
            async for token in engine.query_stream(
                request.query,
                session_id=request.session_id,
            ):
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/graph", response_model=GraphResponse)
async def graph_query(request: GraphRequest):
    """LangGraph状态图工作流查询"""
    try:
        workflow = get_graph_workflow()
        result = workflow.run(
            query=request.query,
            session_id=request.session_id,
            search_type=request.search_type,
        )
        return GraphResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent", response_model=AgentResponse)
async def agent_query(request: QueryRequest):
    """Agent智能问答（LangGraph路由）"""
    try:
        workflow = get_graph_workflow()
        result = workflow.run(request.query, search_type=request.search_type)
        return AgentResponse(
            answer=result.get("answer", ""),
            agent_type="langgraph",
            sources=[s.get("source", "") for s in result.get("sources", [])],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/documents/upload", response_model=DocumentInfo)
async def upload_document(file: UploadFile = File(...)):
    """上传并索引文档"""
    import tempfile

    allowed_types = DocumentLoader.SUPPORTED_EXTENSIONS
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}，支持: {list(allowed_types)}"
        )

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        loader = get_document_loader()
        docs = loader.load_file(tmp_path)
        splitter = get_text_splitter()
        chunks = splitter.split_and_preserve_metadata(docs)
        vs = get_vectorstore()
        vs.add_documents(chunks)

        os.unlink(tmp_path)

        return DocumentInfo(
            filename=file.filename,
            chunks=len(chunks),
            message=f"成功索引 {len(chunks)} 个文本块",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档处理失败: {e}")


@app.get("/api/documents/count")
async def get_document_count():
    """获取已索引文档数量"""
    try:
        vs = get_vectorstore()
        count = vs.document_count()
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/reset")
async def reset_memory(session_id: str = "default"):
    """重置对话记忆"""
    try:
        engine = get_rag_engine()
        engine.reset_memory(session_id)
        return {"message": f"会话 {session_id} 的对话记忆已重置"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/reset-all")
async def reset_all_memory():
    """重置所有对话记忆"""
    try:
        engine = get_rag_engine()
        engine.reset_all_memories()
        return {"message": "所有对话记忆已重置"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
