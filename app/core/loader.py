"""
文档加载模块
支持 PDF、TXT、Word、Markdown、CSV 等多格式文档的加载与解析
"""

import os
from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document


class DocumentLoader:
    """统一文档加载器，支持多格式文件"""

    SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx", ".md", ".csv"}

    def __init__(self):
        self._loaders = {
            ".txt": self._load_text,
            ".pdf": self._load_pdf,
            ".docx": self._load_word,
            ".md": self._load_markdown,
            ".csv": self._load_csv,
        }

    def load_file(self, file_path: str) -> List[Document]:
        """加载单个文件"""
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext not in self._loaders:
            raise ValueError(f"不支持的文件格式: {ext}，支持: {list(self._loaders.keys())}")

        docs = self._loaders[ext](file_path)
        for doc in docs:
            doc.metadata["source"] = str(path)
            doc.metadata["filename"] = path.name
            doc.metadata["file_type"] = ext
        return docs

    def load_directory(self, directory: str, recursive: bool = True) -> List[Document]:
        """加载目录下所有支持的文档"""
        dir_path = Path(directory)
        if not dir_path.exists():
            raise FileNotFoundError(f"目录不存在: {directory}")

        pattern = "**/*.*" if recursive else "*.*"
        all_documents = []

        for file_path in dir_path.glob(pattern):
            if file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                try:
                    docs = self.load_file(str(file_path))
                    all_documents.extend(docs)
                except Exception as e:
                    print(f"加载文件失败 {file_path}: {e}")

        return all_documents

    def _load_text(self, file_path: str) -> List[Document]:
        """加载 TXT 文件"""
        from langchain_community.document_loaders import TextLoader
        loader = TextLoader(file_path, encoding="utf-8")
        return loader.load()

    def _load_pdf(self, file_path: str) -> List[Document]:
        """加载 PDF 文件"""
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(file_path)
        return loader.load()

    def _load_word(self, file_path: str) -> List[Document]:
        """加载 Word 文件"""
        from langchain_community.document_loaders import Docx2txtLoader
        loader = Docx2txtLoader(file_path)
        return loader.load()

    def _load_markdown(self, file_path: str) -> List[Document]:
        """加载 Markdown 文件"""
        from langchain_community.document_loaders import UnstructuredMarkdownLoader
        loader = UnstructuredMarkdownLoader(file_path)
        return loader.load()

    def _load_csv(self, file_path: str) -> List[Document]:
        """加载 CSV 文件（每行作为一个文档）"""
        import csv
        documents = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return [Document(page_content="空CSV文件", metadata={"source": file_path})]

        fieldnames = list(rows[0].keys())
        for i, row in enumerate(rows):
            # 将每行转为自然语言描述
            content_parts = [f"{k}: {v}" for k, v in row.items() if v]
            content = f"CSV记录 #{i+1}\n" + "\n".join(content_parts)
            documents.append(Document(
                page_content=content,
                metadata={
                    "source": file_path,
                    "row_index": i,
                    "columns": fieldnames,
                    "total_rows": len(rows),
                },
            ))
        return documents
