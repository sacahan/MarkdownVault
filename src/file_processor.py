"""
檔案處理模組 - 處理 Markdown 檔案的上傳與驗證
"""

import os
from typing import List, Optional, Tuple
from .markdown_cleaner import MarkdownCleaner, CleaningStrategy


class FileProcessor:
    """
    處理文件上傳、驗證與讀取
    """

    def __init__(
        self,
        allowed_extensions: List[str] = [".md"],
        max_file_size_mb: float = 5.0,
        enable_markdown_cleaning: bool = True,
        cleaning_strategy: str = "balanced",
        preserve_code_blocks: bool = True,
        preserve_headings_as_context: bool = True,
    ):
        """
        初始化檔案處理器

        Args:
            allowed_extensions: 允許的副檔名列表
            max_file_size_mb: 單一檔案最大大小 (MB)
            enable_markdown_cleaning: 是否啟用 Markdown 清理
            cleaning_strategy: 清理策略 (conservative/balanced/aggressive)
            preserve_code_blocks: 是否保留代碼塊內容
            preserve_headings_as_context: 是否將標題轉換為上下文文字
        """
        self.allowed_extensions = allowed_extensions
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.enable_markdown_cleaning = enable_markdown_cleaning

        # 初始化 Markdown 清理器
        if self.enable_markdown_cleaning:
            try:
                strategy_enum = CleaningStrategy(cleaning_strategy)
            except ValueError:
                strategy_enum = CleaningStrategy.BALANCED

            self.markdown_cleaner = MarkdownCleaner(
                strategy=strategy_enum,
                preserve_code_blocks=preserve_code_blocks,
                preserve_headings_as_context=preserve_headings_as_context,
            )
        else:
            self.markdown_cleaner = None

    def validate_file(self, file_path: str, file_size: int) -> Tuple[bool, str]:
        """
        驗證檔案是否符合要求

        Args:
            file_path: 檔案路徑
            file_size: 檔案大小 (bytes)

        Returns:
            Tuple[bool, str]: (是否通過驗證, 錯誤訊息)
        """
        # 檢查副檔名
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in self.allowed_extensions:
            return (
                False,
                f"不支援的檔案類型: {ext}。允許的類型: {', '.join(self.allowed_extensions)}",
            )

        # 檢查檔案大小
        if file_size > self.max_file_size_bytes:
            max_size_mb = self.max_file_size_bytes / (1024 * 1024)
            return (
                False,
                f"檔案太大: {file_size / (1024 * 1024):.2f}MB。最大允許: {max_size_mb:.2f}MB",
            )

        return True, ""

    def read_file_content(self, file_path: str) -> Optional[str]:
        """
        讀取檔案內容

        Args:
            file_path: 檔案路徑

        Returns:
            Optional[str]: 檔案內容，如果出錯則為 None
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 如果啟用 Markdown 清理，則處理內容
            if self.enable_markdown_cleaning and self.markdown_cleaner:
                content = self.markdown_cleaner.clean_content(content)

            return content
        except Exception as e:
            print(f"讀取檔案時發生錯誤: {e}")
            return None

    def process_markdown_content(self, content: str) -> str:
        """
        處理 Markdown 內容（可選的額外處理方法）

        Args:
            content: 原始 Markdown 內容

        Returns:
            str: 處理後的內容
        """
        if not content:
            return content

        if self.enable_markdown_cleaning and self.markdown_cleaner:
            return self.markdown_cleaner.clean_content(content)
        else:
            return content

    def get_cleaning_preview(self, content: str, max_length: int = 500) -> dict:
        """
        獲取清理預覽

        Args:
            content: 原始內容
            max_length: 預覽最大長度

        Returns:
            dict: 預覽結果
        """
        if self.enable_markdown_cleaning and self.markdown_cleaner:
            return self.markdown_cleaner.preview_cleaning(content, max_length)
        else:
            return {
                "original_preview": content[:max_length]
                + ("..." if len(content) > max_length else ""),
                "cleaned_preview": content[:max_length]
                + ("..." if len(content) > max_length else ""),
                "stats": {
                    "original_length": len(content),
                    "cleaned_length": len(content),
                    "reduction_ratio": 0,
                    "original_lines": len(content.splitlines()),
                    "cleaned_lines": len(content.splitlines()),
                },
            }
