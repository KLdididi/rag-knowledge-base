"""
RAG 知识库问答系统 - 启动入口
支持：混合检索、LangGraph工作流、SSE流式输出、多轮对话
"""

import uvicorn
from app.core.config import config


def main():
    print("=" * 55)
    print("  RAG Knowledge Base API Server v2.0")
    print("=" * 55)
    print(f"  Host:    http://{config.server.host}:{config.server.port}")
    print(f"  Docs:    http://{config.server.host}:{config.server.port}/docs")
    print(f"  Search:  {config.retriever.search_type}")
    print("=" * 55)

    uvicorn.run(
        "app.api.server:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
    )


if __name__ == "__main__":
    main()
