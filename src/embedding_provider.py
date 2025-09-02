"""
嵌入模型提供者模組
"""

import os
from typing import List
from openai import OpenAI
from sentence_transformers import SentenceTransformer


class OpenAIEmbeddingProvider:
    """
    使用 OpenAI 的模型來產生嵌入
    """

    def __init__(self, model_name: str = "text-embedding-3-small"):
        """
        初始化 OpenAI 嵌入提供者

        Args:
            model_name: 要使用的模型名稱
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("未設定 OPENAI_API_KEY 環境變數")

        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self.model_identifier = "openai"

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        將多個文字轉換為嵌入向量

        Args:
            texts: 要轉換的文字列表

        Returns:
            List[List[float]]: 嵌入向量列表
        """
        if not texts:
            return []

        try:
            # 將輸入中的換行符替換為空格，OpenAI 建議這樣做
            texts = [text.replace("\n", " ") for text in texts]

            response = self.client.embeddings.create(input=texts, model=self.model_name)

            # 提取嵌入向量
            embeddings = [item.embedding for item in response.data]
            return embeddings
        except Exception as e:
            print(f"產生嵌入時發生錯誤: {e}")
            raise


class SentenceTransformerEmbeddingProvider:
    """
    使用 SentenceTransformer 的本地模型來產生嵌入
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        初始化 SentenceTransformer 嵌入提供者

        Args:
            model_name: 要使用的模型名稱
        """
        self.model = SentenceTransformer(model_name)
        self.model_identifier = "minilm"

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        將多個文字轉換為嵌入向量

        Args:
            texts: 要轉換的文字列表

        Returns:
            List[List[float]]: 嵌入向量列表
        """
        if not texts:
            return []

        try:
            # SentenceTransformer 可以直接處理換行符
            embeddings = self.model.encode(texts, convert_to_tensor=False)
            # 將 numpy array 轉換為 list
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            print(f"產生嵌入時發生錯誤: {e}")
            raise
