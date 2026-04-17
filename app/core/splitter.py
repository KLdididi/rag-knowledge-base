"""
文本切分模块
支持递归字符切分、Token切分等多种策略
"""

from typing import List, Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class TextSplitter:
    """文本切分器，提供多种切分策略"""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", "。", "！", "？", " ", ""]
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=self.separators,
        )

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """对文档列表进行切分"""
        return self._splitter.split_documents(documents)

    def split_text(self, text: str) -> List[Document]:
        """对纯文本进行切分"""
        return self._splitter.create_documents([text])

    def split_and_preserve_metadata(self, documents: List[Document]) -> List[Document]:
        """切分文档并保留元数据"""
        chunks = self.split_documents(documents)
        # 给每个chunk添加序号
        source_counter = {}
        for chunk in chunks:
            source = chunk.metadata.get("source", "unknown")
            source_counter[source] = source_counter.get(source, 0) + 1
            chunk.metadata["chunk_index"] = source_counter[source]
            chunk.metadata["chunk_total"] = sum(
                1 for d in documents if d.metadata.get("source") == source
            )
        return chunks
