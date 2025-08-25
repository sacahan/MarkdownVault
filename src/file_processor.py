"""
檔案處理模組 - 處理 Markdown 檔案的上傳與驗證
"""

import os
from typing import List, Optional, Tuple


class FileProcessor:
    """
    處理文件上傳、驗證與讀取
    """

    def __init__(
        self, allowed_extensions: List[str] = [".md"], max_file_size_mb: float = 5.0
    ):
        """
        初始化檔案處理器

        Args:
            allowed_extensions: 允許的副檔名列表
            max_file_size_mb: 單一檔案最大大小 (MB)
        """
        self.allowed_extensions = allowed_extensions
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

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
                return f.read()
        except Exception as e:
            print(f"讀取檔案時發生錯誤: {e}")
            return None
