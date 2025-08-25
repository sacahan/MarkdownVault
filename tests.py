"""
測試模組 - 單元測試檔案
"""

from src.text_splitter import TextSplitter
from src.file_processor import FileProcessor


class TestTextSplitter:
    """
    切分器單元測試
    """

    def test_split_text_empty(self):
        """測試空字串"""
        splitter = TextSplitter()
        result = splitter.split_text("")
        assert result == []

    def test_split_text_smaller_than_chunk(self):
        """測試小於 chunk_size 的文字"""
        splitter = TextSplitter(chunk_size=1000, chunk_overlap=200)
        text = "This is a short text"
        result = splitter.split_text(text)
        assert len(result) == 1
        assert result[0]["text"] == text
        assert result[0]["start"] == 0
        assert result[0]["end"] == len(text)

    def test_split_text_exact_chunk_size(self):
        """測試剛好等於 chunk_size 的文字"""
        chunk_size = 20
        splitter = TextSplitter(chunk_size=chunk_size, chunk_overlap=5)
        text = "x" * chunk_size  # 長度剛好 20
        result = splitter.split_text(text)
        assert len(result) == 1
        assert len(result[0]["text"]) == chunk_size

    def test_split_text_with_overlap(self):
        """測試切分與重疊"""
        splitter = TextSplitter(chunk_size=10, chunk_overlap=3)
        text = "0123456789ABCDEFGHIJ"  # 長度 20
        result = splitter.split_text(text)
        assert len(result) == 3
        assert result[0]["text"] == "0123456789"
        assert result[1]["text"] == "789ABCDEFG"
        assert result[2]["text"] == "EFGHIJ"

    def test_split_text_with_metadata(self):
        """測試附加 metadata"""
        splitter = TextSplitter()
        text = "This is a test"
        metadata = {"source": "test.md"}
        result = splitter.split_text(text, metadata)
        assert result[0]["source"] == "test.md"

    def test_split_file(self):
        """測試 split_file 方法"""
        splitter = TextSplitter(chunk_size=10, chunk_overlap=0)
        text = "0123456789ABCDEFGHIJ"
        result = splitter.split_file("test.md", text)
        assert len(result) == 2
        assert result[0]["source_filename"] == "test.md"
        assert result[0]["chunk_index"] == 0
        assert result[1]["chunk_index"] == 1


class TestFileProcessor:
    """
    檔案處理器單元測試
    """

    def test_validate_file_valid_md(self):
        """測試有效的 MD 檔案"""
        processor = FileProcessor(allowed_extensions=[".md"], max_file_size_mb=5.0)
        is_valid, _ = processor.validate_file("test.md", 1024)
        assert is_valid

    def test_validate_file_invalid_extension(self):
        """測試無效的副檔名"""
        processor = FileProcessor(allowed_extensions=[".md"], max_file_size_mb=5.0)
        is_valid, error_msg = processor.validate_file("test.txt", 1024)
        assert not is_valid
        assert "不支援的檔案類型" in error_msg

    def test_validate_file_too_large(self):
        """測試超過大小限制"""
        processor = FileProcessor(allowed_extensions=[".md"], max_file_size_mb=1.0)
        # 2MB
        is_valid, error_msg = processor.validate_file("test.md", 2 * 1024 * 1024)
        assert not is_valid
        assert "檔案太大" in error_msg
