"""
向量資料庫模組 - 使用 Chroma 儲存並檢索向量
"""

import os
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings


class VectorDatabase:
    """
    向量資料庫管理器，使用 Chroma 實作
    """

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "markdown_documents",
    ):
        """
        初始化向量資料庫

        Args:
            persist_directory: Chroma 資料儲存目錄
            collection_name: 集合名稱
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # 確保儲存目錄存在
        os.makedirs(persist_directory, exist_ok=True)

        # 初始化 Chroma 客戶端
        self.client = chromadb.PersistentClient(
            path=persist_directory, settings=Settings(anonymized_telemetry=False)
        )

        # 取得或建立集合
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        """
        取得或建立集合
        """
        try:
            return self.client.get_collection(name=self.collection_name)
        except Exception:
            return self.client.create_collection(name=self.collection_name)

    def add_documents(
        self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]
    ) -> List[str]:
        """
        將文件片段與對應向量加入資料庫

        Args:
            chunks: 文件片段列表，每個包含 text 與 metadata
            embeddings: 對應的嵌入向量列表

        Returns:
            List[str]: 加入的 ID 列表
        """
        if not chunks or not embeddings:
            return []

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"chunks 數量 ({len(chunks)}) 必須等於 embeddings 數量 ({len(embeddings)})"
            )

        # 準備資料
        ids = [f"{chunk['source_filename']}_{chunk['chunk_index']}" for chunk in chunks]
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [
            {
                "source_filename": chunk["source_filename"],
                "chunk_index": chunk["chunk_index"],
                "start": chunk["start"],
                "end": chunk["end"],
            }
            for chunk in chunks
        ]

        # 加入資料庫
        self.collection.add(
            ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas
        )

        return ids

    def search(
        self, query_embedding: List[float], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        根據查詢向量搜尋相似文件

        Args:
            query_embedding: 查詢向量
            top_k: 返回的最大結果數

        Returns:
            List[Dict]: 搜尋結果列表
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        # 整理結果
        formatted_results = []

        if not results["ids"]:
            return []

        for i in range(len(results["ids"][0])):
            # ChromaDB 餘弦距離轉換為相似度分數 (0-1 範圍，1 表示完全相似)
            distance = results["distances"][0][i]
            # ChromaDB 餘弦距離範圍通常是 0-2，需要正確轉換為相似度
            # 相似度 = (2 - distance) / 2，確保範圍在 0-1 之間
            similarity = max(0.0, min(1.0, (2.0 - distance) / 2.0))

            formatted_results.append(
                {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": similarity,
                }
            )

        return formatted_results

    def list_documents(self) -> List[str]:
        """
        列出資料庫中所有的文件名稱

        Returns:
            List[str]: 唯一文件名稱列表
        """
        # 取得所有的 metadata
        all_metadatas = self.collection.get()["metadatas"]

        if not all_metadatas:
            return []

        # 提取唯一的文件名稱
        filenames = set()
        for metadata in all_metadatas:
            if metadata and "source_filename" in metadata:
                filenames.add(metadata["source_filename"])

        return sorted(list(filenames))

    def delete_document(self, filename: str) -> bool:
        """
        刪除指定文件的所有片段

        Args:
            filename: 要刪除的文件名稱

        Returns:
            bool: 是否成功刪除
        """
        try:
            # 使用 where 過濾條件刪除
            self.collection.delete(where={"source_filename": filename})
            return True
        except Exception as e:
            print(f"刪除文件時發生錯誤: {e}")
            return False
