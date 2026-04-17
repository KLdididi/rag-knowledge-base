# API Reference - RAG Knowledge Base

本文档提供 RAG 知识库系统的完整 API 参考。

---

## Base URL

```
http://localhost:8000
```

API 文档（Swagger UI）：http://localhost:8000/docs

---

## 1. 健康检查

### GET /health

检查服务健康状态。

**响应示例**：
```json
{
  "status": "ok",
  "version": "2.0.0",
  "document_count": 42,
  "supported_formats": [".pdf", ".docx", ".txt", ".md", ".csv"],
  "llm_provider": "openai",
  "llm_model": "gpt-4",
  "embedding_model": "text-embedding-3-small"
}
```

---

## 2. RAG 查询

### POST /api/query

标准 RAG 知识库查询（非流式）。

**请求体**：
```json
{
  "query": "什么是 RAG 技术？",
  "search_type": "hybrid",
  "top_k": 4,
  "prompt_mode": "standard",
  "session_id": "user123",
  "return_sources": true
}
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | ✅ | - | 用户查询问题 |
| `search_type` | string | ❌ | "hybrid" | 检索类型：similarity / mmr / hybrid |
| `top_k` | integer | ❌ | 4 | 检索的文档数量 |
| `prompt_mode` | string | ❌ | "standard" | Prompt 模式：standard / few_shot / structured |
| `session_id` | string | ❌ | "default" | 会话 ID，用于追踪对话历史 |
| `return_sources` | boolean | ❌ | true | 是否返回检索来源 |

**响应示例**：
```json
{
  "answer": "RAG（Retrieval Augmented Generation）是一种结合检索和生成的技术...",
  "question": "什么是 RAG 技术？",
  "sources": [
    {
      "content": "RAG 是检索增强生成的缩写...",
      "metadata": {"filename": "rag_guide.md", "chunk_index": 0}
    }
  ],
  "session_id": "user123",
  "latency_ms": 1234
}
```

**错误响应**：
```json
{
  "detail": "No documents found in knowledge base"
}
```

---

### POST /api/query/stream

SSE 流式 RAG 查询，逐 Token 返回。

**请求体**：同 `/api/query`

**响应类型**：Server-Sent Events (text/event-stream)

**数据格式**：
```
data: {"token": "RAG"}

data: {"token": "（"}

data: {"token": "检索"}

...

data: [DONE]
```

**响应头**：
```
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
```

**cURL 示例**：
```bash
curl -N -X POST http://localhost:8000/api/query/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "介绍一下 Python"}'
```

---

## 3. LangGraph 工作流

### POST /api/graph

使用 LangGraph 状态图工作流进行查询，包含执行链路追踪。

**请求体**：
```json
{
  "query": "查找向量数据库相关信息",
  "session_id": "user456"
}
```

**响应示例**：
```json
{
  "answer": "向量数据库是一种专门用于存储和检索向量嵌入的数据库...",
  "trace": [
    {
      "node": "intent_classifier",
      "input": "查找向量数据库相关信息",
      "output": "knowledge_query",
      "status": "success"
    },
    {
      "node": "retriever",
      "input": "查找向量数据库相关信息",
      "output": "检索到 3 个相关文档",
      "status": "success"
    },
    {
      "node": "generator",
      "input": "基于 3 个文档生成回答",
      "output": "回答已生成",
      "status": "success"
    }
  ]
}
```

---

## 4. Agent 问答

### POST /api/agent

Agent 智能问答接口。

**请求体**：
```json
{
  "query": "帮我总结这篇文档的要点",
  "mode": "analyze",
  "session_id": "user789"
}
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | ✅ | - | 用户查询 |
| `mode` | string | ❌ | "query" | Agent 模式：query / analyze / summarize |
| `session_id` | string | ❌ | "default" | 会话 ID |

**响应示例**：
```json
{
  "answer": "文档要点总结：\n1. RAG 技术原理\n2. 检索策略优化\n3. 性能调优方法",
  "mode": "analyze",
  "session_id": "user789"
}
```

---

## 5. 文档管理

### POST /api/documents/upload

上传并索引文档。

**请求类型**：multipart/form-data

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | ✅ | 上传的文件（PDF/Word/TXT/Markdown/CSV） |
| `chunk_size` | integer | ❌ | 分块大小（默认从配置读取） |
| `chunk_overlap` | integer | ❌ | 分块重叠大小（默认从配置读取） |

**cURL 示例**：
```bash
# 上传 PDF
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@technical_doc.pdf"

# 上传 Markdown
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@readme.md"

# 上传 CSV
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@sales_data.csv"
```

**响应示例**：
```json
{
  "status": "success",
  "filename": "technical_doc.pdf",
  "document_count": 3,
  "chunks_created": 15
}
```

**错误响应**：
```json
{
  "detail": "Unsupported file format: .xyz"
}
```

---

### GET /api/documents/count

获取已索引文档数量。

**响应示例**：
```json
{
  "count": 42,
  "vectorstore_size_mb": 12.5
}
```

---

### DELETE /api/documents

删除所有索引文档（慎用）。

**响应示例**：
```json
{
  "status": "success",
  "deleted_count": 42
}
```

---

## 6. 对话记忆

### POST /api/memory/reset

重置指定会话的对话记忆。

**请求体**：
```json
{
  "session_id": "user123"
}
```

**响应示例**：
```json
{
  "status": "success",
  "session_id": "user123",
  "message": "Session memory reset successfully"
}
```

---

### POST /api/memory/reset-all

重置所有会话的对话记忆。

**响应示例**：
```json
{
  "status": "success",
  "message": "All session memories reset successfully",
  "sessions_cleared": 5
}
```

---

## 7. 缓存管理

### GET /api/cache/stats

获取缓存统计信息。

**响应示例**：
```json
{
  "enabled": true,
  "cache_size": 128,
  "hit_count": 42,
  "miss_count": 15,
  "hit_rate": "73.7%"
}
```

---

### DELETE /api/cache/clear

清空响应缓存。

**响应示例**：
```json
{
  "status": "success",
  "message": "Cache cleared successfully"
}
```

---

## 8. 错误代码

| HTTP 状态码 | 说明 |
|-------------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 422 | 请求体验证失败 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用（如 LLM 服务未启动） |

---

## 9. 完整请求示例

### Python 示例
```python
import requests

# 标准查询
response = requests.post(
    "http://localhost:8000/api/query",
    json={
        "query": "RAG 是什么？",
        "search_type": "hybrid",
        "prompt_mode": "few_shot"
    }
)
print(response.json())

# 流式查询
import sseclient
response = requests.post(
    "http://localhost:8000/api/query/stream",
    json={"query": "介绍一下 Python"},
    stream=True
)
client = sseclient.SSEClient(response)
for event in client.events():
    if event.data == "[DONE]":
        break
    print(event.data)
```

### JavaScript 示例
```javascript
// 标准查询
const response = await fetch('http://localhost:8000/api/query', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({query: 'RAG 是什么？'})
});
const data = await response.json();
console.log(data.answer);

// 流式查询
const stream = await fetch('http://localhost:8000/api/query/stream', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({query: '介绍一下 Python'})
});
const reader = stream.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const {done, value} = await reader.read();
  if (done) break;
  const text = decoder.decode(value);
  console.log(text);
}
```
