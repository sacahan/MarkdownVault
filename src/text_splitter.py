"""
切分器模組 - 負責將 Markdown 文件切分為小片段
"""

from typing import List, Dict, Any, Optional


class TextSplitter:
    """
    Markdown 文件切分器：將文字以字元為基礎進行切分，處理 overlap
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        初始化切分器

        Args:
            chunk_size: 每個切片的最大字元數 (預設 1000)
            chunk_overlap: 每個切片的重疊字元數 (預設 200)
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size 必須是正整數")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap 必須是非負整數")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必須小於 chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(
        self, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        將文字切分為多個片段，每個片段包含原始文字與位置資訊

        Args:
            text: 要切分的文字
            metadata: 可選的額外 metadata，會被加到每個片段中

        Returns:
            List[Dict]: 切分後的片段列表，每個片段為字典:
                {
                    "text": 片段文字,
                    "start": 在原文中的開始位置,
                    "end": 在原文中的結束位置,
                    **metadata  # 其他 metadata (如果有提供)
                }
        """
        if not text:
            return []

        # 初始化返回列表
        chunks = []
        # 文字總長度
        text_len = len(text)

        # 起始位置
        start = 0

        while start < text_len:
            # 計算結束位置
            end = min(start + self.chunk_size, text_len)

            # 建立當前片段
            chunk = {"text": text[start:end], "start": start, "end": end}

            # 添加額外 metadata (如果有)
            if metadata:
                chunk.update(metadata)

            chunks.append(chunk)

            # 移動起始位置 (考慮 overlap)
            start = end - self.chunk_overlap

            # 確保 start 不會小於 0 或卡在原地
            if start <= 0 or start >= text_len or start == (end - self.chunk_overlap):
                start = end

        return chunks

    def split_file(self, file_path: str, file_content: str) -> List[Dict[str, Any]]:
        """
        切分檔案內容並加入檔案相關 metadata

        Args:
            file_path: 檔案路徑
            file_content: 檔案內容

        Returns:
            List[Dict]: 切分後的片段列表，每個片段包含檔案資訊
        """
        # 建立檔案 metadata
        metadata = {"source_filename": file_path}

        # 切分文字
        chunks = self.split_text(file_content, metadata)

        # 添加片段索引
        for i, chunk in enumerate(chunks):
            chunk["chunk_index"] = i

        return chunks
