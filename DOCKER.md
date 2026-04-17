# Docker 部署指南

本文档提供 RAG 知识库系统的 Docker 容器化部署指南。

---

## 1. 快速开始

### 基础版（Ollama 本地模型）
```bash
# 启动 API + Ollama 服务
docker-compose --profile ollama up -d

# 访问 API
curl http://localhost:8000/health

# 查看文档
open http://localhost:8000/docs
```

### 高级版（OpenAI 云端模型）
```bash
# 设置 API Key
export OPENAI_API_KEY=sk-your-key-here

# 启动 API 服务
docker-compose up -d api

# 查看日志
docker logs -f rag-api
```

### 完整部署（API + Gradio UI）
```bash
# 高级版 + Gradio UI
export OPENAI_API_KEY=sk-your-key-here
docker-compose up -d api

# 单独启动 Gradio UI
docker-compose --profile ui up -d ui
# 访问 http://localhost:7860
```

---

## 2. Docker Compose Profiles

| Profile | 服务 | 说明 |
|---------|------|------|
| `ollama` | api + ollama | 基础版：本地模型，完全离线 |
| `openai` | api | 高级版：OpenAI 云端模型 |
| `ui` | ui | Gradio Web UI |

**启动组合示例**：
```bash
# 基础版 + UI
docker-compose --profile ollama --profile ui up -d

# 高级版 + UI
docker-compose up -d api && docker-compose --profile ui up -d ui
```

---

## 3. 环境变量配置

### 必需变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENAI_API_KEY` | - | OpenAI API Key（高级版必需） |
| `LLM_PROVIDER` | `openai` | LLM 提供商：`openai` 或 `ollama` |
| `LLM_MODEL` | `gpt-3.5-turbo` | LLM 模型名称 |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding 模型 |

### Ollama 配置（基础版）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OLLAMA_API_BASE` | `http://host.docker.internal:11434/v1` | Ollama API 地址 |
| `OLLAMA_MODEL` | `llama3` | Ollama 模型名称 |

### 检索配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SEARCH_TYPE` | `hybrid` | 检索类型：`similarity` / `mmr` / `hybrid` |
| `DEFAULT_TOP_K` | `5` | 默认检索文档数量 |

### 完整 .env 示例
```bash
# 高级版配置
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx
LLM_MODEL=gpt-4
EMBEDDING_MODEL=text-embedding-3-small

# 基础版配置
# LLM_PROVIDER=ollama
# OLLAMA_API_BASE=http://ollama:11434/v1
# OLLAMA_MODEL=llama3
# EMBEDDING_MODEL=nomic-embed-text

# 检索配置
SEARCH_TYPE=hybrid
DEFAULT_TOP_K=5
```

---

## 4. Ollama 模型管理

### 在容器中使用 Ollama

```bash
# 进入 Ollama 容器
docker exec -it rag-ollama bash

# 查看已安装模型
ollama list

# 拉取新模型
ollama pull llama3
ollama pull qwen2.5:3b
ollama pull nomic-embed-text

# 验证模型
ollama run llama3 "Hello"
```

### 推荐模型配置

| 用途 | 模型 | VRAM | 说明 |
|------|------|------|------|
| LLM（通用） | `llama3` | ~4GB | Meta 开源模型，效果好 |
| LLM（中文） | `qwen2.5:3b` | ~2GB | 阿里通义千问，中文优化 |
| LLM（更强） | `llama3:8b` | ~6GB | 更大参数，效果更好 |
| Embedding | `nomic-embed-text` | ~275MB | 高质量 Embedding |

### 预拉取模型（优化启动速度）

在 `docker-compose.yml` 中添加启动命令：
```yaml
ollama:
  image: ollama/ollama:latest
  command: bash -c "ollama pull llama3 && ollama pull nomic-embed-text && ollama serve"
```

---

## 5. 卷管理

| 主机路径 | 容器路径 | 说明 |
|----------|----------|------|
| `chroma_data` (named volume) | `/app/chroma_db` | 向量数据库持久化 |
| `./data` | `/app/data:ro` | 上传文档目录（只读） |
| `./logs` | `/app/logs` | 日志目录 |
| `ollama_data` (named volume) | `/root/.ollama` | Ollama 模型存储 |

### 备份向量数据库
```bash
# 备份
docker run --rm -v rag-network_chroma_data:/data -v $(pwd):/backup alpine tar czf /backup/chroma_backup.tar.gz -C /data .

# 恢复
docker run --rm -v rag-network_chroma_data:/data -v $(pwd):/backup alpine tar xzf /backup/chroma_backup.tar.gz -C /data
```

---

## 6. GPU 加速（NVIDIA GPU）

### 前置条件
- NVIDIA GPU + nvidia-container-toolkit

### docker-compose.yml 配置
```yaml
services:
  api:
    # ...
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=all

  ollama:
    # ...
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

---

## 7. 生产环境部署

### Nginx 反向代理 + SSL
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://rag-api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # SSE 流式输出
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }

    location /ui {
        proxy_pass http://rag-ui:7860;
        proxy_set_header Host $host;
    }
}
```

### Docker Swarm 部署
```bash
# 初始化 Swarm
docker swarm init

# 部署 stack
docker stack deploy -c docker-compose.yml rag-kb

# 扩缩容
docker service scale rag-kb_api=3
```

### Kubernetes 部署
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: your-registry/rag-kb:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: rag-secrets
              key: openai-api-key
```

---

## 8. 资源限制

### 开发环境（最小配置）
```yaml
deploy:
  resources:
    limits:
      memory: 512M
    reservations:
      memory: 256M
```

### 生产环境（推荐配置）
```yaml
deploy:
  resources:
    limits:
      memory: 2G
    reservations:
      memory: 512M
```

### Ollama + LLM（需要 GPU）
```yaml
deploy:
  resources:
    limits:
      memory: 8G
      device_ids: ['0']
    reservations:
      memory: 2G
```

---

## 9. 故障排查

### 容器启动失败
```bash
# 查看日志
docker logs -f rag-api

# 进入容器调试
docker exec -it rag-api /bin/bash

# 检查环境变量
docker exec rag-api env | grep -E "LLM|OLLAMA|OPENAI"
```

### Ollama 连接失败
```bash
# 检查 Ollama 是否运行
curl http://localhost:11434

# 在容器内检查
docker exec rag-api curl http://ollama:11434

# 检查网络连通性
docker network inspect rag-network
```

### 常见错误

**`Connection refused` to Ollama**：
```bash
# 确保 Ollama API Base 正确
export OLLAMA_API_BASE=http://ollama:11434/v1
docker-compose restart api
```

**`Incorrect API key` with OpenAI**：
```bash
# 验证 Key 格式
echo $OPENAI_API_KEY | head -c 20
# 正确格式: sk-proj-xxxxxxxxxxxxx
```

**向量数据库为空**：
```bash
# 检查卷挂载
docker volume inspect rag-network_chroma_data
# 上传文档
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@your_document.pdf"
```

---

## 10. 安全建议

1. **不将 API Key 写入镜像**：使用环境变量或 Docker secrets
2. **运行非 root 用户**：Dockerfile 已配置 `raguser`
3. **限制资源**：设置内存和 CPU 限制
4. **网络隔离**：使用 Docker 网络，不暴露不需要的端口
5. **定期备份**：备份向量数据库卷

```bash
# Docker secrets（Swarm 模式）
echo "sk-xxx" | docker secret create rag_openai_key -
```
