"""
主要開發文件整合測試，模擬端到端的使用流程
"""

import os
import pytest
from unittest.mock import patch, MagicMock

import tempfile
import shutil


class MockEmbedding:
    """Mock 嵌入向量"""

    def __init__(self, dim=5):
        self.dim = dim

    def generate(self, text_count):
        """生成假向量"""
        import numpy as np

        return [list(np.random.random(self.dim)) for _ in range(text_count)]


def test_text_splitter_integration():
    """測試切分器整合"""
    from src.text_splitter import TextSplitter

    # 建立切分器
    splitter = TextSplitter(chunk_size=50, chunk_overlap=10)

    # 準備測試文件
    test_text = """# 測試文件

這是一份測試 Markdown 文件，用於整合測試。
它包含標題、段落和其他基本元素。

## 第二章節

這是第二個章節的內容。可以用來測試切分功能。
    """

    # 執行切分
    chunks = splitter.split_file("test.md", test_text)

    # 驗證結果
    assert len(chunks) > 1  # 確保有切分
    assert chunks[0]["source_filename"] == "test.md"
    assert chunks[0]["chunk_index"] == 0
    assert "測試文件" in chunks[0]["text"]  # 內容正確


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="需要 OpenAI API 金鑰")
def test_embedding_provider_real():
    """測試真實的嵌入提供者 (需要 API 金鑰)"""
    from src.embedding_provider import OpenAIEmbeddingProvider

    provider = OpenAIEmbeddingProvider()
    result = provider.embed_texts(["這是測試文字"])

    assert len(result) == 1
    assert isinstance(result[0], list)
    assert len(result[0]) > 0  # 有返回向量


def test_embedding_provider_mock():
    """測試模擬的嵌入提供者"""
    from src.embedding_provider import OpenAIEmbeddingProvider

    with patch("openai.OpenAI") as mock_openai:
        # 模擬 API 回應
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3, 0.4, 0.5])]
        mock_client.embeddings.create.return_value = mock_response

        # 使用模擬的提供者
        provider = OpenAIEmbeddingProvider()
        result = provider.embed_texts(["這是測試文字"])

        # 驗證結果
        assert len(result) == 1
        assert result[0] == [0.1, 0.2, 0.3, 0.4, 0.5]


def test_vector_database():
    """測試向量資料庫"""
    from src.vector_database import VectorDatabase

    # 建立臨時目錄
    temp_dir = tempfile.mkdtemp()
    try:
        # 初始化資料庫
        db = VectorDatabase(persist_directory=temp_dir)

        # 準備資料
        chunks = [
            {
                "text": "這是測試文字1",
                "source_filename": "test1.md",
                "chunk_index": 0,
                "start": 0,
                "end": 20,
            },
            {
                "text": "這是測試文字2",
                "source_filename": "test1.md",
                "chunk_index": 1,
                "start": 20,
                "end": 40,
            },
        ]

        # 產生假向量
        mock_embed = MockEmbedding(dim=5)
        embeddings = mock_embed.generate(len(chunks))

        # 添加文件
        ids = db.add_documents(chunks, embeddings)
        assert len(ids) == 2

        # 列出文件
        docs = db.list_documents()
        assert len(docs) == 1
        assert "test1.md" in docs

        # 搜尋
        results = db.search(embeddings[0], top_k=1)
        assert len(results) == 1

        # 刪除
        success = db.delete_document("test1.md")
        assert success

        # 驗證刪除
        docs = db.list_documents()
        assert len(docs) == 0
    finally:
        # 清理
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    # 可以直接執行此文件進行整合測試
    test_text_splitter_integration()
    test_embedding_provider_mock()
    test_vector_database()
    print("整合測試通過！")
