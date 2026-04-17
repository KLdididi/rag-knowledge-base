# 面试项目升级 - 基础版 (Ollama + Gradio)

## 已完成的升级

### 1. Ollama 本地模型支持
- 修改了 `app/core/config.py`，添加 LLM_PROVIDER 配置
- 修改了 `app/api/server.py`，支持 Ollama 和 OpenAI 切换
- 默认使用 Ollama，无需 API Key

### 2. Gradio Web UI
- 创建了 `app/ui/gradio_app.py`，包含完整可视化界面
- 支持对话、文档上传、设置切换

### 3. 依赖更新
- 添加了 `langchain-ollama`, `langchain-openai`, `gradio`
- 修复了 langchain 版本兼容问题

## 启动方式

### 方式一：启动 Gradio UI
```bash
cd "C:\Users\Administrator\Desktop\面试项目"
python -m app.ui.gradio_app
# 访问 http://localhost:7860
```

### 方式二：启动 FastAPI 服务
```bash
cd "C:\Users\Administrator\Desktop\面试项目"
python run.py
# API: http://localhost:8000
# 文档: http://localhost:8000/docs
```

## 配置说明 (.env)

```env
# LLM 提供商: ollama / openai
LLM_PROVIDER=ollama

# 模型选择 (Ollama)
LLM_MODEL=llama3
# 或: qwen2.5:3b, deepseek-r1:1.5b, mistral

# Embedding 模型 (Ollama)
EMBEDDING_MODEL=nomic-embed-text

# 检索模式
SEARCH_TYPE=hybrid  # hybrid/similarity/mmr
```

## 面试亮点

1. **本地部署** - 不依赖 API Key，展示对本地 LLM 的理解
2. **混合检索** - 向量 + BM25 + RRF，展示 RAG 核心算法
3. **可视化界面** - Gradio UI，现场演示效果好
4. **多模型支持** - 可切换 Ollama 模型

## 注意事项

1. 首次使用需确保 Ollama 已启动：`ollama serve`
2. 如需 OpenAI API，修改 .env 中的 LLM_PROVIDER=openai
3. 文档数据存储在 ./chroma_db 目录
