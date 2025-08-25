"""
嵌入器模組 - 將文字轉換為向量表示
"""

import os
from typing import List
import openai


class EmbeddingProvider:
    """
    嵌入模型提供者的基礎類別，定義基本介面
    """

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        將文字列表轉換為向量表示

        Args:
            texts: 要嵌入的文字列表

        Returns:
            List[List[float]]: 嵌入向量列表
        """
        raise NotImplementedError("子類必須實作此方法")


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    使用 OpenAI API 的嵌入提供者
    """

    def __init__(
        self, model_name: str = "text-embedding-3-small", batch_size: int = 1000
    ):
        """
        初始化 OpenAI 嵌入提供者

        Args:
            model_name: 使用的 OpenAI 嵌入模型名稱
            batch_size: 每批處理的最大文本數量
        """
        super().__init__()
        self.model_name = model_name
        self.batch_size = batch_size

        # 初始化 OpenAI 客戶端
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("未設定 OPENAI_API_KEY 環境變數")

        self.client = openai.OpenAI(api_key=api_key)

    def _create_embedding_batch(self, texts: List[str]) -> List[List[float]]:
        """
        為一批文字建立嵌入
        """
        try:
            response = self.client.embeddings.create(model=self.model_name, input=texts)
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"嵌入批次時發生錯誤: {e}")
            raise

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        將文字列表轉換為向量表示，處理批次限制

        Args:
            texts: 要嵌入的文字列表

        Returns:
            List[List[float]]: 嵌入向量列表
        """
        if not texts:
            return []

        all_embeddings = []

        # 分批處理文字
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_embeddings = self._create_embedding_batch(batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings
