# CONTRIBUTING - 开发贡献指南

感谢您对本项目的关注！本文档将帮助您了解如何参与项目开发。

---

## 1. 开发环境设置

### 1.1 克隆项目
```bash
git clone https://github.com/KLdididi/rag-knowledge-base.git
cd rag-knowledge-base
```

### 1.2 创建虚拟环境
```bash
# 使用 venv
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS

# 或使用 conda
conda create -n rag-env python=3.10
conda activate rag-env
```

### 1.3 安装依赖
```bash
pip install -r requirements.txt
```

### 1.4 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 填入您的配置
```

### 1.5 启动服务验证
```bash
# 启动 API 服务
python run.py

# 启动 Gradio UI
python -m app.ui.gradio_app
```

---

## 2. 代码规范

### 2.1 Python 代码风格
- 遵循 PEP 8 规范
- 使用 Black 进行代码格式化
- 使用 Ruff 进行 linting

```bash
# 安装工具
pip install black ruff

# 格式化代码
black app/ tests/

# 检查代码
ruff check app/
```

### 2.2 命名规范
| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | `RAGEngine`, `VectorStore` |
| 函数名 | snake_case | `query_stream`, `load_file` |
| 常量 | UPPER_SNAKE_CASE | `MAX_CHUNK_SIZE`, `DEFAULT_TOP_K` |
| 私有成员 | 前缀 `_` | `_retrieve`, `_build_index` |
| 配置类 | PascalCase + Config | `LLMConfig`, `VectorStoreConfig` |

### 2.3 导入规范
```python
# 标准库
import os
import json
from typing import List, Optional

# 第三方库（按字母排序）
from fastapi import FastAPI
from langchain_core.documents import Document

# 本地导入
from app.core.config import config
from app.core.rag_engine import RAGEngine
```

### 2.4 文档字符串
```python
def query_stream(self, question: str, session_id: str = "default") -> AsyncIterator[str]:
    """
    流式查询方法，逐 Token 返回回答。
    
    Args:
        question: 用户问题
        session_id: 会话 ID，用于追踪对话历史
    
    Yields:
        str: 生成的 Token 字符串
    
    Raises:
        ValueError: question 为空时抛出
        RuntimeError: LLM 服务不可用时抛出
    """
```

---

## 3. Git 工作流程

### 3.1 分支命名
| 分支类型 | 命名规范 | 示例 |
|----------|----------|------|
| 功能分支 | feature/功能名 | feature/streaming-output |
| 修复分支 | fix/问题描述 | fix/retrieve-return-bug |
| 文档分支 | docs/文档类型 | docs/add-api-reference |
| 重构分支 | refactor/模块名 | refactor/vectorstore |

### 3.2 提交规范
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 类型**：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构（不影响功能）
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例**：
```
feat(vectorstore): 添加 BM25 混合检索支持

- 实现 hybrid_search 方法
- 使用 RRF 算法融合向量和 BM25 结果
- 添加单元测试

Closes #12
```

### 3.3 Pull Request 流程
1. Fork 项目并创建功能分支
2. 编写代码并添加测试
3. 确保所有测试通过
4. 更新相关文档
5. 提交 Pull Request
6. 等待代码审查
7. 合并到主分支

---

## 4. 测试规范

### 4.1 测试文件位置
```
tests/
├── __init__.py
├── test_core.py      # 核心模块测试
├── test_api.py       # API 集成测试
└── test_vectorstore.py  # 向量存储测试
```

### 4.2 测试规范
```python
import pytest
from langchain_core.documents import Document

class TestVectorStore:
    """向量存储测试"""
    
    def test_create_from_documents(self):
        """测试从文档创建向量存储"""
        # Arrange
        docs = [Document(page_content="Test content")]
        
        # Act
        vs = VectorStore(embeddings=mock_embeddings)
        vs.create_from_documents(docs)
        
        # Assert
        assert vs.document_count() == 1
    
    def test_hybrid_search_returns_ranked_results(self):
        """测试混合检索返回排序结果"""
        # ...
```

### 4.3 运行测试
```bash
# 运行所有测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_core.py -v

# 运行单个测试
pytest tests/test_core.py::TestVectorStore::test_hybrid_search -v

# 生成覆盖率报告
pytest tests/ --cov=app --cov-report=html
```

### 4.4 Mock 规范
```python
from unittest.mock import MagicMock

@pytest.fixture
def mock_embeddings():
    embeddings = MagicMock()
    embeddings.embed_query.return_value = [0.1] * 384
    return embeddings
```

---

## 5. 模块开发指南

### 5.1 添加新的文档加载器
1. 在 `app/core/loader.py` 中添加新方法
2. 更新 `SUPPORTED_EXTENSIONS` 列表
3. 添加单元测试
4. 更新 README 文档

```python
def load_markdown(self, file_path: str) -> List[Document]:
    """加载 Markdown 文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return [Document(
        page_content=content,
        metadata={'filename': os.path.basename(file_path), 'type': 'md'}
    )]
```

### 5.2 添加新的检索策略
1. 在 `app/core/vectorstore.py` 中实现新方法
2. 在 `app/core/config.py` 中添加配置项
3. 在 `app/core/rag_engine.py` 中集成新策略
4. 添加测试和文档

### 5.3 添加新的 Prompt 模板
1. 在 `app/core/prompts/` 目录创建或修改文件
2. 在 `rag_engine.py` 中引用新模板
3. 确保 Prompt 支持变量插值

---

## 6. 代码审查清单

提交 Pull Request 前，请确保：

- [ ] 代码通过所有测试
- [ ] 新功能包含单元测试
- [ ] 代码符合 PEP 8 规范
- [ ] 导入了所需的依赖（如有新增）
- [ ] 更新了相关文档
- [ ] 没有硬编码的敏感信息
- [ ] Commit 消息清晰描述变更内容

---

## 7. 许可证

本项目采用 MIT 许可证。提交贡献即表示您同意您的代码将按照 MIT 许可证的条款发布。
