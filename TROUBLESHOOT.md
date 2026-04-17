# TROUBLESHOOT - 常见问题排查指南

本文档收录 RAG 知识库系统的常见问题及解决方案。

---

## 1. 启动问题

### 1.1 Ollama 连接失败

**错误信息**：
```
ConnectionError: [Errno 111] Connection refused
httpx.ConnectError: Connection refused
```

**原因**：Ollama 服务未启动

**解决方案**：
```bash
# 启动 Ollama 服务
ollama serve

# 验证服务状态
curl http://localhost:11434
# 应返回: {"status":"ok"}
```

**高级配置**（如使用非默认端口）：
```env
OLLAMA_API_BASE=http://localhost:11434/v1
```

---

### 1.2 模型未找到

**错误信息**：
```
Error: model 'qwen2.5:3b' not found
```

**原因**：指定的模型未下载

**解决方案**：
```bash
# 查看已安装模型
ollama list

# 拉取模型（以 qwen2.5:3b 为例）
ollama pull qwen2.5:3b

# 其他常用模型
ollama pull llama3
ollama pull deepseek-r1:1.5b
ollama pull mistral
ollama pull nomic-embed-text  # Embedding 模型
```

---

### 1.3 端口被占用

**错误信息**：
```
OSError: [Errno 10048] Only one usage of each socket address is normally permitted
```

**原因**：8000 或 7860 端口已被其他程序占用

**解决方案**：
```bash
# 查找占用端口的进程
netstat -ano | findstr :8000   # FastAPI
netstat -ano | findstr :7860   # Gradio

# 结束进程（替换 PID 为实际值）
taskkill /PID <PID> /F

# 或修改 .env 使用其他端口
# API_PORT=8001
# GRADIO_PORT=7861
```

---

## 2. 导入和依赖问题

### 2.1 langchain 版本不兼容

**错误信息**：
```
ImportError: cannot import name 'Document' from 'langchain.schema'
ModuleNotFoundError: No module named 'langchain.memory'
```

**原因**：项目使用了已废弃的 langchain 导入路径

**解决方案**：
```bash
# 更新依赖
pip install -r requirements.txt --upgrade

# 或手动安装 langchain_core
pip install langchain-core langchain-community
```

**正确的导入方式**：
```python
# 旧版（已废弃）
from langchain.schema import Document
from langchain.prompts import ChatPromptTemplate

# 新版
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
```

---

### 2.2 Chroma 数据库锁定

**错误信息**：
```
ValueError: Database at ./chroma_db is already connected to by another instance
```

**原因**：多个进程同时访问同一个 Chroma 数据库

**解决方案**：
```bash
# 方案1：重启 Ollama 服务释放锁
ollama serve

# 方案2：删除锁文件
del chroma_db\chroma.sqlite-journal

# 方案3：使用新的数据库目录
# 修改 .env:
# PERSIST_DIRECTORY=./chroma_db_v2
```

---

### 2.3 Embedding 模型加载失败

**错误信息**：
```
ValueError: Model not loaded. Run `ollama pull nomic-embed-text` first
```

**原因**：Ollama Embedding 模型未安装

**解决方案**：
```bash
# 拉取 Embedding 模型
ollama pull nomic-embed-text

# 验证
ollama run nomic-embed-text "Hello world"
```

---

## 3. 功能问题

### 3.1 检索结果为空

**原因**：向量数据库中无文档或文档数量为 0

**解决方案**：
```bash
# 1. 检查文档数量
curl http://localhost:8000/api/documents/count

# 2. 上传文档（通过 Gradio UI 或 API）
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@your_document.pdf"

# 3. 或使用测试文档验证
python -c "from app.core.loader import DocumentLoader; from app.core.splitter import TextSplitter; from app.core.vectorstore import VectorStore
loader = DocumentLoader()
splitter = TextSplitter()
docs = loader.load_file('data/test_rag.txt')
chunks = splitter.split_documents(docs)
vs = VectorStore(embeddings=..., persist_directory='./chroma_db')
vs.create_from_documents(chunks)
print(f'Indexed {len(chunks)} chunks')"
```

---

### 3.2 回答质量差

**可能原因**：
1. 文档未正确分块
2. Embedding 模型不匹配
3. 检索参数不合适

**优化建议**：
```python
# 调整分块大小
splitter = TextSplitter(chunk_size=500, chunk_overlap=50)

# 调整检索数量
engine.top_k = 8  # 增加检索数量

# 尝试不同检索模式
engine.search_type = 'mmr'  # 多样性检索
engine.search_type = 'hybrid'  # 混合检索（默认）
```

---

### 3.3 流式输出不工作

**原因**：Gradio 版本不兼容或浏览器问题

**解决方案**：
```bash
# 更新 Gradio
pip install gradio --upgrade

# 使用 Chrome 或 Edge 浏览器
# 确保网络连接稳定

# 检查 SSE 端点
curl -N -X POST http://localhost:8000/api/query/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "测试"}'
```

---

## 4. 配置问题

### 4.1 环境变量不生效

**原因**：.env 文件未正确配置

**检查清单**：
```bash
# 1. 确认 .env 文件存在且在项目根目录
ls .env

# 2. 确认无空格和引号问题
# 正确: API_KEY=sk-xxxx
# 错误: API_KEY="sk-xxxx"

# 3. 重启服务使配置生效
python run.py  # 或 python -m app.ui.gradio_app
```

---

### 4.2 OpenAI API Key 无效

**错误信息**：
```
AuthenticationError: Incorrect API key provided
```

**解决方案**：
```bash
# 检查 API Key 格式
# 正确: sk-proj-xxxxxxxxxxxxx
# 错误: sk-xxxxxxxx (过时的格式)

# 确认 Key 有余额
# 访问 https://platform.openai.com/account/usage

# 设置正确的 API Base（使用代理）
# OPENAI_API_BASE=https://api.openai.com/v1
```

---

## 5. 性能问题

### 5.1 首次响应慢

**原因**：首次调用时 LLM 需要加载模型

**优化方案**：
```bash
# Ollama：预加载模型
ollama pull llama3  # 确保模型已缓存

# 基础版（Ollama）首次响应通常 10-30 秒，后续 <1 秒
# 高级版（GPT-4）取决于网络延迟
```

---

### 5.2 内存占用高

**原因**：Chroma 数据库或模型占用大量内存

**优化方案**：
```python
# 减少检索数量
top_k = 4  # 默认

# 使用更小的 Embedding 模型
EMBEDDING_MODEL=nomic-embed-text  # 较小

# 定期清理数据库
# 删除 chroma_db 目录重建
```

---

## 6. 其他问题

### 6.1 Windows 中文路径问题

**原因**：项目路径包含中文字符

**解决方案**：
```bash
# 方案1：将项目移动到纯英文路径
# C:\Users\Administrator\Desktop\面试项目 -> C:\Users\Administrator\projects\rag_knowledge_base

# 方案2：使用 PowerShell 7+
pwsh -Command "cd 'C:\Users\Administrator\Desktop\面试项目'; python run.py"
```

---

### 6.2 Docker 容器无法访问 Ollama

**解决方案**：
```yaml
# docker-compose.yml
services:
  rag:
    environment:
      - OLLAMA_API_BASE=http://host.docker.internal:11434/v1
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

---

## 获取帮助

如遇本文档未覆盖的问题：

1. 查看 GitHub Issues：https://github.com/KLdididi/rag-knowledge-base/issues
2. 查看 API 文档：http://localhost:8000/docs
3. 查看运行时日志获取详细错误信息
