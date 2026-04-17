# CHANGELOG - RAG Knowledge Base

All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-04-17

### Added
- **Ollama 本地模型支持**：配置 LLM_PROVIDER=ollama 即可使用本地模型，无需 API Key
- **Gradio Web UI**：`app/ui/gradio_app.py` 提供可视化对话界面，支持流式输出
- **流式输出 (SSE)**：基于 Server-Sent Events 的实时流式响应，逐 Token 输出
- **智能缓存**：基于问题文本 Hash 的响应缓存，相同问题秒级返回
- **Reranker 重排序**：使用重排序模型对检索结果进行二次排序，提升相关性
- **版本管理**：统一的版本号管理（当前版本 2.0.0）
- **GitHub 仓库**：https://github.com/KLdididi/rag-knowledge-base

### Changed
- **配置管理**：统一使用 .env 环境变量配置，移除硬编码
- **依赖更新**：更新至 langchain-ollama、langchain-openai、langchain-chroma 等最新版本
- **向量存储**：Chroma 持久化存储，支持增量添加文档
- **混合检索**：优化 RRF 融合算法，文档 ID 使用内容索引替代内存地址
- **API 文档**：自动生成 Swagger UI 交互式文档

### Fixed
- 修复 _retrieve 方法在 hybrid 和 mmr 模式下缺失 return 语句的 bug
- 修复 gradio_app.py 同步调用异步 query_stream 的问题
- 修复 vectorstore.py 使用 id(doc.page_content) 作为文档 ID 的问题
- 修复 langchain 版本兼容性问题（迁移至 langchain_core）

### Deprecated
- 移除 langchain.schema（旧版导入路径）
- 移除 langchain.prompts（旧版导入路径）
- 移除 langchain.chains（旧版导入路径）
- 移除 langchain.memory（旧版导入路径）
- 移除 langchain.vectorstores（旧版导入路径）
- 移除 langchain.text_splitters（旧版导入路径）

## [1.0.0] - 2026-04-15

### Added
- 基础 RAG 问答系统
- 多格式文档加载（PDF、Word、TXT、Markdown、CSV）
- 文本切分（递归字符切分 + 元数据保留）
- Chroma 向量数据库
- 混合检索（向量检索 + BM25 + RRF 融合）
- LangGraph 状态图工作流
- FastAPI REST API（9 个接口）
- Docker 部署支持
- 单元测试和集成测试
- README 完整文档
