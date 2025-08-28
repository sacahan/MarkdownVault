"""
Markdown 清理模組 - 處理 Markdown 格式符號以優化 RAG 檢索效果
"""

from enum import Enum
from typing import Dict, Optional
import re


class CleaningStrategy(Enum):
    """清理策略枚舉"""

    CONSERVATIVE = "conservative"  # 保守型：僅移除明顯的格式符號
    BALANCED = "balanced"  # 平衡型：移除格式但保留語義結構
    AGGRESSIVE = "aggressive"  # 積極型：最大程度提取純文本


class MarkdownCleaner:
    """
    Markdown 格式清理器

    用於移除 Markdown 格式符號，提升向量嵌入和檢索的準確性
    """

    def __init__(
        self,
        strategy: CleaningStrategy = CleaningStrategy.BALANCED,
        preserve_code_blocks: bool = True,
        preserve_headings_as_context: bool = True,
        custom_patterns: Optional[Dict[str, str]] = None,
    ):
        """
        初始化 Markdown 清理器

        Args:
            strategy: 清理策略
            preserve_code_blocks: 是否保留代碼塊內容
            preserve_headings_as_context: 是否將標題轉換為上下文文字
            custom_patterns: 自定義清理模式 {pattern: replacement}
        """
        self.strategy = strategy
        self.preserve_code_blocks = preserve_code_blocks
        self.preserve_headings_as_context = preserve_headings_as_context
        self.custom_patterns = custom_patterns or {}

        # 初始化清理模式
        self._init_cleaning_patterns()

    def _init_cleaning_patterns(self):
        """初始化各種清理策略的模式"""

        # 基礎清理模式（所有策略都會使用）
        self.base_patterns = {
            # 移除水平線
            r"^-{3,}$": "",
            r"^={3,}$": "",
            r"^\*{3,}$": "",
            # 移除表格分隔符
            r"\|[-:]+\|": "",
            r"^\|.*\|$": lambda m: self._clean_table_row(m.group(0)),
            # 移除多餘空行
            r"\n{3,}": "\n\n",
        }

        # 保守型清理模式
        self.conservative_patterns = {
            **self.base_patterns,
            # 僅移除最明顯的格式符號
            r"\*\*(.*?)\*\*": r"\1",  # 粗體
            r"\*(.*?)\*": r"\1",  # 斜體
            r"`(.*?)`": r"\1",  # 行內代碼
        }

        # 平衡型清理模式
        self.balanced_patterns = {
            **self.conservative_patterns,
            # 清理連結但保留文字
            r"\[([^\]]+)\]\([^)]+\)": r"\1",  # [文字](連結)
            r"\[([^\]]+)\]\[[^\]]*\]": r"\1",  # [文字][引用]
            # 清理圖片但保留替代文字
            r"!\[([^\]]*)\]\([^)]+\)": r"\1",  # ![alt](src)
            # 清理引用標記
            r"^>\s*": "",
            # 清理清單標記
            r"^[\s]*[-*+]\s+": "",
            r"^[\s]*\d+\.\s+": "",
        }

        # 積極型清理模式
        self.aggressive_patterns = {
            **self.balanced_patterns,
            # 更積極的清理
            r"~~(.*?)~~": r"\1",  # 刪除線
            r"==(.*?)==": r"\1",  # 高亮
            r"\^([^)]+)\^": r"\1",  # 上標
            r"~([^)]+)~": r"\1",  # 下標
            # 移除所有剩餘的特殊字符組合
            r"[#*_~`>|]": "",
        }

    def clean_content(self, content: str) -> str:
        """
        清理 Markdown 內容的主要方法

        Args:
            content: 原始 Markdown 內容

        Returns:
            str: 清理後的文本
        """
        if not content or not content.strip():
            return content

        # 預處理
        cleaned_content = self._preprocess_content(content)

        # 根據策略選擇清理模式
        if self.strategy == CleaningStrategy.CONSERVATIVE:
            patterns = self.conservative_patterns
        elif self.strategy == CleaningStrategy.BALANCED:
            patterns = self.balanced_patterns
        else:  # AGGRESSIVE
            patterns = self.aggressive_patterns

        # 應用清理模式
        cleaned_content = self._apply_patterns(cleaned_content, patterns)

        # 應用自定義模式
        cleaned_content = self._apply_patterns(cleaned_content, self.custom_patterns)

        # 後處理
        cleaned_content = self._postprocess_content(cleaned_content)

        return cleaned_content

    def _preprocess_content(self, content: str) -> str:
        """預處理內容"""

        # 處理代碼塊
        if self.preserve_code_blocks:
            # 保留代碼塊內容，但移除標記
            content = re.sub(r"```[\w]*\n(.*?)\n```", r"\1", content, flags=re.DOTALL)
            content = re.sub(r"`([^`]+)`", r"\1", content)
        else:
            # 移除代碼塊
            content = re.sub(r"```[\w]*\n.*?\n```", "", content, flags=re.DOTALL)

        # 處理標題
        if self.preserve_headings_as_context:
            # 將標題轉換為普通文本
            content = re.sub(r"^#{1,6}\s+(.*)$", r"\1", content, flags=re.MULTILINE)
        else:
            # 移除標題標記但保留文字
            content = re.sub(r"^#{1,6}\s+", "", content, flags=re.MULTILINE)

        return content

    def _apply_patterns(self, content: str, patterns: Dict[str, str]) -> str:
        """應用清理模式"""
        for pattern, replacement in patterns.items():
            if callable(replacement):
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            else:
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        return content

    def _clean_table_row(self, row: str) -> str:
        """清理表格行"""
        # 移除表格邊框，保留內容
        row = row.strip("|")
        cells = [cell.strip() for cell in row.split("|")]
        return " ".join(filter(None, cells))

    def _postprocess_content(self, content: str) -> str:
        """後處理內容"""

        # 清理多餘的空白
        content = re.sub(r"\s+", " ", content)
        content = re.sub(r"\n\s*\n", "\n\n", content)

        # 移除行首行尾空白
        lines = []
        for line in content.split("\n"):
            line = line.strip()
            if line:  # 只保留非空行
                lines.append(line)

        content = "\n".join(lines)

        return content.strip()

    def get_cleaning_stats(self, original: str, cleaned: str) -> Dict[str, int]:
        """
        獲取清理統計信息

        Args:
            original: 原始內容
            cleaned: 清理後內容

        Returns:
            Dict: 統計信息
        """
        return {
            "original_length": len(original),
            "cleaned_length": len(cleaned),
            "reduction_ratio": 1 - (len(cleaned) / len(original)) if original else 0,
            "original_lines": len(original.splitlines()),
            "cleaned_lines": len(cleaned.splitlines()),
        }

    def preview_cleaning(self, content: str, max_length: int = 500) -> Dict[str, str]:
        """
        預覽清理效果

        Args:
            content: 原始內容
            max_length: 預覽最大長度

        Returns:
            Dict: 包含原始和清理後的預覽
        """
        cleaned = self.clean_content(content)

        return {
            "original_preview": content[:max_length]
            + ("..." if len(content) > max_length else ""),
            "cleaned_preview": cleaned[:max_length]
            + ("..." if len(cleaned) > max_length else ""),
            "stats": self.get_cleaning_stats(content, cleaned),
        }
