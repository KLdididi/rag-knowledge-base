# 面试项目升级 - 高级版 (GPT-4 + 流式输出 + Reranker)

## 高端版 vs 基础版

| 功能 | 基础版 | 高级版 |
|------|--------|--------|
| LLM | Ollama (本地) | GPT-4 (API) |
| Embedding | nomic-embed-text | text-embedding-3-small |
| 检索 | 混合检索 | 混合检索 + Reranker |
| 缓存 | 无 | 智能缓存 |
| 输出 | 批量 | 流式输出 (实时显示) |

## 启动方式

### 1. 配置 API Key
编辑 `.env` 文件：
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
LLM_MODEL=gpt-4
EMBEDDING_MODEL=text-embedding-3-small
USE_RERANKER=true
USE_CACHE=true
STREAMING=true
```

### 2. 启动 Gradio UI
```bash
cd "C:\Users\Administrator\Desktop\面试项目"
python -m app.ui.gradio_app
# 访问 http://localhost:7860
```

## 面试亮点

### 1. GPT-4 强大能力
- 回答质量更高
- 支持更长上下文

### 2. 流式输出
- 实时显示回答
- 面试演示效果炫酷

### 3. Reranker 重排序
- 检索更多候选 (10个)
- 智能重排序提升相关性
- 面试可以讲"先检索后排序"的两阶段架构

### 4. 响应缓存
- 相同问题秒级响应
- 节省 API 调用成本

## 技术架构图

```
用户问题
   ↓
┌─────────────────────────────────────┐
│           RAG Engine                │
├─────────────────────────────────────┤
│  1. 缓存检查 (Cache)                │
│     ↓ 有缓存 → 直接返回             │
│  2. 混合检索 (Hybrid Search)        │
│     - 向量检索 (Chroma)             │
│     - BM25 关键词检索               │
│     ↓                               │
│  3. Reranker 重排序                │
│     ↓                               │
│  4. GPT-4 生成回答                 │
│     ↓                               │
│  5. 流式输出 (SSE)                  │
│     ↓                               │
│  6. 缓存存储                        │
└─────────────────────────────────────┘
   ↓
回答用户
```

## 费用估算

| 项目 | 消耗 | 费用 |
|------|------|------|
| GPT-4 | ~$0.01/次 | 按量计费 |
| Embedding | ~$0.0001/次 | 按量计费 |
| 缓存命中 | 免费 | 0 |

面试展示时可以说："生产环境可以用缓存降低 50% 成本"
