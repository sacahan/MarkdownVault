"""
Markdown 文件向量化服務示例
"""

import os
from dotenv import load_dotenv
from src.text_splitter import TextSplitter
from src.embedding_provider import OpenAIEmbeddingProvider
from src.vector_database import VectorDatabase
from src.file_processor import FileProcessor

# 載入環境變數
load_dotenv()


def main():
    """
    示範如何使用 API 進行文件處理與搜尋
    """
    # 初始化元件
    splitter = TextSplitter(
        chunk_size=int(os.getenv("DEFAULT_CHUNK_SIZE", "1000")),
        chunk_overlap=int(os.getenv("DEFAULT_CHUNK_OVERLAP", "200")),
    )
    embedding_provider = OpenAIEmbeddingProvider(
        model_name=os.getenv("MODEL_NAME", "text-embedding-3-small")
    )
    db = VectorDatabase(
        persist_directory=os.getenv("CHROMA_DB_DIRECTORY", "./chroma_db"),
        collection_name=os.getenv("COLLECTION_NAME", "markdown_documents"),
    )
    file_processor = FileProcessor(
        max_file_size_mb=float(os.getenv("MAX_FILE_SIZE_MB", "5.0"))
    )

    # 建立測試 Markdown
    demo_markdown = """# 向量化測試文件

## 簡介

這是一個示範如何處理 Markdown 文件的範例。
可以用來測試向量化流程與檢索功能。

## 功能

1. 文件切分
2. 向量化
3. 存儲
4. 檢索

## 結論

向量資料庫為文件提供了語意搜尋能力。
    """

    # 寫入臨時檔案
    temp_file_path = "example.md"
    with open(temp_file_path, "w", encoding="utf-8") as f:
        f.write(demo_markdown)

    try:
        print("步驟 1: 處理 Markdown 檔案")

        # 讀取檔案
        content = file_processor.read_file_content(temp_file_path)
        if not content:
            print("無法讀取檔案")
            return

        print(f"成功讀取檔案: {temp_file_path}, 大小: {len(content)} 字元")

        # 切分文件
        chunks = splitter.split_file(temp_file_path, content)
        print(f"將文件切分為 {len(chunks)} 個片段")

        # 向量化
        texts = [chunk["text"] for chunk in chunks]
        print("產生嵌入向量...")
        embeddings = embedding_provider.embed_texts(texts)
        print(f"成功產生 {len(embeddings)} 個向量")

        # 儲存到向量資料庫
        print("儲存到向量資料庫...")
        db.add_documents(chunks, embeddings)
        print("完成儲存")

        # 查詢
        print("\n步驟 2: 執行語意搜尋")

        query = "文件如何切分"
        print(f"查詢: '{query}'")

        # 生成查詢向量
        query_embedding = embedding_provider.embed_texts([query])[0]

        # 搜尋
        results = db.search(query_embedding, top_k=2)

        # 顯示結果
        print(f"找到 {len(results)} 個結果:")
        for i, result in enumerate(results):
            print(f"\n結果 {i+1}: (分數: {result['score']:.4f})")
            print(f"來源: {result['metadata']['source_filename']}")
            print(f"片段: {result['text']}")

        # 列出檔案
        print("\n步驟 3: 管理文件")
        files = db.list_documents()
        print(f"資料庫中的文件: {files}")

        # 刪除
        print(f"刪除文件: {temp_file_path}")
        success = db.delete_document(temp_file_path)
        print(f"刪除{'成功' if success else '失敗'}")

        # 驗證刪除
        files = db.list_documents()
        print(f"刪除後的文件列表: {files}")

    finally:
        # 清理
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"已刪除臨時檔案: {temp_file_path}")


if __name__ == "__main__":
    main()
