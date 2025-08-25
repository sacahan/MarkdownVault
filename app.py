"""
應用程式主模組 - 使用 Gradio 實作 UI 介面
"""

import os
from dotenv import load_dotenv
import gradio as gr
from typing import List, Dict, Any

from src.text_splitter import TextSplitter
from src.embedding_provider import OpenAIEmbeddingProvider
from src.vector_database import VectorDatabase
from src.file_processor import FileProcessor

# 預設設定
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_TOP_K = 10
DEFAULT_MODEL = "text-embedding-3-small"


class MarkdownVectorApp:
    """
    Markdown 文件向量化應用程式
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        model_name: str = DEFAULT_MODEL,
        db_directory: str = "./chroma_db",
        collection_name: str = "markdown_documents",
        max_file_size_mb: float = 5.0,
    ):
        """
        初始化應用程式

        Args:
            chunk_size: 切分大小
            chunk_overlap: 切分重疊
            model_name: 嵌入模型名稱
            db_directory: 資料庫目錄
            collection_name: 集合名稱
            max_file_size_mb: 單一檔案大小上限 (MB)
        """
        # 初始化元件
        self.text_splitter = TextSplitter(chunk_size, chunk_overlap)
        self.embedding_provider = OpenAIEmbeddingProvider(model_name)
        self.vector_db = VectorDatabase(db_directory, collection_name)
        self.file_processor = FileProcessor(max_file_size_mb=max_file_size_mb)

    def process_files(
        self, files: List, chunk_size: int, chunk_overlap: int
    ) -> Dict[str, Any]:
        """
        處理上傳的檔案

        Args:
            files: 上傳的檔案列表
            chunk_size: 切分大小
            chunk_overlap: 切分重疊

        Returns:
            Dict: 處理結果
        """
        if not files:
            return {"status": "error", "message": "未提供檔案", "ingested_files": []}

        # 更新切分器設定
        self.text_splitter = TextSplitter(chunk_size, chunk_overlap)

        successful_files = []
        failed_files = []
        total_chunks = 0

        for file in files:
            # 獲取檔案資訊
            file_path = file.name
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)

            # 驗證檔案
            is_valid, error_msg = self.file_processor.validate_file(
                file_path, file_size
            )
            if not is_valid:
                failed_files.append({"filename": file_name, "reason": error_msg})
                continue

            # 讀取檔案內容
            content = self.file_processor.read_file_content(file_path)
            if content is None:
                failed_files.append(
                    {"filename": file_name, "reason": "無法讀取檔案內容"}
                )
                continue

            # 切分文件
            chunks = self.text_splitter.split_file(file_name, content)
            if not chunks:
                failed_files.append(
                    {"filename": file_name, "reason": "檔案內容為空或切分失敗"}
                )
                continue

            # 獲取文字列表進行嵌入
            texts = [chunk["text"] for chunk in chunks]

            try:
                # 產生嵌入
                embeddings = self.embedding_provider.embed_texts(texts)

                # 儲存到向量資料庫
                self.vector_db.add_documents(chunks, embeddings)

                successful_files.append(file_name)
                total_chunks += len(chunks)
            except Exception as e:
                failed_files.append(
                    {"filename": file_name, "reason": f"處理時發生錯誤: {str(e)}"}
                )

        return {
            "status": "success" if successful_files else "error",
            "message": f"成功處理 {len(successful_files)} 個檔案，總計 {total_chunks} 個片段",
            "ingested_files": successful_files,
            "failed_files": failed_files,
        }

    def search_documents(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        搜尋文件

        Args:
            query: 查詢文字
            top_k: 返回數量

        Returns:
            List[Dict]: 搜尋結果
        """
        if not query:
            return []

        try:
            # 產生查詢向量
            query_embedding = self.embedding_provider.embed_texts([query])[0]

            # 搜尋向量資料庫
            results = self.vector_db.search(query_embedding, top_k)

            # 格式化結果
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "score": f"{result['score']:.4f}",
                        "filename": result["metadata"]["source_filename"],
                        "chunk_index": result["metadata"]["chunk_index"],
                        "start": result["metadata"]["start"],
                        "end": result["metadata"]["end"],
                        "text": result["text"],
                    }
                )

            return formatted_results
        except Exception as e:
            print(f"搜尋時發生錯誤: {e}")
            return []

    def list_documents(self) -> List[str]:
        """
        列出已儲存的文件

        Returns:
            List[str]: 文件列表
        """
        return self.vector_db.list_documents()

    def delete_document(self, filename: str) -> Dict[str, Any]:
        """
        刪除文件

        Args:
            filename: 要刪除的文件名稱

        Returns:
            Dict: 處理結果
        """
        if not filename:
            return {"status": "error", "message": "未提供檔案名稱"}

        success = self.vector_db.delete_document(filename)

        if success:
            return {"status": "success", "message": f"成功刪除文件: {filename}"}
        else:
            return {"status": "error", "message": f"刪除文件時發生錯誤: {filename}"}


def create_ui(app: MarkdownVectorApp):
    """
    建立 Gradio UI 介面

    Args:
        app: MarkdownVectorApp 實例
    """

    with gr.Blocks(
        title="Markdown 文件向量化服務",
        theme=gr.themes.Default(),
        analytics_enabled=False,
        mode="simple",
    ) as interface:
        gr.Markdown("# Markdown 文件向量化服務")
        gr.Markdown("上傳、向量化、搜尋 Markdown 文件")

        with gr.Tabs():
            # 上傳頁簽
            with gr.TabItem("上傳文件"):
                with gr.Row():
                    with gr.Column():
                        upload_files = gr.File(
                            label="上傳 Markdown 檔案",
                            file_types=[".md"],
                            file_count="multiple",
                        )
                        with gr.Row():
                            chunk_size = gr.Slider(
                                label="Chunk Size",
                                minimum=100,
                                maximum=2000,
                                value=DEFAULT_CHUNK_SIZE,
                                step=100,
                            )
                            chunk_overlap = gr.Slider(
                                label="Chunk Overlap",
                                minimum=0,
                                maximum=500,
                                value=DEFAULT_CHUNK_OVERLAP,
                                step=50,
                            )
                        upload_button = gr.Button("上傳並處理")
                    with gr.Column():
                        upload_output = gr.JSON(label="處理結果")

                upload_button.click(
                    fn=app.process_files,
                    inputs=[upload_files, chunk_size, chunk_overlap],
                    outputs=upload_output,
                )

            # 搜尋頁簽
            with gr.TabItem("搜尋文件"):
                with gr.Row():
                    # 上半部：搜尋輸入區域
                    query_text = gr.Textbox(
                        label="輸入查詢文字",
                        placeholder="輸入要搜尋的文字...",
                        lines=3,
                        scale=3,
                    )

                    top_k = gr.Slider(
                        label="結果數量 (Top K)",
                        minimum=1,
                        maximum=20,
                        value=DEFAULT_TOP_K,
                        step=1,
                        container=True,
                        scale=1,
                    )
                with gr.Row():
                    search_button = gr.Button("搜尋", size="lg")
                    clean_button = gr.Button("清除", size="lg")

                with gr.Row():
                    # 下半部：搜尋結果區域
                    search_output = gr.Dataframe(
                        label="搜尋結果",
                        headers=[
                            "分數",
                            "檔案名稱",
                            "片段索引",
                            "開始位置",
                            "結束位置",
                            "文字內容",
                        ],
                        col_count=(6, "fixed"),
                        interactive=False,
                    )

                # 將搜尋結果轉換為資料框格式
                def format_search_results(query, top_k):
                    results = app.search_documents(query, top_k)
                    if not results:
                        return []

                    # 轉換為列表格式
                    formatted_data = []
                    for result in results:
                        formatted_data.append(
                            [
                                result["score"],
                                result["filename"],
                                result["chunk_index"],
                                result["start"],
                                result["end"],
                                result["text"],
                            ]
                        )

                    return formatted_data

                search_button.click(
                    fn=format_search_results,
                    inputs=[query_text, top_k],
                    outputs=search_output,
                    api_name="search",
                )

                # 清除搜尋結果 callback
                def clear_search():
                    return "", []

                clean_button.click(
                    fn=clear_search,
                    inputs=None,
                    outputs=[query_text, search_output],
                )

            # 管理頁簽
            with gr.TabItem("文件管理"):
                with gr.Row():
                    with gr.Column():
                        refresh_button = gr.Button("重新整理文件列表")
                        document_list = gr.Dropdown(
                            label="選擇文件",
                            choices=[],
                            interactive=True,
                            allow_custom_value=True,
                        )
                        delete_button = gr.Button("刪除所選文件")
                    with gr.Column():
                        management_output = gr.JSON(label="操作結果")

                def reload_document_list():
                    """
                    更新文件列表
                    """
                    choices = app.list_documents()
                    return gr.Dropdown(
                        choices=choices, value=choices[0] if choices else None
                    )

                def delete_and_update(filename):
                    if not filename:
                        return {"status": "error", "message": "請選擇要刪除的文件"}, []
                    result = app.delete_document(filename)
                    choices = app.list_documents()
                    return result, gr.Dropdown(
                        choices=choices, value=choices[0] if choices else None
                    )

                # 初始化時載入文件列表
                interface.load(
                    fn=reload_document_list, inputs=None, outputs=document_list
                )

                # 重新整理文件列表
                refresh_button.click(
                    fn=reload_document_list,
                    inputs=None,
                    outputs=document_list,
                )

                # 刪除文件
                delete_button.click(
                    fn=delete_and_update,
                    inputs=[document_list],
                    outputs=[management_output, document_list],
                )

    return interface


def main():
    """
    主函數
    """
    # 載入 .env 設定（如果存在）
    load_dotenv()

    # 從環境變數讀取可覆寫的設定
    db_directory = os.getenv("CHROMA_DB_DIRECTORY", "./chroma_db")
    collection_name = os.getenv("COLLECTION_NAME", "markdown_documents")
    try:
        chunk_size = int(os.getenv("DEFAULT_CHUNK_SIZE", str(DEFAULT_CHUNK_SIZE)))
    except ValueError:
        chunk_size = DEFAULT_CHUNK_SIZE
    try:
        chunk_overlap = int(
            os.getenv("DEFAULT_CHUNK_OVERLAP", str(DEFAULT_CHUNK_OVERLAP))
        )
    except ValueError:
        chunk_overlap = DEFAULT_CHUNK_OVERLAP
    model_name = os.getenv("MODEL_NAME", DEFAULT_MODEL)
    try:
        max_file_size_mb = float(os.getenv("MAX_FILE_SIZE_MB", "5.0"))
    except ValueError:
        max_file_size_mb = 5.0

    # 如果 env 指向的資料庫目錄不存在或沒有 chroma 資料，fallback 到 ./chroma_db（專案內預設位置）
    chosen_db_directory = db_directory
    try:
        has_chroma_file = False
        if os.path.isdir(db_directory):
            # 檢查是否有 chroma.sqlite3 或任何檔案存在
            for fname in os.listdir(db_directory):
                if fname.endswith(".sqlite3") or fname.endswith(".db"):
                    has_chroma_file = True
                    break
    except Exception:
        has_chroma_file = False

    if not has_chroma_file:
        alt = "./chroma_db"
        if os.path.isdir(alt):
            chosen_db_directory = alt
            print(
                f"CHROMA_DB_DIRECTORY '{db_directory}' empty/missing — falling back to '{alt}'"
            )
        else:
            # 否則仍使用原本設定（資料夾會在 VectorDatabase 建構時建立）
            chosen_db_directory = db_directory

    # 初始化應用程式
    app = MarkdownVectorApp(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        model_name=model_name,
        db_directory=chosen_db_directory,
        collection_name=collection_name,
        max_file_size_mb=max_file_size_mb,
    )

    # 顯示實際使用的設定（診斷用）
    print(
        f"Using config: CHROMA_DB_DIRECTORY={db_directory}, COLLECTION_NAME={collection_name}, "
        f"DEFAULT_CHUNK_SIZE={chunk_size}, DEFAULT_CHUNK_OVERLAP={chunk_overlap}, MODEL_NAME={model_name}, "
        f"MAX_FILE_SIZE_MB={max_file_size_mb}"
    )
    print("伺服器啟動: http://127.0.0.1:7861")

    # 建立 UI
    interface = create_ui(app)

    # 啟動伺服器
    interface.launch(
        show_error=True, server_name="127.0.0.1", server_port=7861, quiet=True
    )


if __name__ == "__main__":
    main()
