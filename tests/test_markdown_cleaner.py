"""
Markdown 清理器測試模組
"""

from src.markdown_cleaner import MarkdownCleaner, CleaningStrategy


class TestMarkdownCleaner:
    """MarkdownCleaner 單元測試"""

    def test_basic_initialization(self):
        """測試基本初始化"""
        cleaner = MarkdownCleaner()
        assert cleaner.strategy == CleaningStrategy.BALANCED
        assert cleaner.preserve_code_blocks is True
        assert cleaner.preserve_headings_as_context is True

    def test_custom_initialization(self):
        """測試自定義初始化"""
        cleaner = MarkdownCleaner(
            strategy=CleaningStrategy.AGGRESSIVE,
            preserve_code_blocks=False,
            preserve_headings_as_context=False,
        )
        assert cleaner.strategy == CleaningStrategy.AGGRESSIVE
        assert cleaner.preserve_code_blocks is False
        assert cleaner.preserve_headings_as_context is False

    def test_empty_content(self):
        """測試空內容"""
        cleaner = MarkdownCleaner()
        assert cleaner.clean_content("") == ""
        assert cleaner.clean_content("   ") == ""
        assert cleaner.clean_content(None) == ""

    def test_conservative_strategy_bold_italic(self):
        """測試保守策略 - 粗體和斜體"""
        cleaner = MarkdownCleaner(strategy=CleaningStrategy.CONSERVATIVE)

        # 粗體
        result = cleaner.clean_content("這是 **粗體** 文字")
        assert "**" not in result
        assert "粗體" in result

        # 斜體
        result = cleaner.clean_content("這是 *斜體* 文字")
        assert "*" not in result or result.count("*") == 0
        assert "斜體" in result

        # 行內代碼
        result = cleaner.clean_content("這是 `代碼` 片段")
        assert "`" not in result
        assert "代碼" in result

    def test_conservative_strategy_preserves_links(self):
        """測試保守策略保留連結格式"""
        cleaner = MarkdownCleaner(strategy=CleaningStrategy.CONSERVATIVE)

        # 保守策略應該保留較複雜的格式
        text = "查看 [連結文字](http://example.com) 了解更多"
        result = cleaner.clean_content(text)
        # 保守策略可能仍包含一些格式，這裡主要測試不會完全破壞內容
        assert "連結文字" in result

    def test_balanced_strategy_links(self):
        """測試平衡策略 - 連結處理"""
        cleaner = MarkdownCleaner(strategy=CleaningStrategy.BALANCED)

        # Markdown 連結
        result = cleaner.clean_content("查看 [連結文字](http://example.com) 了解更多")
        assert "[" not in result
        assert "]" not in result
        assert "(" not in result
        assert ")" not in result
        assert "連結文字" in result
        assert "example.com" not in result

        # 參考連結
        result = cleaner.clean_content("查看 [連結文字][ref] 了解更多")
        assert "連結文字" in result
        assert "[ref]" not in result

    def test_balanced_strategy_images(self):
        """測試平衡策略 - 圖片處理"""
        cleaner = MarkdownCleaner(strategy=CleaningStrategy.BALANCED)

        result = cleaner.clean_content("這是圖片 ![替代文字](image.png) 描述")
        assert "!" not in result
        assert "替代文字" in result
        assert "image.png" not in result

    def test_balanced_strategy_quotes_and_lists(self):
        """測試平衡策略 - 引用和清單"""
        cleaner = MarkdownCleaner(strategy=CleaningStrategy.BALANCED)

        # 引用
        result = cleaner.clean_content("> 這是引用文字")
        assert ">" not in result
        assert "這是引用文字" in result

        # 無序清單
        result = cleaner.clean_content("- 項目一\n* 項目二\n+ 項目三")
        assert "-" not in result or result.count("-") == 0
        assert "*" not in result or result.count("*") == 0
        assert "+" not in result
        assert "項目一" in result
        assert "項目二" in result
        assert "項目三" in result

        # 有序清單
        result = cleaner.clean_content("1. 第一項\n2. 第二項")
        assert "1." not in result
        assert "2." not in result
        assert "第一項" in result
        assert "第二項" in result

    def test_aggressive_strategy(self):
        """測試積極策略"""
        cleaner = MarkdownCleaner(strategy=CleaningStrategy.AGGRESSIVE)

        text = "# 標題\n~~刪除線~~ ==高亮== ^上標^ ~下標~"
        result = cleaner.clean_content(text)

        assert "~~" not in result
        assert "==" not in result
        assert "^" not in result or result.count("^") == 0
        assert "~" not in result or result.count("~") == 0
        assert "#" not in result

        assert "標題" in result
        assert "刪除線" in result
        assert "高亮" in result
        assert "上標" in result
        assert "下標" in result

    def test_horizontal_rules(self):
        """測試水平線處理"""
        cleaner = MarkdownCleaner()

        test_cases = [
            "---",
            "===",
            "***",
            "----",
            "======",
        ]

        for hr in test_cases:
            result = cleaner.clean_content(f"文字前\n{hr}\n文字後")
            assert hr not in result
            assert "文字前" in result
            assert "文字後" in result

    def test_table_handling(self):
        """測試表格處理"""
        cleaner = MarkdownCleaner()

        table = """| 欄位1 | 欄位2 | 欄位3 |
|-------|-------|-------|
| 值1   | 值2   | 值3   |"""

        result = cleaner.clean_content(table)

        assert "|" not in result
        assert "-------" not in result
        assert "欄位1" in result
        assert "欄位2" in result
        assert "值1" in result
        assert "值2" in result

    def test_headings_preservation(self):
        """測試標題保留"""
        cleaner = MarkdownCleaner(preserve_headings_as_context=True)

        text = """# 主標題
## 子標題
### 小標題
普通文字"""

        result = cleaner.clean_content(text)

        assert "#" not in result
        assert "主標題" in result
        assert "子標題" in result
        assert "小標題" in result
        assert "普通文字" in result

    def test_headings_removal(self):
        """測試標題移除標記"""
        cleaner = MarkdownCleaner(preserve_headings_as_context=False)

        text = "# 主標題\n普通文字"
        result = cleaner.clean_content(text)

        assert "#" not in result
        assert "主標題" in result
        assert "普通文字" in result

    def test_code_blocks_preservation(self):
        """測試代碼塊保留"""
        cleaner = MarkdownCleaner(preserve_code_blocks=True)

        text = """```python
def hello():
    print("Hello")
```"""

        result = cleaner.clean_content(text)

        assert "```" not in result
        assert "python" not in result  # 語言標記應該被移除
        assert "def hello():" in result
        assert 'print("Hello")' in result

    def test_code_blocks_removal(self):
        """測試代碼塊移除"""
        cleaner = MarkdownCleaner(preserve_code_blocks=False)

        text = """文字前
```python
def hello():
    print("Hello")
```
文字後"""

        result = cleaner.clean_content(text)

        assert "```" not in result
        assert "def hello():" not in result
        assert "文字前" in result
        assert "文字後" in result

    def test_inline_code_handling(self):
        """測試行內代碼處理"""
        cleaner = MarkdownCleaner()

        text = "使用 `print()` 函數輸出"
        result = cleaner.clean_content(text)

        assert "`" not in result
        assert "print()" in result
        assert "函數輸出" in result

    def test_custom_patterns(self):
        """測試自定義模式"""
        custom_patterns = {r"\[TODO\]": "[待辦]", r"\[DONE\]": "[完成]"}

        cleaner = MarkdownCleaner(custom_patterns=custom_patterns)

        text = "[TODO] 完成測試 [DONE] 寫文檔"
        result = cleaner.clean_content(text)

        assert "[TODO]" not in result
        assert "[DONE]" not in result
        assert "[待辦]" in result
        assert "[完成]" in result

    def test_multiple_blank_lines(self):
        """測試多餘空行處理"""
        cleaner = MarkdownCleaner()

        text = """段落一


段落二



段落三"""

        result = cleaner.clean_content(text)

        # 應該保留段落結構但清理多餘空行
        lines = result.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        assert "段落一" in non_empty_lines
        assert "段落二" in non_empty_lines
        assert "段落三" in non_empty_lines
        assert len(non_empty_lines) == 3

    def test_cleaning_stats(self):
        """測試清理統計"""
        cleaner = MarkdownCleaner()

        original = "# 標題\n**粗體** 和 *斜體* 文字"
        cleaned = cleaner.clean_content(original)
        stats = cleaner.get_cleaning_stats(original, cleaned)

        assert stats["original_length"] == len(original)
        assert stats["cleaned_length"] == len(cleaned)
        assert 0 <= stats["reduction_ratio"] <= 1
        assert stats["original_lines"] >= 1
        assert stats["cleaned_lines"] >= 1

    def test_preview_cleaning(self):
        """測試清理預覽"""
        cleaner = MarkdownCleaner()

        content = "# 標題\n**粗體** 文字 " * 100  # 創建長內容
        preview = cleaner.preview_cleaning(content, max_length=50)

        assert "original_preview" in preview
        assert "cleaned_preview" in preview
        assert "stats" in preview
        assert len(preview["original_preview"]) <= 53  # 50 + "..."
        assert len(preview["cleaned_preview"]) <= 53

    def test_complex_markdown_document(self):
        """測試複雜 Markdown 文檔"""
        cleaner = MarkdownCleaner()

        complex_doc = """# 主標題

這是一個包含多種格式的文檔。

## 子標題

- 清單項目 **粗體**
- 另一個項目 *斜體*
- 第三項 `代碼`

> 這是引用文字
> 多行引用

### 表格示例

| 名稱 | 年齡 | 職業 |
|------|------|------|
| 張三 | 25   | 工程師 |

```python
def example():
    return "Hello World"
```

[連結文字](http://example.com)

---

![圖片](image.png)

~~刪除文字~~ ==高亮文字=="""

        result = cleaner.clean_content(complex_doc)

        # 檢查內容是否被保留
        assert "主標題" in result
        assert "子標題" in result
        assert "清單項目" in result
        assert "粗體" in result
        assert "斜體" in result
        assert "代碼" in result
        assert "引用文字" in result
        assert "張三" in result
        assert "工程師" in result
        assert "連結文字" in result
        assert "刪除文字" in result
        assert "高亮文字" in result

        # 檢查格式符號是否被移除
        assert "**" not in result
        assert "*" not in result or result.count("*") == 0
        assert "`" not in result
        assert ">" not in result
        assert "|" not in result
        assert "---" not in result
        assert "~~" not in result
        assert "==" not in result
        assert "[" not in result
        assert "]" not in result
        assert "(" not in result
        assert ")" not in result
