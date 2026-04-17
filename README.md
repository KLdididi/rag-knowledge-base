# RAG Knowledge Base Assistant

> 基于大语言模型的智能知识库问答系统，集成混合检索、LangGraph多Agent工作流、Prompt工程与流式输出。

## 系统架构图

```
用户请求
   │
   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Gradio UI / FastAPI                        │
│              (http://localhost:7860 / :8000)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
   ┌─────────────────────────┼─────────────────────────┐
   │                         │                         │
   ▼                         ▼                         ▼
┌──────────┐          ┌──────────────┐        ┌────────────┐
│ 流式输出  │          │  RAG Engine   │        │  Workflow  │
│ (SSE)    │          │  核心引擎      │        │  LangGraph │
└──────────┘          └───────┬───────┘        └─────┬──────┘
                               │                       │
        ┌──────────────────────┼───────────────────────┤
        │                      │                       │
        ▼                      ▼                       ▼
┌──────────────────┐  ┌───────────────┐  ┌─────────────────────┐
│    智能缓存        │  │  检索器        │  │   意图识别          │
│  (Hash Cache)     │  │  Retriever    │  │  Intent Classifier │
└──────────────────┘  └───────┬───────┘  └──────────┬──────────┘
                               │                       │
              ┌────────────────┼───────────────────────┤
              │                │                       │
              ▼                ▼                       ▼
      ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐
      │  缓存命中?    │  │ 检索策略路由  │  │  检索 → 生成 → 质量检查  │
      │  Yes → 返回  │  │ (混合/MMR/相似)│  │       DAG 执行链路        │
      └──────────────┘  └───────┬───────┘  └──────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────────┐
              │                  │                      │
              ▼                  ▼                      ▼
      ┌──────────────┐  ┌──────────────┐      ┌──────────────┐
      │  向量检索     │  │   BM25       │      │  Reranker    │
      │ (Embedding)  │  │ 关键词检索    │      │  重排序      │
      └──────┬───────┘  └──────┬───────┘      └──────┬───────┘
             │                  │                      │
             └──────────────────┼──────────────────────┘
                                │
                                ▼
                       ┌──────────────┐
                       │   RRF 融合   │
                       │  排序合并     │
                       └──────┬───────┘
                              │
                              ▼
                       ┌──────────────┐
                       │  LLM 生成    │
                       │  流式返回     │
                       └──────────────┘


## 项目简介

面向企业知识管理场景构建的RAG（Retrieval Augmented Generation）问答系统。采用向量检索+BM25关键词检索的混合召回策略，通过RRF（Reciprocal Rank Fusion）融合排序，结合LangGraph状态图驱动的多Agent工作流，实现意图识别→检索路由→回答生成→质量检查的完整pipeline。

## 技术栈

| 模块 | 技术选型 |
|------|----------|
| 核心语言 | Python 3.10+ |
| LLM框架 | LangChain + LangGraph |
| 大模型 | OpenAI GPT（兼容各类API） |
| Embedding | OpenAI Embedding |
| 向量数据库 | Chroma |
| 混合检索 | Vector Search + BM25 + RRF |
| 工作流引擎 | LangGraph StateGraph |
| API服务 | FastAPI + Uvicorn + SSE |
| 容器化 | Docker + Docker Compose |
| 测试 | Pytest + httpx |

## 项目架构

```
rag_knowledge_base/
├── app/
│   ├── __init__.py
│   ├── core/                       # 核心模块
│   │   ├── config.py               # 统一配置管理（环境变量→dataclass）
│   │   ├── loader.py               # 文档加载器（PDF/Word/TXT/Markdown/CSV）
│   │   ├── splitter.py             # 文本切分（递归字符切分+元数据保留）
│   │   ├── vectorstore.py          # 向量存储 + 混合检索（Vector+BM25+RRF）
│   │   ├── rag_engine.py           # RAG引擎（检索+生成+对话记忆+流式输出）
│   │   └── prompts/                # Prompt模板管理
│   │       ├── rag_prompts.py      # RAG Prompt（标准/Few-shot/结构化输出）
│   │       └── agent_prompts.py    # Agent Prompt（路由/问答）
│   ├── agents/
│   │   └── workflow.py             # LangGraph状态图工作流
│   └── api/
│       └── server.py               # FastAPI服务（9个API接口）
├── tests/
│   ├── test_core.py                # 核心模块单元测试
│   └── test_api.py                 # API集成测试
├── data/                           # 文档数据目录
├── run.py                          # 启动入口
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── .gitignore
```

## 核心功能

### 1. 多格式文档解析
- 支持 PDF、Word、TXT、Markdown、CSV 五种格式
- 策略模式（Strategy Pattern）实现，新增格式只需添加loader方法
- CSV加载时自动将每行转为自然语言描述，便于语义检索
- 自动提取文件元数据（文件名、类型、来源）

### 2. 混合检索策略
- **向量检索**：基于Embedding的语义相似度搜索
- **BM25检索**：基于关键词匹配的稀疏检索
- **RRF融合**：Reciprocal Rank Fusion算法合并两路召回结果
- **MMR检索**：最大边际相关性，保证结果多样性
- 可通过配置切换检索模式（similarity/mmr/hybrid）

### 3. LangGraph 状态图工作流
- 基于 LangGraph StateGraph 构建有向无环工作流
- **意图识别节点**：分类用户查询（知识查询/文档上传/重置/对话）
- **条件路由**：根据意图分支到不同处理节点
- **检索节点**：执行混合检索
- **生成节点**：基于检索上下文生成回答
- **质量检查节点**：评估回答质量，不合格可重试
- 支持完整执行链路追踪（trace）

### 4. Prompt 工程
- **标准模式**：结构化Prompt，约束LLM仅基于上下文回答
- **Few-shot模式**：带示例的Prompt，提升输出格式一致性
- **结构化输出模式**：约束LLM输出JSON，便于下游解析
- Prompt模板与代码分离，支持热更新

### 5. 对话记忆管理
- 基于 Session ID 的多会话隔离
- 每个Session独立维护对话历史
- 支持单会话重置和全量重置
- 自动限制对话历史长度，避免Token溢出

### 6. SSE 流式输出
- 基于 Server-Sent Events 的实时流式响应
- 逐Token输出，适合前端实时渲染
- 支持错误处理和连接中断恢复

### 7. API服务
- FastAPI 构建，自动生成交互式 API 文档（Swagger UI）
- 9个API接口覆盖全部功能
- CORS跨域支持
- 统一异常处理和响应模型

## 快速开始

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 启动服务
python run.py

# 运行测试
pytest tests/ -v
```

### Docker部署

```bash
# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

启动后访问：
- API服务：http://localhost:8000
- API文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查（返回版本、文档数、支持格式） |
| `/api/query` | POST | RAG知识库查询（支持检索类型和Prompt模式选择） |
| `/api/query/stream` | POST | SSE流式查询 |
| `/api/graph` | POST | LangGraph工作流查询（返回执行链路追踪） |
| `/api/agent` | POST | Agent智能问答 |
| `/api/documents/upload` | POST | 上传并索引文档 |
| `/api/documents/count` | GET | 获取已索引文档数量 |
| `/api/memory/reset` | POST | 重置指定会话的对话记忆 |
| `/api/memory/reset-all` | POST | 重置所有对话记忆 |

### 示例请求

```bash
# 混合检索查询
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "什么是RAG技术", "search_type": "hybrid", "prompt_mode": "few_shot"}'

# LangGraph工作流查询（带链路追踪）
curl -X POST http://localhost:8000/api/graph \
  -H "Content-Type: application/json" \
  -d '{"query": "帮我查找向量数据库相关信息"}'

# SSE流式查询
curl -N -X POST http://localhost:8000/api/query/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "介绍一下Embedding技术", "session_id": "user123"}'

# 上传Markdown文档
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@technical_doc.md"

# 上传CSV数据
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@sales_data.csv"
```

## 设计决策

### 为什么用混合检索？
纯向量检索对专有名词、编号等精确匹配效果差；纯BM25无法理解语义。混合检索通过RRF融合两路召回，互补短板，实际场景中检索准确率可提升20-30%。

### 为什么用LangGraph而不是简单Agent？
LangGraph提供显式状态管理和条件路由，支持：
- 工作流可视化（有向图结构）
- 质量检查→重试的循环逻辑
- 完整的执行链路追踪（trace）
- 更可控的Agent行为，适合生产环境

### 为什么Prompt要与代码分离？
Prompt需要频繁迭代调优，分离后可以：
- 不改代码直接调整Prompt策略
- A/B测试不同Prompt效果
- 支持Prompt版本管理
