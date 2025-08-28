"""
Markdown 清理功能整合測試
"""

import os
import tempfile
from src.file_processor import FileProcessor
from src.text_splitter import TextSplitter


class TestMarkdownCleaningIntegration:
    """Markdown 清理功能整合測試"""

    def create_temp_markdown_file(self, content: str) -> str:
        """創建臨時 Markdown 文件"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            return f.name

    def test_file_processor_with_cleaning_enabled(self):
        """測試啟用清理的 FileProcessor"""
        processor = FileProcessor(
            enable_markdown_cleaning=True, cleaning_strategy="balanced"
        )

        markdown_content = """# 測試文檔

這是一個 **粗體** 和 *斜體* 文字的測試。

- 清單項目 1
- 清單項目 2

> 這是引用文字

```python
def test_function():
    return "test"
```

[連結文字](http://example.com)
"""

        temp_file = self.create_temp_markdown_file(markdown_content)

        try:
            cleaned_content = processor.read_file_content(temp_file)

            # 檢查格式符號被移除
            assert "**" not in cleaned_content
            assert "*" not in cleaned_content or cleaned_content.count("*") == 0
            assert ">" not in cleaned_content
            assert "[" not in cleaned_content
            assert "]" not in cleaned_content
            assert "#" not in cleaned_content

            # 檢查內容被保留
            assert "測試文檔" in cleaned_content
            assert "粗體" in cleaned_content
            assert "斜體" in cleaned_content
            assert "清單項目 1" in cleaned_content
            assert "引用文字" in cleaned_content
            assert "def test_function():" in cleaned_content
            assert "連結文字" in cleaned_content

        finally:
            os.unlink(temp_file)

    def test_file_processor_with_cleaning_disabled(self):
        """測試停用清理的 FileProcessor"""
        processor = FileProcessor(enable_markdown_cleaning=False)

        markdown_content = "# 標題\n**粗體** 文字"
        temp_file = self.create_temp_markdown_file(markdown_content)

        try:
            content = processor.read_file_content(temp_file)

            # 應該保持原始格式
            assert "#" in content
            assert "**" in content
            assert "標題" in content
            assert "粗體" in content

        finally:
            os.unlink(temp_file)

    def test_text_splitting_with_cleaned_content(self):
        """測試清理後內容的文本切分"""
        processor = FileProcessor(
            enable_markdown_cleaning=True, cleaning_strategy="balanced"
        )

        splitter = TextSplitter(chunk_size=50, chunk_overlap=10)

        # 創建一個較長的 Markdown 文檔
        long_markdown = (
            """# 長文檔測試

## 第一段
這是第一段的內容，包含一些 **粗體** 和 *斜體* 文字。

## 第二段
這是第二段的內容，包含 [連結](http://example.com) 和 `代碼`。

## 第三段
這是第三段的內容，用來測試文本切分功能。
"""
            * 3
        )  # 重複內容以確保超過 chunk_size

        temp_file = self.create_temp_markdown_file(long_markdown)

        try:
            cleaned_content = processor.read_file_content(temp_file)
            chunks = splitter.split_file("test.md", cleaned_content)

            # 檢查切分結果
            assert len(chunks) > 1  # 應該被分成多個塊

            for chunk in chunks:
                # 檢查每個塊都不包含 Markdown 格式符號
                text = chunk["text"]
                assert "**" not in text
                assert "*" not in text or text.count("*") == 0
                assert "#" not in text
                assert "[" not in text
                assert "`" not in text

                # 檢查 metadata 正確
                assert chunk["source_filename"] == "test.md"
                assert "chunk_index" in chunk
                assert "start" in chunk
                assert "end" in chunk

        finally:
            os.unlink(temp_file)

    def test_cleaning_preview_functionality(self):
        """測試清理預覽功能"""
        processor = FileProcessor(
            enable_markdown_cleaning=True, cleaning_strategy="aggressive"
        )

        markdown_content = """# 標題

**粗體** *斜體* `代碼` [連結](url) ![圖片](img.png)

- 清單項目
- 另一項目

> 引用文字

~~刪除線~~ ==高亮=="""

        preview = processor.get_cleaning_preview(markdown_content, max_length=100)

        # 檢查預覽結構
        assert "original_preview" in preview
        assert "cleaned_preview" in preview
        assert "stats" in preview

        # 檢查統計信息
        stats = preview["stats"]
        assert stats["original_length"] > 0
        assert stats["cleaned_length"] > 0
        assert stats["reduction_ratio"] > 0  # 應該有縮減

        # 檢查預覽長度
        assert len(preview["original_preview"]) <= 103  # 100 + "..."
        assert len(preview["cleaned_preview"]) <= 103

    def test_different_cleaning_strategies_integration(self):
        """測試不同清理策略的整合效果"""
        markdown_content = """# 測試

**粗體** [連結](url) `代碼` ~~刪除~~"""

        strategies = ["conservative", "balanced", "aggressive"]
        results = {}

        for strategy in strategies:
            processor = FileProcessor(
                enable_markdown_cleaning=True, cleaning_strategy=strategy
            )

            temp_file = self.create_temp_markdown_file(markdown_content)

            try:
                cleaned = processor.read_file_content(temp_file)
                results[strategy] = cleaned
            finally:
                os.unlink(temp_file)

        # 檢查策略效果差異
        # 保守策略應該保留較多格式
        # 積極策略應該清理得最徹底

        # 所有策略都應該保留核心內容
        for strategy, content in results.items():
            assert "測試" in content
            assert "粗體" in content
            assert "連結" in content
            assert "代碼" in content
            assert "刪除" in content

    def test_code_blocks_preservation_options(self):
        """測試代碼塊保留選項"""
        markdown_with_code = """# 文檔

普通文字

```python
def hello():
    print("Hello World")
    return True
```

更多文字"""

        # 測試保留代碼塊
        processor_preserve = FileProcessor(
            enable_markdown_cleaning=True, preserve_code_blocks=True
        )

        temp_file = self.create_temp_markdown_file(markdown_with_code)

        try:
            content_preserve = processor_preserve.read_file_content(temp_file)

            # 應該保留代碼內容
            assert "def hello():" in content_preserve
            assert 'print("Hello World")' in content_preserve
            assert "return True" in content_preserve

            # 但不應該有格式標記
            assert "```" not in content_preserve
            assert "python" not in content_preserve  # 語言標記應該被移除

        finally:
            os.unlink(temp_file)

        # 測試不保留代碼塊
        processor_no_preserve = FileProcessor(
            enable_markdown_cleaning=True, preserve_code_blocks=False
        )

        temp_file = self.create_temp_markdown_file(markdown_with_code)

        try:
            content_no_preserve = processor_no_preserve.read_file_content(temp_file)

            # 不應該有代碼內容
            assert "def hello():" not in content_no_preserve
            assert 'print("Hello World")' not in content_no_preserve

            # 但應該有其他內容
            assert "文檔" in content_no_preserve
            assert "普通文字" in content_no_preserve
            assert "更多文字" in content_no_preserve

        finally:
            os.unlink(temp_file)

    def test_headings_as_context_options(self):
        """測試標題作為上下文選項"""
        markdown_with_headings = """# 主標題

段落內容

## 子標題

更多內容

### 小標題

最後內容"""

        # 測試保留標題作為上下文
        processor_context = FileProcessor(
            enable_markdown_cleaning=True, preserve_headings_as_context=True
        )

        temp_file = self.create_temp_markdown_file(markdown_with_headings)

        try:
            content_context = processor_context.read_file_content(temp_file)

            # 應該保留標題文字
            assert "主標題" in content_context
            assert "子標題" in content_context
            assert "小標題" in content_context

            # 不應該有標題標記
            assert "#" not in content_context

        finally:
            os.unlink(temp_file)

    def test_end_to_end_with_mock_vector_operations(self):
        """測試端對端流程（不包含實際向量操作）"""
        markdown_content = """# API 文檔

## 簡介

這個 API 提供 **強大** 的功能來處理數據。

### 特性

- *快速* 處理
- `簡單` 集成
- [詳細文檔](http://docs.example.com)

### 代碼示例

```python
import api_client

client = api_client.Client()
result = client.process_data(data)
```

> 注意：請確保正確設置 API 密鑰。

---

## 結論

這個 API 是 ~~舊系統~~ 的 ==完美== 替代方案。"""

        # 創建 FileProcessor 和 TextSplitter
        processor = FileProcessor(
            enable_markdown_cleaning=True,
            cleaning_strategy="balanced",
            preserve_code_blocks=True,
            preserve_headings_as_context=True,
        )

        splitter = TextSplitter(chunk_size=200, chunk_overlap=50)

        temp_file = self.create_temp_markdown_file(markdown_content)

        try:
            # 模擬完整處理流程
            # 1. 讀取和清理內容
            cleaned_content = processor.read_file_content(temp_file)

            # 2. 切分文本
            chunks = splitter.split_file("api_doc.md", cleaned_content)

            # 3. 驗證結果
            assert len(chunks) > 0

            # 檢查所有塊都被正確清理
            for chunk in chunks:
                text = chunk["text"]

                # 檢查格式符號被移除
                assert "**" not in text
                assert "*" not in text or text.count("*") == 0
                assert "#" not in text
                assert "[" not in text
                assert ">" not in text
                assert "---" not in text
                assert "~~" not in text
                assert "==" not in text

            # 檢查重要內容是否保留在某些塊中
            all_text = " ".join([chunk["text"] for chunk in chunks])

            assert "API 文檔" in all_text
            assert "簡介" in all_text
            assert "強大" in all_text
            assert "快速" in all_text
            assert "簡單" in all_text
            assert "詳細文檔" in all_text
            assert "import api_client" in all_text
            assert "注意" in all_text
            assert "結論" in all_text
            assert "舊系統" in all_text
            assert "完美" in all_text

        finally:
            os.unlink(temp_file)
